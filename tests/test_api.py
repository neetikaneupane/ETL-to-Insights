"""
API integration tests.

Requires the API server to be running on http://localhost:8000
with the ETL database populated.

Run with: pytest tests/test_api.py -v
"""
import os
import sys

import pytest
import requests

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
USERNAME = os.environ.get("API_USERNAME", "admin")
PASSWORD = os.environ.get("API_PASSWORD", "changeme123")


@pytest.fixture(scope="module")
def token():
    resp = requests.post(
        f"{API_BASE}/token",
        data={"grant_type": "password", "username": USERNAME, "password": PASSWORD},
    )
    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestHealth:
    def test_health(self):
        resp = requests.get(f"{API_BASE}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAuth:
    def test_login_valid(self):
        resp = requests.post(
            f"{API_BASE}/token",
            data={"grant_type": "password", "username": USERNAME, "password": PASSWORD},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_invalid(self):
        resp = requests.post(
            f"{API_BASE}/token",
            data={"grant_type": "password", "username": "wrong", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_no_token_returns_401(self):
        resp = requests.get(f"{API_BASE}/employees")
        assert resp.status_code == 401


class TestEmployeeCRUD:
    _test_id = None

    @pytest.fixture(autouse=True)
    def _setup_test_id(self):
        if TestEmployeeCRUD._test_id is None:
            TestEmployeeCRUD._test_id = f"PYTEST-{int(__import__('time').time())}"
        yield

    def test_list_employees(self, auth_header):
        resp = requests.get(f"{API_BASE}/employees", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_employee(self, auth_header):
        resp = requests.get(f"{API_BASE}/employees/00025", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["client_employee_id"] == "00025"

    def test_get_employee_404(self, auth_header):
        resp = requests.get(f"{API_BASE}/employees/NONEXISTENT", headers=auth_header)
        assert resp.status_code == 404

    def test_create_employee(self, auth_header):
        test_id = TestEmployeeCRUD._test_id
        payload = {
            "client_employee_id": test_id,
            "first_name": "Pytest",
            "last_name": "Creator",
            "department_name": "Testing",
            "hire_date": "2026-01-01",
        }
        resp = requests.post(f"{API_BASE}/employees", json=payload, headers=auth_header)
        assert resp.status_code == 201
        assert resp.json()["client_employee_id"] == test_id

    def test_create_duplicate(self, auth_header):
        test_id = TestEmployeeCRUD._test_id
        payload = {
            "client_employee_id": test_id,
            "first_name": "Pytest",
            "last_name": "Creator",
            "department_name": "Testing",
            "hire_date": "2026-01-01",
        }
        resp = requests.post(f"{API_BASE}/employees", json=payload, headers=auth_header)
        assert resp.status_code == 409

    def test_update_employee(self, auth_header):
        test_id = TestEmployeeCRUD._test_id
        resp = requests.put(
            f"{API_BASE}/employees/{test_id}",
            json={"first_name": "UpdatedPytest"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "UpdatedPytest"

    def test_delete_employee(self, auth_header):
        test_id = TestEmployeeCRUD._test_id
        resp = requests.delete(f"{API_BASE}/employees/{test_id}", headers=auth_header)
        assert resp.status_code == 204

    def test_get_deleted(self, auth_header):
        test_id = TestEmployeeCRUD._test_id
        resp = requests.get(f"{API_BASE}/employees/{test_id}", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json().get("active_status") is False


class TestTimesheetReadOnly:
    def test_list_timesheets(self, auth_header):
        resp = requests.get(f"{API_BASE}/timesheets?limit=3", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 3

    def test_timesheets_by_employee(self, auth_header):
        resp = requests.get(f"{API_BASE}/timesheets/employee/00025?limit=3", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_timesheets_by_employee_404(self, auth_header):
        resp = requests.get(f"{API_BASE}/timesheets/employee/NONEXISTENT?limit=3", headers=auth_header)
        assert resp.status_code == 404

    def test_timesheets_date_range(self, auth_header):
        resp = requests.get(
            f"{API_BASE}/timesheets?start_date=2026-01-01&end_date=2026-01-31&limit=5",
            headers=auth_header,
        )
        assert resp.status_code == 200


class TestAnalytics:
    def test_headcount(self, auth_header):
        resp = requests.get(f"{API_BASE}/analytics/headcount", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "as_of_date" in data[0]
        assert "active_headcount" in data[0]

    def test_turnover(self, auth_header):
        resp = requests.get(f"{API_BASE}/analytics/turnover", headers=auth_header)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_tenure_by_department(self, auth_header):
        resp = requests.get(f"{API_BASE}/analytics/tenure-by-department", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "avg_tenure_years" in data[0]

    def test_working_hours(self, auth_header):
        resp = requests.get(f"{API_BASE}/analytics/working-hours-summary", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_avg_hours_per_day" in data

    def test_attendance(self, auth_header):
        resp = requests.get(f"{API_BASE}/analytics/attendance-summary", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "late_arrival_rate" in data

    def test_rolling_hours(self, auth_header):
        resp = requests.get(f"{API_BASE}/analytics/rolling-hours-top", headers=auth_header)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_early_attrition(self, auth_header):
        resp = requests.get(f"{API_BASE}/analytics/early-attrition", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_employees" in data
