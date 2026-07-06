-- KPI: Turnover Trend
-- Definition: Measure of employee terminations across specific time periods.
-- Placeholder employees are naturally excluded here, since they have no
-- term_date at all, they simply never appear as a termination event.

-- === Monthly turnover (primary view) ===
SELECT
    date_trunc('month', term_date)::date AS termination_month,
    COUNT(*) AS terminations
FROM curated.employee
WHERE is_placeholder = false
  AND term_date IS NOT NULL
GROUP BY termination_month
ORDER BY termination_month;


-- === Quarterly turnover (rollup) ===
SELECT
    date_trunc('quarter', term_date)::date AS termination_quarter,
    COUNT(*) AS terminations
FROM curated.employee
WHERE is_placeholder = false
  AND term_date IS NOT NULL
GROUP BY termination_quarter
ORDER BY termination_quarter;


-- === Monthly turnover rate (terminations as a percentage of active headcount that month) ===
-- This is more meaningful than a raw count alone, since 2 terminations out of 50
-- employees is a very different signal than 2 out of 500. Reuses the same active
-- headcount logic from active_headcount.sql for the denominator.

WITH month_ends AS (
    SELECT
        (generate_series(
            date_trunc('month', (SELECT MIN(hire_date) FROM curated.employee WHERE is_placeholder = false)),
            date_trunc('month', CURRENT_DATE),
            interval '1 month'
        ) + interval '1 month' - interval '1 day')::date AS as_of_date
),
headcount AS (
    SELECT
        m.as_of_date,
        COUNT(e.client_employee_id) AS active_headcount
    FROM month_ends m
    LEFT JOIN curated.employee e
        ON e.is_placeholder = false
        AND e.hire_date <= m.as_of_date
        AND (e.term_date IS NULL OR e.term_date > m.as_of_date)
    GROUP BY m.as_of_date
),
terminations AS (
    SELECT
        (date_trunc('month', term_date) + interval '1 month' - interval '1 day')::date AS as_of_date,
        COUNT(*) AS terminations
    FROM curated.employee
    WHERE is_placeholder = false
      AND term_date IS NOT NULL
    GROUP BY as_of_date
)
SELECT
    h.as_of_date,
    h.active_headcount,
    COALESCE(t.terminations, 0) AS terminations,
    ROUND(
        100.0 * COALESCE(t.terminations, 0) / NULLIF(h.active_headcount, 0), 2
    ) AS turnover_rate_percentage
FROM headcount h
LEFT JOIN terminations t ON h.as_of_date = t.as_of_date
ORDER BY h.as_of_date;