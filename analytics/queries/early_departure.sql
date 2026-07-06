-- KPI: Early Departure Count
-- Definition: Number of days employees left earlier than the expected shift
-- end time, considering a five minute grace period. Only rows where both
-- punch and schedule data exist are assessable.

-- === Early departure count per employee ===
SELECT
    client_employee_id,
    COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL) AS assessable_punches,
    COUNT(*) FILTER (WHERE is_early_departure = true) AS early_departures,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_early_departure = true)
        / NULLIF(COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL), 0), 2
    ) AS early_departure_rate_percentage
FROM curated.timesheet
GROUP BY client_employee_id
HAVING COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL) > 0
ORDER BY early_departures DESC;


-- === Overall summary ===
SELECT
    COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL) AS total_assessable_punches,
    COUNT(*) FILTER (WHERE is_early_departure = true) AS total_early_departures,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_early_departure = true)
        / NULLIF(COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL), 0), 2
    ) AS overall_early_departure_rate_percentage
FROM curated.timesheet;