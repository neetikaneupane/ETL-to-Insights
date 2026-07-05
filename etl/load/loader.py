import pandas as pd
from datetime import date
from sqlalchemy import MetaData, Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from etl.utils.db_connection import get_engine
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def read_staging_employees(engine):
    query = "SELECT * FROM staging.employee_staging"
    df = pd.read_sql(query, engine)
    logger.info(f"Read {len(df)} rows from staging.employee_staging")
    return df


def build_full_name(row):
    parts = [row.get("first_name"), row.get("middle_name"), row.get("last_name")]
    parts = [p for p in parts if p]
    return " ".join(parts) if parts else None


def compute_tenure_days(row, today):
    hire_date = row.get("hire_date")
    if pd.isna(hire_date):
        return None

    end_date = row.get("term_date") if pd.notna(row.get("term_date")) else today
    return (end_date - hire_date).days


def curate_employees(df):
    today = date.today()

    df["is_placeholder"] = (df["first_name"] == "Unknown") & (df["last_name"] == "Unknown")
    df["full_name"] = df.apply(build_full_name, axis=1)
    df["tenure_days"] = df.apply(lambda row: compute_tenure_days(row, today), axis=1)

    return df


def upsert_curated_employees(df, engine):
    curated_columns = [
        "client_employee_id", "first_name", "middle_name", "last_name", "preferred_name",
        "full_name", "job_code", "job_title", "job_start_date", "organization_id",
        "organization_name", "department_id", "department_name", "dob", "hire_date",
        "recent_hire_date", "anniversary_date", "term_date", "tenure_days",
        "years_of_experience", "work_email", "address", "city", "state", "zip", "country",
        "manager_employee_id", "manager_employee_name", "fte_status", "is_per_deim",
        "cell_phone", "work_phone", "scheduled_weekly_hour", "active_status",
        "termination_reason", "clinical_level", "is_placeholder",
    ]

    clean_df = df[curated_columns].astype(object)
    clean_df = clean_df.where(pd.notnull(clean_df), None)

    records = clean_df.to_dict(orient="records")

    if not records:
        logger.warning("No employee records to upsert into curated")
        return

    meta = MetaData(schema="curated")
    employee_table = Table("employee", meta, autoload_with=engine)

    batch_size = 300
    total_upserted = 0

    with engine.begin() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            stmt = pg_insert(employee_table).values(batch)
            update_columns = {
                col.name: stmt.excluded[col.name]
                for col in employee_table.columns
                if col.name not in ("client_employee_id", "created_at")
            }
            update_columns["updated_at"] = pd.Timestamp.now()

            stmt = stmt.on_conflict_do_update(
                index_elements=["client_employee_id"],
                set_=update_columns,
            )
            conn.execute(stmt)
            total_upserted += len(batch)

    logger.info(f"Upserted {total_upserted} employee records into curated.employee")



def run_employee_load():
    logger.info("Starting employee curated load")
    engine = get_engine()
    df = read_staging_employees(engine)

    if df.empty:
        logger.warning("No staging employee data found, skipping curated load")
        return

    df = curate_employees(df)
    upsert_curated_employees(df, engine)
    logger.info("Employee curated load finished")

def read_staging_timesheets(engine):
    query = "SELECT * FROM staging.timesheet_staging"
    df = pd.read_sql(query, engine)
    logger.info(f"Read {len(df)} rows from staging.timesheet_staging")
    return df


def compute_attendance_flags(df, grace_minutes):
    grace = pd.Timedelta(minutes=grace_minutes)

    has_schedule = df["scheduled_start_datetime"].notna() & df["scheduled_end_datetime"].notna()
    has_punches = df["punch_in_datetime"].notna() & df["punch_out_datetime"].notna()

    df["is_late_arrival"] = None
    df["is_early_departure"] = None
    df["is_overtime"] = None

    valid_start = has_schedule & df["punch_in_datetime"].notna()
    df.loc[valid_start, "is_late_arrival"] = (
        df.loc[valid_start, "punch_in_datetime"]
        > df.loc[valid_start, "scheduled_start_datetime"] + grace
    )

    valid_end = has_schedule & df["punch_out_datetime"].notna()
    df.loc[valid_end, "is_early_departure"] = (
        df.loc[valid_end, "punch_out_datetime"]
        < df.loc[valid_end, "scheduled_end_datetime"] - grace
    )

    valid_overtime = has_schedule & has_punches
    actual_duration = (
        df.loc[valid_overtime, "punch_out_datetime"] - df.loc[valid_overtime, "punch_in_datetime"]
    )
    scheduled_duration = (
        df.loc[valid_overtime, "scheduled_end_datetime"] - df.loc[valid_overtime, "scheduled_start_datetime"]
    )
    df.loc[valid_overtime, "is_overtime"] = actual_duration > (scheduled_duration + grace)

    return df


def deduplicate_timesheets(df):
    before_count = len(df)
    df = df.drop_duplicates(
        subset=["client_employee_id", "punch_in_datetime", "punch_out_datetime"],
        keep="first",
    )
    after_count = len(df)
    if before_count != after_count:
        logger.info(
            f"Removed {before_count - after_count} duplicate timesheet rows "
            f"during curated load, keeping first occurrence"
        )
    return df


def curate_timesheets(df, config):
    grace_minutes = config["business_rules"]["grace_period_minutes"]
    df = deduplicate_timesheets(df)
    df = compute_attendance_flags(df, grace_minutes)
    return df


def upsert_curated_timesheets(df, engine):
    curated_columns = [
        "client_employee_id", "department_id", "department_name", "home_department_id",
        "home_department_name", "pay_code", "hours_worked", "punch_apply_date",
        "punch_in_datetime", "punch_out_datetime", "scheduled_start_datetime",
        "scheduled_end_datetime", "is_late_arrival", "is_early_departure", "is_overtime",
    ]

    clean_df = df[curated_columns].astype(object)
    clean_df = clean_df.where(pd.notnull(clean_df), None)

    records = clean_df.to_dict(orient="records")

    if not records:
        logger.warning("No timesheet records to upsert into curated")
        return

    meta = MetaData(schema="curated")
    timesheet_table = Table("timesheet", meta, autoload_with=engine)

    batch_size = 300
    total_upserted = 0

    with engine.begin() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            stmt = pg_insert(timesheet_table).values(batch)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["client_employee_id", "punch_in_datetime", "punch_out_datetime"]
            )
            conn.execute(stmt)
            total_upserted += len(batch)

    logger.info(f"Upserted {total_upserted} timesheet records into curated.timesheet")


def run_timesheet_load():
    from etl.utils.db_connection import load_config

    logger.info("Starting timesheet curated load")
    engine = get_engine()
    config = load_config()
    df = read_staging_timesheets(engine)

    if df.empty:
        logger.warning("No staging timesheet data found, skipping curated load")
        return

    df = curate_timesheets(df, config)
    upsert_curated_timesheets(df, engine)
    logger.info("Timesheet curated load finished")


if __name__ == "__main__":
    run_employee_load()
    run_timesheet_load()