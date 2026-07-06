-- KPI: Active Headcount Over Time
-- Definition: Number of employees actively employed on a given date, based on
-- hire_date and term_date. An employee counts as active on a date if
-- hire_date <= that date AND (term_date IS NULL OR term_date > that date).
-- Placeholder employees (is_placeholder = true) are excluded, since they have
-- no hire_date and cannot be meaningfully placed on a timeline.

-- === Monthly summary (default view) ===
-- Generates one row per month end, from the earliest real hire_date up to today.

WITH month_ends AS (
    SELECT
        (generate_series(
            date_trunc('month', (SELECT MIN(hire_date) FROM curated.employee WHERE is_placeholder = false)),
            date_trunc('month', CURRENT_DATE),
            interval '1 month'
        ) + interval '1 month' - interval '1 day')::date AS as_of_date
)
SELECT
    as_of_date,
    COUNT(e.client_employee_id) AS active_headcount
FROM month_ends
LEFT JOIN curated.employee e
    ON e.is_placeholder = false
    AND e.hire_date <= month_ends.as_of_date
    AND (e.term_date IS NULL OR e.term_date > month_ends.as_of_date)
GROUP BY as_of_date
ORDER BY as_of_date;


-- === Daily granularity (available on request) ===
-- Same logic, just change the generate_series interval from '1 month' to '1 day'.
-- Note this can produce a very large result set over a multi-decade hire history,
-- so it is best used with an explicit date range filter in the WHERE clause
-- of the outer query when called from the API, rather than the full history.

-- WITH day_range AS (
--     SELECT generate_series(
--         (SELECT MIN(hire_date) FROM curated.employee WHERE is_placeholder = false),
--         CURRENT_DATE,
--         interval '1 day'
--     )::date AS as_of_date
-- )
-- SELECT
--     as_of_date,
--     COUNT(e.client_employee_id) AS active_headcount
-- FROM day_range
-- LEFT JOIN curated.employee e
--     ON e.is_placeholder = false
--     AND e.hire_date <= day_range.as_of_date
--     AND (e.term_date IS NULL OR e.term_date > day_range.as_of_date)
-- GROUP BY as_of_date
-- ORDER BY as_of_date;


-- === Single date lookup (for API "as of" queries) ===
-- Replace :as_of_date with a specific date parameter when calling from the API.

-- SELECT COUNT(*) AS active_headcount
-- FROM curated.employee
-- WHERE is_placeholder = false
--   AND hire_date <= :as_of_date
--   AND (term_date IS NULL OR term_date > :as_of_date);