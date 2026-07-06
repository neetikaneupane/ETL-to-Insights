-- KPI: Early Attrition Rate
-- Definition: Proportion of employees who leave within the first few months
-- of joining. Shown at two thresholds, 90 days and 6 months, since a very
-- quick exit and a somewhat slower one both matter but signal different
-- things, 90 days often points to onboarding or role mismatch, 6 months
-- points more toward broader early tenure dissatisfaction.
-- Placeholder employees are excluded, since they have no hire_date at all.

-- === Early attrition rate at 90 days ===
WITH base AS (
    SELECT
        client_employee_id,
        hire_date,
        term_date,
        CASE
            WHEN term_date IS NOT NULL AND (term_date - hire_date) <= 90 THEN true
            ELSE false
        END AS left_within_90_days
    FROM curated.employee
    WHERE is_placeholder = false
      AND hire_date IS NOT NULL
)
SELECT
    COUNT(*) AS total_employees,
    COUNT(*) FILTER (WHERE left_within_90_days) AS left_within_90_days_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE left_within_90_days) / NULLIF(COUNT(*), 0), 2
    ) AS early_attrition_rate_90_day_percentage
FROM base;


-- === Early attrition rate at 6 months (approximated as 182 days) ===
WITH base AS (
    SELECT
        client_employee_id,
        hire_date,
        term_date,
        CASE
            WHEN term_date IS NOT NULL AND (term_date - hire_date) <= 182 THEN true
            ELSE false
        END AS left_within_6_months
    FROM curated.employee
    WHERE is_placeholder = false
      AND hire_date IS NOT NULL
)
SELECT
    COUNT(*) AS total_employees,
    COUNT(*) FILTER (WHERE left_within_6_months) AS left_within_6_months_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE left_within_6_months) / NULLIF(COUNT(*), 0), 2
    ) AS early_attrition_rate_6_month_percentage
FROM base;


-- === Which specific employees left early, at either threshold (diagnostic) ===
SELECT
    client_employee_id,
    full_name,
    department_name,
    hire_date,
    term_date,
    (term_date - hire_date) AS days_employed,
    CASE
        WHEN (term_date - hire_date) <= 90 THEN '90 days'
        WHEN (term_date - hire_date) <= 182 THEN '6 months'
        ELSE 'later'
    END AS attrition_bucket
FROM curated.employee
WHERE is_placeholder = false
  AND hire_date IS NOT NULL
  AND term_date IS NOT NULL
  AND (term_date - hire_date) <= 182
ORDER BY days_employed;