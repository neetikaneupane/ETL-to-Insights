-- KPI: Rolling Average Working Hours
-- Definition: Moving average of working hours across a defined recent time
-- window, computed per employee, using their 7 most recent and 30 most
-- recent worked days respectively, not calendar days. This means the window
-- rolls across actual worked days for that employee, skipping days they did
-- not work, since averaging across calendar gaps would understate their
-- true recent workload pattern.

-- === Full rolling average history, every employee, every worked day ===
WITH daily_hours AS (
    SELECT
        client_employee_id,
        punch_apply_date,
        SUM(hours_worked) AS daily_hours
    FROM curated.timesheet
    WHERE hours_worked IS NOT NULL
    GROUP BY client_employee_id, punch_apply_date
)
SELECT
    client_employee_id,
    punch_apply_date,
    daily_hours,
    ROUND(
        AVG(daily_hours) OVER (
            PARTITION BY client_employee_id
            ORDER BY punch_apply_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_avg_hours_7day,
    ROUND(
        AVG(daily_hours) OVER (
            PARTITION BY client_employee_id
            ORDER BY punch_apply_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_avg_hours_30day
FROM daily_hours
ORDER BY client_employee_id, punch_apply_date;


-- === Most recent snapshot per employee (practical reporting view) ===
-- The full history above is extremely long, one row per employee per worked
-- day. This gives just each employee's latest rolling averages, the number
-- that actually matters for a dashboard, detecting who is trending toward
-- overtime or reduced productivity right now.

WITH daily_hours AS (
    SELECT
        client_employee_id,
        punch_apply_date,
        SUM(hours_worked) AS daily_hours
    FROM curated.timesheet
    WHERE hours_worked IS NOT NULL
    GROUP BY client_employee_id, punch_apply_date
),
rolling AS (
    SELECT
        client_employee_id,
        punch_apply_date,
        daily_hours,
        ROUND(
            AVG(daily_hours) OVER (
                PARTITION BY client_employee_id
                ORDER BY punch_apply_date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ), 2
        ) AS rolling_avg_hours_7day,
        ROUND(
            AVG(daily_hours) OVER (
                PARTITION BY client_employee_id
                ORDER BY punch_apply_date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 2
        ) AS rolling_avg_hours_30day
    FROM daily_hours
)
SELECT DISTINCT ON (client_employee_id)
    client_employee_id,
    punch_apply_date AS as_of_date,
    rolling_avg_hours_7day,
    rolling_avg_hours_30day
FROM rolling
ORDER BY client_employee_id, punch_apply_date DESC;