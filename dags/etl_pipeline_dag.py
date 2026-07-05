from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl.extract.minio_extractor import run_minio_extraction
from etl.transform.employee_transform import run_employee_transform
from etl.transform.timesheet_transform import run_timesheet_transform
from etl.load.loader import run_employee_load, run_timesheet_load
from etl.quality_checks.validation import run_quality_checks

default_args = {
    "owner": "neetika",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="etl_to_insights_pipeline",
    description="End to end ETL pipeline for employee and timesheet data",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["etl", "employee", "timesheet"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_from_minio",
        python_callable=run_minio_extraction,
    )

    transform_employee_task = PythonOperator(
        task_id="transform_employee",
        python_callable=run_employee_transform,
    )

    transform_timesheet_task = PythonOperator(
        task_id="transform_timesheet",
        python_callable=run_timesheet_transform,
    )

    load_employee_task = PythonOperator(
        task_id="load_employee_curated",
        python_callable=run_employee_load,
    )

    load_timesheet_task = PythonOperator(
        task_id="load_timesheet_curated",
        python_callable=run_timesheet_load,
    )

    quality_check_task = PythonOperator(
        task_id="run_quality_checks",
        python_callable=run_quality_checks,
    )

    extract_task >> transform_employee_task >> transform_timesheet_task
    transform_timesheet_task >> load_employee_task >> load_timesheet_task
    load_timesheet_task >> quality_check_task