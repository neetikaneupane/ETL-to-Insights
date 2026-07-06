-- KPI: Average Working Hours per Employee
-- Definition: Mean number of hours worked per day or per week by each employee.
-- Placeholder employees are included here, since excluding them would discard
-- over 99% of the timesheet volume, this KPI is about hours patterns, not
-- employee identity, so it still holds meaning even without full bio data.

-- === Average hours per day, per employee ===
SELECT
    client_employee_id,
    COUNT(DISTINCT punch_apply_date) AS days_worked,
    ROUND(AVG(hours_worked), 2) AS avg_hours_per_day
FROM curated.timesheet
WHERE hours_worked IS NOT NULL
GROUP BY client_employee_id
ORDER BY avg_hours_per_day DESC;


-- === Average hours per week, per employee ===
-- Groups punches into ISO weeks, sums hours within each week, then averages
-- those weekly totals per employee, rather than averaging daily hours and
-- multiplying by 7, which would not correctly account for employees who
-- do not work every day of the week.

WITH weekly_hours AS (
    SELECT
        client_employee_id,
        date_trunc('week', punch_apply_date) AS week_start,
        SUM(hours_worked) AS total_hours_that_week
    FROM curated.timesheet
    WHERE hours_worked IS NOT NULL
    GROUP BY client_employee_id, week_start
)
SELECT
    client_employee_id,
    COUNT(*) AS weeks_worked,
    ROUND(AVG(total_hours_that_week), 2) AS avg_hours_per_week
FROM weekly_hours
GROUP BY client_employee_id
ORDER BY avg_hours_per_week DESC;


-- === Overall summary across all employees (both granularities) ===
SELECT
    ROUND(AVG(hours_worked), 2) AS overall_avg_hours_per_day
FROM curated.timesheet
WHERE hours_worked IS NOT NULL;

WITH weekly_hours AS (
    SELECT
        client_employee_id,
        date_trunc('week', punch_apply_date) AS week_start,
        SUM(hours_worked) AS total_hours_that_week
    FROM curated.timesheet
    WHERE hours_worked IS NOT NULL
    GROUP BY client_employee_id, week_start
)
SELECT
    ROUND(AVG(total_hours_that_week), 2) AS overall_avg_hours_per_week
FROM weekly_hours;