import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SCHEMA_DUMP_PATH = Path(__file__).resolve().parent / "bincom_test_converted.sql"


def _load_psycopg2():
    try:
        import psycopg2 as psycopg2_module
        import psycopg2.extras as psycopg2_extras_module
    except ModuleNotFoundError as import_error:
        raise RuntimeError(f"psycopg2 is not installed in this environment: {import_error}") from import_error

    return psycopg2_module, psycopg2_extras_module


def get_connection():
    psycopg2_module, _ = _load_psycopg2()

    return psycopg2_module.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "bincom_test"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def bootstrap_schema_from_dump():
    conn = None
    cur = None
    try:
        _, psycopg2_extras_module = _load_psycopg2()
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2_extras_module.RealDictCursor)

        cur.execute(
            """
            SELECT
                to_regclass('public.polling_unit') AS polling_unit,
                to_regclass('public.lga') AS lga,
                to_regclass('public.party') AS party,
                to_regclass('public.announced_pu_results') AS announced_pu_results,
                to_regclass('public.ward') AS ward,
                to_regclass('public.states') AS states
            """
        )
        schema_row = cur.fetchone() or {}
        if all(schema_row.values()):
            conn.commit()
            return False

        if not SCHEMA_DUMP_PATH.exists():
            raise RuntimeError(f"Schema dump not found at {SCHEMA_DUMP_PATH}")

        cur.execute(SCHEMA_DUMP_PATH.read_text(encoding="utf-8"))
        conn.commit()
        return True
    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise RuntimeError(f"Database bootstrap failed: {e}") from e
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def fetch_all(query: str, params: tuple = ()):
    conn = None
    cur = None
    try:
        _, psycopg2_extras_module = _load_psycopg2()
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2_extras_module.RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        raise RuntimeError(f"Database query failed: {e}") from e
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def execute_write(query: str, params: tuple = ()):
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
    except Exception as e:
        raise RuntimeError(f"Database write failed: {e}") from e
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
