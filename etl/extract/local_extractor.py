import os
import glob
import pandas as pd
from etl.utils.db_connection import get_engine, load_config
from etl.utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_csv_file(file_path, file_format):
    return pd.read_csv(
        file_path,
        sep=file_format["delimiter"],
        quotechar=file_format["quote_char"],
        na_values=file_format["null_values"],
        dtype=str,
        encoding=file_format["encoding"],
    )


def extract_employee_files():
    config = load_config()
    engine = get_engine()
    file_format = config["file_format"]

    folder = os.path.join(BASE_DIR, config["storage"]["local"]["employee_path"])
    csv_files = glob.glob(os.path.join(folder, "*.csv"))

    if not csv_files:
        logger.warning(f"No employee csv files found in {folder}")
        return

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        try:
            logger.info(f"Reading employee file: {file_name}")
            df = read_csv_file(file_path, file_format)
            df["source_file"] = file_name

            df.to_sql(
                "employee_raw",
                engine,
                schema="raw",
                if_exists="append",
                index=False,
            )
            logger.info(f"Loaded {len(df)} rows from {file_name} into raw.employee_raw")

        except Exception as e:
            logger.error(f"Failed to process employee file {file_name}: {e}")


def extract_timesheet_files():
    config = load_config()
    engine = get_engine()
    file_format = config["file_format"]

    folder = os.path.join(BASE_DIR, config["storage"]["local"]["timesheet_path"])
    csv_files = glob.glob(os.path.join(folder, "*.csv"))

    if not csv_files:
        logger.warning(f"No timesheet csv files found in {folder}")
        return

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        try:
            logger.info(f"Reading timesheet file: {file_name}")
            df = read_csv_file(file_path, file_format)
            df["source_file"] = file_name

            df.to_sql(
                "timesheet_raw",
                engine,
                schema="raw",
                if_exists="append",
                index=False,
            )
            logger.info(f"Loaded {len(df)} rows from {file_name} into raw.timesheet_raw")

        except Exception as e:
            logger.error(f"Failed to process timesheet file {file_name}: {e}")


def run_local_extraction():
    logger.info("Starting local extraction")
    extract_employee_files()
    extract_timesheet_files()
    logger.info("Local extraction finished")


if __name__ == "__main__":
    run_local_extraction()