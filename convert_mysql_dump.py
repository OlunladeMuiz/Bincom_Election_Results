from pathlib import Path
import re


SOURCE_PATH = Path(r"C:\Users\HP USER\Downloads\bincom_test.sql")
OUTPUT_PATH = Path(__file__).resolve().parent / "bincom_test_converted.sql"

AUTO_INCREMENT_COLUMNS = [
    ("agentname", "name_id"),
    ("announced_lga_results", "result_id"),
    ("announced_pu_results", "result_id"),
    ("announced_state_results", "result_id"),
    ("announced_ward_results", "result_id"),
    ("lga", "uniqueid"),
    ("party", "id"),
    ("polling_unit", "uniqueid"),
    ("ward", "uniqueid"),
]


def convert_mysql_dump(sql: str) -> str:
    sql = re.sub(r"^\s*SET SQL_MODE=.*?;\s*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"^\s*/\*!.*?\*/;\s*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"^\s*LOCK TABLES .*?;\s*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"^\s*UNLOCK TABLES;\s*$", "", sql, flags=re.MULTILINE)

    sql = sql.replace("`", '"')
    sql = sql.replace("'0000-00-00 00:00:00'", "NULL")
    sql = sql.replace("'0000-00-00'", "NULL")

    sql = re.sub(
        r'"([^"]+)"\s+int\(\d+\)\s+NOT NULL\s+AUTO_INCREMENT',
        r'"\1" SERIAL NOT NULL',
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"\bint\(\d+\)", "integer", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bdatetime\b", "timestamp", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bdouble\b", "double precision", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\btinyint\(\d+\)", "smallint", sql, flags=re.IGNORECASE)

    sql = re.sub(
        r"\)\s+ENGINE\s*=\s*\w+[^;]*;",
        ");",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(r",\s*\n\s*KEY\s+\"[^\"]+\"\s+\([^)]+\)", "", sql)
    sql = re.sub(r",\s*\n\s*UNIQUE KEY\s+\"[^\"]+\"\s+\([^)]+\)", "", sql)

    # The MySQL dump uses invalid zero timestamps in required audit columns.
    # PostgreSQL cannot store those values, so date columns must accept NULL.
    sql = re.sub(
        r'("date_entered"\s+timestamp)\s+NOT NULL',
        r"\1 NULL",
        sql,
        flags=re.IGNORECASE,
    )

    sequence_resets = ["", "-- Reset SERIAL sequences after importing explicit ids."]
    for table_name, column_name in AUTO_INCREMENT_COLUMNS:
        sequence_resets.append(
            "SELECT setval("
            f"pg_get_serial_sequence('\"{table_name}\"', '{column_name}'), "
            f"COALESCE((SELECT MAX(\"{column_name}\") FROM \"{table_name}\"), 1), true"
            ");"
        )

    return sql.rstrip() + "\n\n" + "\n".join(sequence_resets) + "\n"


if __name__ == "__main__":
    source_sql = SOURCE_PATH.read_text(encoding="latin1")
    converted_sql = convert_mysql_dump(source_sql)
    OUTPUT_PATH.write_text(converted_sql, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
