import os
import tempfile
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def test_read_csv_file():
    from etl.extract.local_extractor import read_csv_file

    file_format = {
        "delimiter": "|",
        "quote_char": "\"",
        "null_values": ["[NULL]", "", "NULL"],
        "encoding": "utf-8",
    }

    content = (
        b"client_employee_id|first_name|last_name|department_name\n"
        b"E001|Alice|Smith|Engineering\n"
        b"E002|Bob|Jones|[NULL]\n"
    )

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(content)
        tmp = f.name

    try:
        df = read_csv_file(tmp, file_format)
        assert len(df) == 2
        assert list(df.columns) == ["client_employee_id", "first_name", "last_name", "department_name"]
        assert df.iloc[0]["client_employee_id"] == "E001"
    finally:
        os.unlink(tmp)


def test_employee_data_file_exists():
    employee_dir = BASE_DIR / "data" / "raw" / "employee"
    csv_files = list(employee_dir.glob("*.csv"))
    assert len(csv_files) > 0, f"No employee CSV files found in {employee_dir}"


def test_timesheet_data_file_exists():
    timesheet_dir = BASE_DIR / "data" / "raw" / "timesheet"
    csv_files = list(timesheet_dir.glob("*.csv"))
    assert len(csv_files) > 0, f"No timesheet CSV files found in {timesheet_dir}"


def test_employee_csv_format():
    employee_file = list((BASE_DIR / "data" / "raw" / "employee").glob("*.csv"))
    if not employee_file:
        return
    df = pd.read_csv(employee_file[0], sep="|", nrows=5)
    expected_cols = {"client_employee_id", "first_name", "last_name", "department_name"}
    assert expected_cols.issubset(df.columns), f"Missing columns in {employee_file[0]}"
