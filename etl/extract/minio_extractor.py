import os
import io
import pandas as pd
from minio import Minio
from etl.utils.db_connection import get_engine, load_config
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def get_minio_client(config):
    minio_config = config["storage"]["minio"]
    endpoint = minio_config["endpoint"]

    client = Minio(
        endpoint,
        access_key=minio_config["access_key"],
        secret_key=minio_config["secret_key"],
        secure=False,
    )
    return client


def read_csv_bytes(data_bytes, file_format):
    return pd.read_csv(
        io.BytesIO(data_bytes),
        sep=file_format["delimiter"],
        quotechar=file_format["quote_char"],
        na_values=file_format["null_values"],
        dtype=str,
        encoding=file_format["encoding"],
    )


def extract_prefix(client, bucket_name, prefix, file_format, engine, table_name, schema="raw"):
    objects = list(client.list_objects(bucket_name, prefix=prefix, recursive=True))

    if not objects:
        logger.warning(f"No objects found in bucket {bucket_name} under prefix {prefix}")
        return

    for obj in objects:
        file_name = os.path.basename(obj.object_name)
        if not file_name.endswith(".csv"):
            continue

        try:
            logger.info(f"Reading {obj.object_name} from MinIO bucket {bucket_name}")
            response = client.get_object(bucket_name, obj.object_name)
            data_bytes = response.read()
            response.close()
            response.release_conn()

            df = read_csv_bytes(data_bytes, file_format)
            df["source_file"] = file_name

            df.to_sql(
                table_name,
                engine,
                schema=schema,
                if_exists="append",
                index=False,
            )
            logger.info(f"Loaded {len(df)} rows from {file_name} into {schema}.{table_name}")

        except Exception as e:
            logger.error(f"Failed to process {obj.object_name} from MinIO: {e}")


def run_minio_extraction():
    logger.info("Starting MinIO extraction")
    config = load_config()
    engine = get_engine()
    client = get_minio_client(config)

    minio_config = config["storage"]["minio"]
    bucket_name = minio_config["bucket_name"]
    file_format = config["file_format"]

    extract_prefix(
        client, bucket_name, minio_config["employee_prefix"],
        file_format, engine, "employee_raw",
    )
    extract_prefix(
        client, bucket_name, minio_config["timesheet_prefix"],
        file_format, engine, "timesheet_raw",
    )

    logger.info("MinIO extraction finished")


if __name__ == "__main__":
    run_minio_extraction()