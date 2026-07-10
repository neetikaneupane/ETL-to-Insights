import re
import pandas as pd
from sqlalchemy import MetaData, Table, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from etl.utils.db_connection import get_engine
from etl.utils.logger import get_logger

logger = get_logger(__name__)

STRING_COLUMNS = [
    "client_employee_id", "department_id", "department_name",
    "home_department_id", "home_department_name", "pay_code",
    "punch_in_comment", "punch_out_comment",
]

DATETIME_COLUMNS = [
    "punch_in_datetime", "punch_out_datetime",
    "scheduled_start_datetime", "scheduled_end_datetime",
]

DATE_COLUMNS = ["punch_apply_date"]

NUMERIC_COLUMNS = ["hours_worked"]

REPEATED_DIGIT_PATTERN = re.compile(r"^(\d)\1{3,}$")
KNOWN_JUNK_IDS = {"999999", "999951", "TEST2", "CMCRN-3"}


def is_junk_employee_id(emp_id):
    if emp_id is None:
        return True
    emp_id = str(emp_id).strip()

    if emp_id in KNOWN_JUNK_IDS:
        return True
    if REPEATED_DIGIT_PATTERN.match(emp_id):
        return True

    return False


def read_raw_timesheets(engine):
    query = "SELECT * FROM raw.timesheet_raw"
    df = pd.read_sql(query, engine)
    logger.info(f"Read {len(df)} rows from raw.timesheet_raw")
    return df


def clean_timesheets(df):
    for col in STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].str.strip()
            df[col] = df[col].replace("", None)

    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    for col in DATETIME_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    before_count = len(df)
    df = df.dropna(subset=["client_employee_id"])
    after_count = len(df)
    if before_count != after_count:
        logger.warning(
            f"Dropped {before_count - after_count} timesheet rows with missing client_employee_id"
        )

    before_junk_filter = len(df)
    junk_mask = df["client_employee_id"].apply(is_junk_employee_id)
    junk_ids_found = sorted(df.loc[junk_mask, "client_employee_id"].unique())
    df = df.loc[~junk_mask]
    after_junk_filter = len(df)

    if before_junk_filter != after_junk_filter:
        logger.warning(
            f"Filtered out {before_junk_filter - after_junk_filter} timesheet rows with "
            f"junk or malformed employee ids: {junk_ids_found}"
        )

    return df


def ensure_employee_placeholders(df, engine):
    existing_ids = set(
        pd.read_sql("SELECT client_employee_id FROM staging.employee_staging", engine)[
            "client_employee_id"
        ]
    )
    timesheet_ids = set(df["client_employee_id"].unique())
    missing_ids = timesheet_ids - existing_ids

    if not missing_ids:
        return

    logger.warning(
        f"Found {len(missing_ids)} employee ids in timesheet data not present in "
        f"staging.employee_staging, inserting placeholder records"
    )

    placeholder_records = [
        {
            "client_employee_id": emp_id,
            "first_name": "Unknown",
            "last_name": "Unknown",
            "active_status": None,
        }
        for emp_id in missing_ids
    ]

    meta = MetaData(schema="staging")
    employee_table = Table("employee_staging", meta, autoload_with=engine)

    with engine.begin() as conn:
        stmt = pg_insert(employee_table).values(placeholder_records)
        stmt = stmt.on_conflict_do_nothing(index_elements=["client_employee_id"])
        conn.execute(stmt)


def load_to_staging(df, engine):
    staging_columns = [
        "client_employee_id", "department_id", "department_name",
        "home_department_id", "home_department_name", "pay_code",
        "punch_in_comment", "punch_out_comment", "hours_worked",
        "punch_apply_date", "punch_in_datetime", "punch_out_datetime",
        "scheduled_start_datetime", "scheduled_end_datetime", "source_file",
    ]

    insert_df = df[staging_columns].where(pd.notnull(df[staging_columns]), None)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE staging.timesheet_staging RESTART IDENTITY CASCADE"))
        insert_df.to_sql(
            "timesheet_staging",
            conn,
            schema="staging",
            if_exists="append",
            index=False,
        )

    logger.info(f"Loaded {len(insert_df)} timesheet rows into staging.timesheet_staging")


def run_timesheet_transform():
    logger.info("Starting timesheet transform")
    engine = get_engine()
    df = read_raw_timesheets(engine)

    if df.empty:
        logger.warning("No raw timesheet data found, skipping transform")
        return

    df = clean_timesheets(df)
    ensure_employee_placeholders(df, engine)
    load_to_staging(df, engine)
    logger.info("Timesheet transform finished")


if __name__ == "__main__":
    run_timesheet_transform()