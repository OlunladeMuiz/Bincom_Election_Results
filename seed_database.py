"""
seed_database.py

Pre-deploy script that imports the converted PostgreSQL dump into the
Railway-managed database if the schema has not already been loaded.

Run automatically via railway.toml preDeployCommand:
    python seed_database.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SCHEMA_DUMP_PATH = Path(__file__).resolve().parent / "bincom_test_converted.sql"


def bootstrap_schema_from_dump() -> None:
    """
    Execute the SQL dump against the configured PostgreSQL database.

    Skips execution if the `polling_unit` table already exists, so
    re-deploys do not wipe and re-import data unnecessarily.
    """
    try:
        import psycopg2
    except ModuleNotFoundError as exc:
        print(f"[seed] ERROR: psycopg2 is not installed — {exc}", file=sys.stderr)
        sys.exit(1)

    conn_kwargs = dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "bincom_test"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )

    try:
        conn = psycopg2.connect(**conn_kwargs)
    except Exception as exc:
        print(f"[seed] ERROR: Could not connect to database — {exc}", file=sys.stderr)
        sys.exit(1)

    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            # Check whether the schema has already been loaded.
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name   = 'polling_unit'
                )
                """
            )
            already_loaded: bool = cur.fetchone()[0]

        if already_loaded:
            print("[seed] Schema already present — skipping import.")
            return

        if not SCHEMA_DUMP_PATH.exists():
            print(
                f"[seed] ERROR: Dump file not found at {SCHEMA_DUMP_PATH}",
                file=sys.stderr,
            )
            sys.exit(1)

        sql = SCHEMA_DUMP_PATH.read_text(encoding="utf-8")

        print(f"[seed] Importing schema from {SCHEMA_DUMP_PATH.name} …")
        with conn.cursor() as cur:
            cur.execute(sql)

        print("[seed] Database seeded successfully.")

    except Exception as exc:
        print(f"[seed] ERROR: Failed to seed database — {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    bootstrap_schema_from_dump()
