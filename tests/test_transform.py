import pandas as pd
from datetime import date


def test_is_junk_employee_id():
    from etl.transform.timesheet_transform import is_junk_employee_id

    assert is_junk_employee_id("999999") is True
    assert is_junk_employee_id("TEST2") is True
    assert is_junk_employee_id("CMCRN-3") is True
    assert is_junk_employee_id("101075-101012") is False
    assert is_junk_employee_id("1111") is True
    assert is_junk_employee_id(None) is True
    assert is_junk_employee_id("00025") is False
    assert is_junk_employee_id("12345") is False
    assert is_junk_employee_id("00457") is False


def test_parse_bool():
    from etl.transform.employee_transform import parse_bool

    assert parse_bool("1") is True
    assert parse_bool("true") is True
    assert parse_bool("yes") is True
    assert parse_bool("y") is True
    assert parse_bool("0") is False
    assert parse_bool("false") is False
    assert parse_bool("no") is False
    assert parse_bool("n") is False
    assert parse_bool("") is None
    assert parse_bool(None) is None
    assert parse_bool("maybe") is None


def test_clean_employees():
    from etl.transform.employee_transform import clean_employees

    data = {
        "client_employee_id": ["E001", "E001", "E002"],
        "first_name": [" Alice ", " Alice", "Bob"],
        "last_name": ["Smith", "Smith", "Jones"],
        "hire_date": ["2020-01-15", "2020-01-15", "invalid-date"],
        "term_date": [None, None, None],
        "loaded_at": pd.to_datetime(["2026-01-02", "2026-01-01", "2026-01-01"]),
    }
    df = pd.DataFrame(data)

    cleaned = clean_employees(df)

    assert len(cleaned) == 2
    assert cleaned.iloc[0]["client_employee_id"] == "E001"
    assert cleaned.iloc[0]["first_name"] == "Alice"
    assert cleaned.iloc[0]["hire_date"] == date(2020, 1, 15)
    assert cleaned.iloc[0]["active_status"] == True
    assert pd.isna(cleaned.iloc[1]["hire_date"])


def test_compute_attendance_flags():
    from etl.load.loader import compute_attendance_flags

    df = pd.DataFrame({
        "client_employee_id": ["E001", "E002", "E003"],
        "scheduled_start_datetime": pd.to_datetime([
            "2026-01-01 09:00", "2026-01-01 09:00", None,
        ]),
        "scheduled_end_datetime": pd.to_datetime([
            "2026-01-01 17:00", "2026-01-01 17:00", None,
        ]),
        "punch_in_datetime": pd.to_datetime([
            "2026-01-01 09:06", "2026-01-01 08:55", "2026-01-01 09:00",
        ]),
        "punch_out_datetime": pd.to_datetime([
            "2026-01-01 17:00", "2026-01-01 16:50", "2026-01-01 17:00",
        ]),
    })

    result = compute_attendance_flags(df, grace_minutes=5)

    assert result.loc[0, "is_late_arrival"] == True
    assert result.loc[1, "is_late_arrival"] == False
    assert pd.isna(result.loc[2, "is_late_arrival"])
    assert result.loc[0, "is_early_departure"] == False
    assert result.loc[1, "is_early_departure"] == True
    assert pd.isna(result.loc[2, "is_early_departure"])


def test_build_full_name():
    from etl.load.loader import build_full_name

    assert build_full_name({"first_name": "John", "middle_name": None, "last_name": "Doe"}) == "John Doe"
    assert build_full_name({"first_name": "John", "middle_name": "M", "last_name": "Doe"}) == "John M Doe"
    assert build_full_name({"first_name": None, "middle_name": None, "last_name": "Doe"}) == "Doe"
    assert build_full_name({"first_name": None, "middle_name": None, "last_name": None}) is None
