from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from api.dependencies import get_db
from api.auth.auth import get_current_user
from etl.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


def rows_to_dicts(result):
    return [dict(row._mapping) for row in result]


def first_row(result):
    rows = rows_to_dicts(result)
    return rows[0] if rows else {}


@router.get("/departments")
def list_departments(
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    query = text("""
        SELECT DISTINCT department_name
        FROM curated.employee
        WHERE is_placeholder = false AND department_name IS NOT NULL
        ORDER BY department_name
    """)
    return [r["department_name"] for r in rows_to_dicts(conn.execute(query))]


@router.get("/employees")
def list_employees_for_search(
    q: str = Query("", description="Search query (matches id or name)"),
    limit: int = Query(50, le=200),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    query = text("""
        SELECT client_employee_id, full_name, department_name
        FROM curated.employee
        WHERE is_placeholder = false
          AND (client_employee_id ILIKE :q OR full_name ILIKE :q)
        ORDER BY full_name
        LIMIT :lim
    """)
    result = conn.execute(query, {"q": f"%{q}%", "lim": limit})
    return rows_to_dicts(result)


@router.get("/headcount")
def active_headcount(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    department_name: Optional[str] = Query(None),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    dept_filter = "AND e.department_name = :dept" if department_name else ""
    query = text(f"""
        WITH month_ends AS (
            SELECT
                (generate_series(
                    date_trunc('month', COALESCE(CAST(:sd AS DATE), (SELECT MIN(hire_date) FROM curated.employee WHERE is_placeholder = false))),
                    date_trunc('month', COALESCE(CAST(:ed AS DATE), CURRENT_DATE)),
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
            {dept_filter}
        GROUP BY as_of_date
        ORDER BY as_of_date
    """)
    result = rows_to_dicts(conn.execute(query, {"sd": start_date, "ed": end_date, "dept": department_name}))
    logger.info(f"Headcount: {len(result)} months (dept={department_name})")
    return result


@router.get("/turnover")
def turnover_trend(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    query = text("""
        SELECT
            date_trunc('month', term_date)::date AS termination_month,
            COUNT(*) AS terminations
        FROM curated.employee
        WHERE is_placeholder = false
          AND term_date IS NOT NULL
          AND (CAST(:sd AS DATE) IS NULL OR term_date >= CAST(:sd AS DATE))
          AND (CAST(:ed AS DATE) IS NULL OR term_date <= CAST(:ed AS DATE))
        GROUP BY termination_month
        ORDER BY termination_month
    """)
    result = rows_to_dicts(conn.execute(query, {"sd": start_date, "ed": end_date}))
    logger.info(f"Turnover: {len(result)} months")
    return result


@router.get("/tenure-by-department")
def tenure_by_department(
    department_name: Optional[str] = Query(None),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    dept_filter = "AND e.department_name = :dept" if department_name else ""
    query = text(f"""
        SELECT
            department_name,
            COUNT(*) AS employee_count,
            ROUND(AVG(tenure_days) / 365.25, 2) AS avg_tenure_years
        FROM curated.employee e
        WHERE is_placeholder = false AND tenure_days IS NOT NULL
              {dept_filter}
        GROUP BY department_name
        ORDER BY avg_tenure_years DESC
    """)
    result = rows_to_dicts(conn.execute(query, {"dept": department_name}))
    logger.info(f"Tenure: {len(result)} departments")
    return result


@router.get("/working-hours-summary")
def working_hours_summary(
    employee_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    emp_filter = "AND client_employee_id = :eid" if employee_id else ""
    date_filter = ("AND (CAST(:sd AS DATE) IS NULL OR punch_apply_date >= CAST(:sd AS DATE)) "
                   "AND (CAST(:ed AS DATE) IS NULL OR punch_apply_date <= CAST(:ed AS DATE))")

    query_daily = text(f"""
        SELECT ROUND(AVG(hours_worked), 2) AS overall_avg_hours_per_day
        FROM curated.timesheet
        WHERE hours_worked IS NOT NULL
              {emp_filter}
              {date_filter}
    """)
    daily = first_row(conn.execute(query_daily, {"eid": employee_id, "sd": start_date, "ed": end_date}))

    query_weekly = text(f"""
        WITH weekly_hours AS (
            SELECT client_employee_id, date_trunc('week', punch_apply_date) AS week_start,
                SUM(hours_worked) AS total_hours_that_week
            FROM curated.timesheet
            WHERE hours_worked IS NOT NULL
                  {emp_filter}
                  {date_filter}
            GROUP BY client_employee_id, week_start
        )
        SELECT ROUND(AVG(total_hours_that_week), 2) AS overall_avg_hours_per_week
        FROM weekly_hours
    """)
    weekly = first_row(conn.execute(query_weekly, {"eid": employee_id, "sd": start_date, "ed": end_date}))

    result = {**daily, **weekly}
    logger.info(f"Working hours summary: {result}")
    return result


@router.get("/attendance-summary")
def attendance_summary(
    employee_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    emp_filter = "AND client_employee_id = :eid" if employee_id else ""
    date_filter = ("AND (CAST(:sd AS DATE) IS NULL OR punch_apply_date >= CAST(:sd AS DATE)) "
                   "AND (CAST(:ed AS DATE) IS NULL OR punch_apply_date <= CAST(:ed AS DATE))")
    query = text(f"""
        SELECT
            ROUND(100.0 * COUNT(*) FILTER (WHERE is_late_arrival = true) / NULLIF(COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL), 0), 2) AS late_arrival_rate,
            ROUND(100.0 * COUNT(*) FILTER (WHERE is_early_departure = true) / NULLIF(COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL), 0), 2) AS early_departure_rate,
            ROUND(100.0 * COUNT(*) FILTER (WHERE is_overtime = true) / NULLIF(COUNT(*) FILTER (WHERE is_overtime IS NOT NULL), 0), 2) AS overtime_rate
        FROM curated.timesheet
        WHERE 1=1
              {emp_filter}
              {date_filter}
    """)
    result = first_row(conn.execute(query, {"eid": employee_id, "sd": start_date, "ed": end_date}))
    if not result:
        return {"late_arrival_rate": 0, "early_departure_rate": 0, "overtime_rate": 0}
    logger.info(f"Attendance: late={result['late_arrival_rate']}% early={result['early_departure_rate']}% overtime={result['overtime_rate']}%")
    return result


@router.get("/rolling-hours-top")
def rolling_hours_top(
    employee_id: Optional[str] = Query(None),
    limit: int = Query(15, le=50),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    emp_filter = "AND client_employee_id = :eid" if employee_id else ""
    query = text(f"""
        WITH daily_hours AS (
            SELECT client_employee_id, punch_apply_date, SUM(hours_worked) AS daily_hours
            FROM curated.timesheet
            WHERE hours_worked IS NOT NULL
                  {emp_filter}
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
        LIMIT :lim
    """)
    result = rows_to_dicts(conn.execute(query, {"eid": employee_id, "lim": limit}))
    logger.info(f"Rolling hours top: {len(result)} employees")
    return result


@router.get("/early-attrition")
def early_attrition(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    query = text("""
        SELECT
            COUNT(*) AS total_employees,
            COUNT(*) FILTER (WHERE term_date IS NOT NULL AND (term_date - hire_date) <= 90) AS left_within_90_days,
            COUNT(*) FILTER (WHERE term_date IS NOT NULL AND (term_date - hire_date) <= 182) AS left_within_6_months
        FROM curated.employee
        WHERE is_placeholder = false
          AND hire_date IS NOT NULL
          AND (CAST(:sd AS DATE) IS NULL OR hire_date >= CAST(:sd AS DATE))
          AND (CAST(:ed AS DATE) IS NULL OR hire_date <= CAST(:ed AS DATE))
    """)
    result = first_row(conn.execute(query, {"sd": start_date, "ed": end_date}))
    if not result:
        return {"total_employees": 0, "left_within_90_days": 0, "left_within_6_months": 0}
    return result
