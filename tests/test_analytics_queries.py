"""
SQL Analytics Query Verification.

These tests connect to the database and run the actual KPI queries
to confirm they produce correct and expected results.
"""
import os
import pytest
from sqlalchemy import text


@pytest.fixture(scope="module")
def engine():
    from etl.utils.db_connection import get_engine
    return get_engine()


class TestHeadcount:
    def test_returns_rows(self, engine):
        query = """
            WITH month_ends AS (
                SELECT (generate_series(
                    date_trunc('month', (SELECT MIN(hire_date) FROM curated.employee WHERE is_placeholder = false)),
                    date_trunc('month', CURRENT_DATE),
                    interval '1 month'
                ) + interval '1 month' - interval '1 day')::date AS as_of_date
            )
            SELECT as_of_date, COUNT(e.client_employee_id) AS active_headcount
            FROM month_ends
            LEFT JOIN curated.employee e
                ON e.is_placeholder = false
                AND e.hire_date <= month_ends.as_of_date
                AND (e.term_date IS NULL OR e.term_date > month_ends.as_of_date)
            GROUP BY as_of_date
            ORDER BY as_of_date
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).all()
        assert len(result) > 0
        assert result[0].active_headcount >= 1


class TestTurnover:
    def test_turnover_months(self, engine):
        query = """
            SELECT date_trunc('month', term_date)::date AS termination_month, COUNT(*) AS terminations
            FROM curated.employee
            WHERE is_placeholder = false AND term_date IS NOT NULL
            GROUP BY termination_month ORDER BY termination_month
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).all()
        assert isinstance(result, list)
        for row in result:
            assert row.terminations >= 1


class TestAvgTenure:
    def test_tenure_happy_path(self, engine):
        query = """
            SELECT department_name, COUNT(*) AS employee_count,
                ROUND(AVG(tenure_days) / 365.25, 2) AS avg_tenure_years
            FROM curated.employee
            WHERE is_placeholder = false AND tenure_days IS NOT NULL
            GROUP BY department_name
            ORDER BY avg_tenure_years DESC
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).all()
        assert len(result) > 0
        assert result[0].avg_tenure_years > 0


class TestLateArrival:
    def test_late_arrival_rate(self, engine):
        query = """
            SELECT COUNT(*) FILTER (WHERE is_late_arrival IS NOT NULL) AS total_assessable,
                COUNT(*) FILTER (WHERE is_late_arrival = true) AS total_late_arrivals
            FROM curated.timesheet
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).first()
        assert result.total_assessable > 0
        assert 0 <= result.total_late_arrivals <= result.total_assessable


class TestEarlyDeparture:
    def test_early_departure_rate(self, engine):
        query = """
            SELECT COUNT(*) FILTER (WHERE is_early_departure IS NOT NULL) AS total_assessable,
                COUNT(*) FILTER (WHERE is_early_departure = true) AS total_early
            FROM curated.timesheet
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).first()
        assert result.total_assessable > 0
        assert 0 <= result.total_early <= result.total_assessable


class TestOvertime:
    def test_overtime_rate(self, engine):
        query = """
            SELECT COUNT(*) FILTER (WHERE is_overtime IS NOT NULL) AS total_assessable,
                COUNT(*) FILTER (WHERE is_overtime = true) AS total_overtime
            FROM curated.timesheet
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).first()
        assert result.total_assessable > 0
        assert 0 <= result.total_overtime <= result.total_assessable


class TestRollingHours:
    def test_rolling_avg(self, engine):
        query = """
            WITH daily_hours AS (
                SELECT client_employee_id, punch_apply_date, SUM(hours_worked) AS daily_hours
                FROM curated.timesheet WHERE hours_worked IS NOT NULL
                GROUP BY client_employee_id, punch_apply_date
            )
            SELECT client_employee_id, punch_apply_date,
                ROUND(AVG(daily_hours) OVER (
                    PARTITION BY client_employee_id ORDER BY punch_apply_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ), 2) AS rolling_avg_hours_7day
            FROM daily_hours
            LIMIT 5
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).all()
        assert len(result) > 0


class TestEarlyAttrition:
    def test_early_attrition_structure(self, engine):
        query = """
            SELECT COUNT(*) AS total_employees,
                COUNT(*) FILTER (WHERE term_date IS NOT NULL AND (term_date - hire_date) <= 90) AS left_within_90_days
            FROM curated.employee
            WHERE is_placeholder = false AND hire_date IS NOT NULL
        """
        with engine.connect() as conn:
            result = conn.execute(text(query)).first()
        assert result.total_employees > 0
        assert 0 <= result.left_within_90_days <= result.total_employees
