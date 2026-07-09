"""
Migration 001: Initial schema setup.

Creates all tables in the raw, staging, curated, and quality schemas
following the Medallion architecture (Bronze → Silver → Gold).

Usage:
    python database/migrations/001_initial_schema.py [--down]

Apply:
    python database/migrations/001_initial_schema.py

Rollback:
    python database/migrations/001_initial_schema.py --down
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import text
from etl.utils.db_connection import get_engine, load_config
from etl.utils.logger import get_logger

logger = get_logger("migration_001")

SCHEMA_SQL = os.path.join(os.path.dirname(__file__), "..", "schema", "init_schema.sql")


def apply():
    logger.info("Applying migration 001: initial schema")
    engine = get_engine()

    with open(SCHEMA_SQL, "r") as f:
        sql = f.read()

    with engine.begin() as conn:
        conn.execute(text(sql))

    logger.info("Migration 001 applied successfully")


def rollback():
    logger.info("Rolling back migration 001")
    engine = get_engine()

    schemas = ["quality", "curated", "staging", "raw"]

    with engine.begin() as conn:
        for schema in schemas:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))

    logger.info("Migration 001 rolled back successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--down", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.down:
        rollback()
    else:
        apply()
