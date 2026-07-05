import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from etl.utils.db_connection import get_engine
from etl.utils.logger import get_logger

logger = get_logger(__name__)

STRING_COLUMNS = [
    "client_employee_id", "first_name", "middle_name", "last_name", "preferred_name",
    "job_code", "job_title", "organization_id", "organization_name",
    "department_id", "department_name", "work_email", "address", "city",
    "state", "zip", "country", "manager_employee_id", "manager_employee_name",
    "fte_status", "cell_phone", "work_phone", "termination_reason", "clinical_level",
]

DATE_COLUMNS = [
    "job_start_date", "dob", "hire_date", "recent_hire_date",
    "anniversary_date", "term_date",
]

NUMERIC_COLUMNS = ["years_of_experience", "scheduled_weekly_hour"]

BOOLEAN_COLUMNS = ["is_per_deim"]

TRUE_VALUES = {"1", "true", "y", "yes"}
FALSE_VALUES = {"0", "false", "n", "no"}


def parse_bool(value):
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def read_raw_employees(engine):
    query = "SELECT * FROM raw.employee_raw"
    df = pd.read_sql(query, engine)
    logger.info(f"Read {len(df)} rows from raw.employee_raw")
    return df


def clean_employees(df):
    for col in STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].str.strip()
            df[col] = df[col].replace("", None)

    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in BOOLEAN_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(parse_bool)

    df["active_status"] = df["term_date"].isna()

    df = df.sort_values("loaded_at", ascending=False)
    before_count = len(df)
    df = df.drop_duplicates(subset="client_employee_id", keep="first")
    after_count = len(df)
    if before_count != after_count:
        logger.info(
            f"Removed {before_count - after_count} duplicate employee rows, "
            f"keeping most recently loaded record per employee"
        )

    df = df.dropna(subset=["client_employee_id"])

    return df


def upsert_to_staging(df, engine):
    staging_columns = [
        "client_employee_id", "first_name", "middle_name", "last_name", "preferred_name",
        "job_code", "job_title", "job_start_date", "organization_id", "organization_name",
        "department_id", "department_name", "dob", "hire_date", "recent_hire_date",
        "anniversary_date", "term_date", "years_of_experience", "work_email", "address",
        "city", "state", "zip", "country", "manager_employee_id", "manager_employee_name",
        "fte_status", "is_per_deim", "cell_phone", "work_phone", "scheduled_weekly_hour",
        "active_status", "termination_reason", "clinical_level",
    ]

    records = df[staging_columns].where(pd.notnull(df[staging_columns]), None).to_dict(orient="records")

    if not records:
        logger.warning("No employee records to upsert into staging")
        return

    with engine.begin() as conn:
        from sqlalchemy import MetaData, Table

        meta = MetaData(schema="staging")
        staging_table = Table("employee_staging", meta, autoload_with=engine)

        stmt = pg_insert(staging_table).values(records)
        update_columns = {
            col.name: stmt.excluded[col.name]
            for col in staging_table.columns
            if col.name not in ("client_employee_id", "created_at")
        }
        update_columns["updated_at"] = text("now()")

        stmt = stmt.on_conflict_do_update(
            index_elements=["client_employee_id"],
            set_=update_columns,
        )
        conn.execute(stmt)

    logger.info(f"Upserted {len(records)} employee records into staging.employee_staging")


def run_employee_transform():
    logger.info("Starting employee transform")
    engine = get_engine()
    df = read_raw_employees(engine)

    if df.empty:
        logger.warning("No raw employee data found, skipping transform")
        return

    df = clean_employees(df)
    upsert_to_staging(df, engine)
    logger.info("Employee transform finished")


if __name__ == "__main__":
    run_employee_transform()