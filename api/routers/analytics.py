from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from api.dependencies import get_db
from api.auth.auth import get_current_user
from etl.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


def rows_to_dicts(result):
    return [dict(row._mapping) for row in result]


@router.get("/headcount")
def active_headcount(conn: Connection = Depends(get_db), current_user: str = Depends(get_current_user)):
    query = text("""
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
        ORDER BY as_of_date
    """)
    result = rows_to_dicts(conn.execute(query))
    logger.info(f"Headcount: {len(result)} months")
    return result


@router.get("/turnover")
def turnover_trend(conn: Connection = Depends(get_db), current_user: str = Depends(get_current_user)):
    query = text("""
        SELECT
            date_trunc('month', term_date)::date AS termination_month,
            COUNT(*) AS terminations
        FROM curated.employee
        WHERE is_placeholder = false AND term_date IS NOT NULL
        GROUP BY termination_month
        ORDER BY termination_month
    """)
    result = rows_to_dicts(conn.execute(query))
    logger.info(f"Turnover: {len(result)} months")
    return result


@router.get("/tenure-by-department")
def tenure_by_department(conn: Connection = Depends(get_db), current_user: str = Depends(get_current_user)):
    query = text("""
        SELECT
            department_name,
            COUNT(*) AS employee_count,
            ROUND(AVG(tenure_days) / 365.25, 2) AS avg_tenure_years
        FROM curated.employee
        WHERE is_placeholder = false AND tenure_days IS NOT NULL
        GROUP BY department_name
        ORDER BY avg_tenure_years DESC
    """)
    result = rows_to_dicts(conn.execute(query))
    logger.info(f"Tenure by department: {len(result)} departments")
    return result


@router.get("/working-hours-summary")
def working_hours_summary(conn: Connection = Depends(get_db), current_user: str = Depends(get_current_user)):
    query = text("""
        SELECT
            ROUND(AVG(hours_worked), 2) AS overall_avg_hours_per_day
        FROM curated.timesheet
        WHERE hours_worked IS NOT NULL
    """)
    daily = rows_to_dicts(conn.execute(query))
    if not daily:
        return {"overall_avg_hours_per_day": 0, "overall_avg_hours_per_week": 0}

    query_weekly = text("""
        WITH weekly_hours AS (
            SELECT client_employee_id, date_trunc('week', punch_apply_date) AS week_start,
                SUM(hours_worked) AS total_hours_that_week
            FROM curated.timesheet
            WHERE hours_worked IS NOT NULL
            GROUP BY client_employee_id, week_start
        )
        SELECT ROUND(AVG(total_hours_that_week), 2) AS overall_avg_hours_per_week
        FROM weekly_hours
    """)
    weekly = rows_to_dicts(conn.execute(query_weekly))
    if not weekly:
        return {"overall_avg_hours_per_day": daily[0]["overall_avg_hours_per_day"], "overall_avg_hours_per_week": 0}

    result_summary = {**daily[0], **weekly[0]}
    logger.info(f"Working hours summary: {result_summary}")
    return result_summary


@router.get("/attendance-summary")
def attendance_summary(conn: Connection = Depends(get_db), current_user: str = Depends(get_current_user)):
    query = text("""
        SELECT
            ROUND(100.0 * COUNT(*) FILTER (WHERE is_late_arrival = true) / NULLIF(COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL), 0), 2) AS late_arrival_rate,
            ROUND(100.0 * COUNT(*) FILTER (WHERE is_early_departure = true) / NULLIF(COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL), 0), 2) AS early_departure_rate,
            ROUND(100.0 * COUNT(*) FILTER (WHERE is_overtime = true) / NULLIF(COUNT(*) FILTER (WHERE is_overtime IS NOT NULL), 0), 2) AS overtime_rate
        FROM curated.timesheet
    """)
    result = rows_to_dicts(conn.execute(query))
    if not result:
        return {"late_arrival_rate": 0, "early_departure_rate": 0, "overtime_rate": 0}
    logger.info(f"Attendance summary: late={result[0]['late_arrival_rate']}% early={result[0]['early_departure_rate']}% overtime={result[0]['overtime_rate']}%")
    return result[0]


@router.get("/rolling-hours-top")
def rolling_hours_top(conn: Connection = Depends(get_db), current_user: str = Depends(get_current_user)):
    query = text("""
        WITH daily_hours AS (
            SELECT client_employee_id, punch_apply_date, SUM(hours_worked) AS daily_hours
            FROM curated.timesheet
            WHERE hours_worked IS NOT NULL
            GROUP BY client_employee_id, punch_apply_date
        ),
        rolling AS (
            SELECT client_employee_id, punch_apply_date, daily_hours,
                ROUND(AVG(daily_hours) OVER (PARTITION BY client_employee_id ORDER BY punch_apply_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_hours_7day,
                ROUND(AVG(daily_hours) OVER (PARTITION BY client_employee_id ORDER BY punch_apply_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_hours_30day
            FROM daily_hours
        )
        SELECT DISTINCT ON (client_employee_id) client_employee_id, punch_apply_date AS as_of_date,
            rolling_avg_hours_7day, rolling_avg_hours_30day
        FROM rolling
        ORDER BY client_employee_id, punch_apply_date DESC
        LIMIT 15
    """)
    result = rows_to_dicts(conn.execute(query))
    logger.info(f"Rolling hours top: {len(result)} employees")
    return result


@router.get("/early-attrition")
def early_attrition(conn: Connection = Depends(get_db), current_user: str = Depends(get_current_user)):
    query = text("""
        SELECT
            COUNT(*) AS total_employees,
            COUNT(*) FILTER (WHERE term_date IS NOT NULL AND (term_date - hire_date) <= 90) AS left_within_90_days,
            COUNT(*) FILTER (WHERE term_date IS NOT NULL AND (term_date - hire_date) <= 182) AS left_within_6_months
        FROM curated.employee
        WHERE is_placeholder = false AND hire_date IS NOT NULL
    """)
    result = rows_to_dicts(conn.execute(query))
    if not result:
        return {"total_employees": 0, "left_within_90_days": 0, "left_within_6_months": 0}
    return result[0]