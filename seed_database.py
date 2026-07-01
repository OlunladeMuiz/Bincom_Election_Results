from db import bootstrap_schema_from_dump


def main():
    try:
        seeded = bootstrap_schema_from_dump()
    except RuntimeError as err:
        print(str(err))
        raise

    if seeded:
        print("Database schema imported from bincom_test_converted.sql")
    else:
        print("Database schema already exists; skipping import")


if __name__ == "__main__":
    main()
