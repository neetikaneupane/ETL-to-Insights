-- KPI: Late Arrival Frequency
-- Definition: Number of times an employee clocked in later than the scheduled
-- start time, considering a five minute grace period. Only rows where both
-- punch and schedule data exist are assessable, rows with is_late_arrival
-- IS NULL had no schedule to compare against and are excluded here.

-- === Late arrival count per employee ===
SELECT
    client_employee_id,
    COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL) AS assessable_punches,
    COUNT(*) FILTER (WHERE is_late_arrival = true) AS late_arrivals,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_late_arrival = true)
        / NULLIF(COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL), 0), 2
    ) AS late_arrival_rate_percentage
FROM curated.timesheet
GROUP BY client_employee_id
HAVING COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL) > 0
ORDER BY late_arrivals DESC;


-- === Overall summary ===
SELECT
    COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL) AS total_assessable_punches,
    COUNT(*) FILTER (WHERE is_late_arrival = true) AS total_late_arrivals,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_late_arrival = true)
        / NULLIF(COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL), 0), 2
    ) AS overall_late_arrival_rate_percentage
FROM curated.timesheet;