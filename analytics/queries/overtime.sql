-- KPI: Total Overtime Count
-- Definition: Total number of workdays where employees exceeded standard
-- shift duration, considering a five minute grace period. Only rows where
-- both punch and schedule data exist are assessable.

-- === Overtime count per employee ===
SELECT
    client_employee_id,
    COUNT(*) FILTER (WHERE is_overtime IS NOT NULL) AS assessable_punches,
    COUNT(*) FILTER (WHERE is_overtime = true) AS overtime_days,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_overtime = true)
        / NULLIF(COUNT(*) FILTER (WHERE is_overtime IS NOT NULL), 0), 2
    ) AS overtime_rate_percentage
FROM curated.timesheet
GROUP BY client_employee_id
HAVING COUNT(*) FILTER (WHERE is_overtime IS NOT NULL) > 0
ORDER BY overtime_days DESC;


-- === Overall summary ===
SELECT
    COUNT(*) FILTER (WHERE is_overtime IS NOT NULL) AS total_assessable_punches,
    COUNT(*) FILTER (WHERE is_overtime = true) AS total_overtime_days,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_overtime = true)
        / NULLIF(COUNT(*) FILTER (WHERE is_overtime IS NOT NULL), 0), 2
    ) AS overall_overtime_rate_percentage
FROM curated.timesheet;