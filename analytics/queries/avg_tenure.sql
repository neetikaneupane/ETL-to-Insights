-- KPI: Average Tenure by Department
-- Definition: Average employment duration of staff within each department.
-- Includes both active and terminated employees, since excluding terminated
-- staff would hide retention problems by only measuring survivors.
-- Placeholder employees are excluded, since they have no hire_date or
-- department data at all.

-- === Overall average tenure by department (primary view) ===
SELECT
    department_name,
    COUNT(*) AS employee_count,
    ROUND(AVG(tenure_days) / 365.25, 2) AS avg_tenure_years
FROM curated.employee
WHERE is_placeholder = false
  AND tenure_days IS NOT NULL
GROUP BY department_name
ORDER BY avg_tenure_years DESC;


-- === Breakdown by active vs terminated (diagnostic view) ===
-- Shows whether a department's average tenure is being pulled down by
-- fast turnover of terminated staff, or reflects genuinely short tenure
-- across the board.

SELECT
    department_name,
    COUNT(*) FILTER (WHERE active_status = true) AS active_count,
    ROUND(AVG(tenure_days) FILTER (WHERE active_status = true) / 365.25, 2) AS avg_tenure_years_active,
    COUNT(*) FILTER (WHERE active_status = false) AS terminated_count,
    ROUND(AVG(tenure_days) FILTER (WHERE active_status = false) / 365.25, 2) AS avg_tenure_years_terminated
FROM curated.employee
WHERE is_placeholder = false
  AND tenure_days IS NOT NULL
GROUP BY department_name
ORDER BY department_name;