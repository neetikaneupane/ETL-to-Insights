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

    records = df[curated_columns].where(pd.notnull(df[curated_columns]), None).to_dict(orient="records")

    if not records:
        logger.warning("No employee records to upsert into curated")
        return

    meta = MetaData(schema="curated")
    employee_table = Table("employee", meta, autoload_with=engine)

    with engine.begin() as conn:
        stmt = pg_insert(employee_table).values(records)
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

    logger.info(f"Upserted {len(records)} employee records into curated.employee")


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


if __name__ == "__main__":
    run_employee_load()