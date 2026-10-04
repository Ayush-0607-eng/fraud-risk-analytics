"""
Builds fraud_analytics.db (SQLite) from sql/01_schema.sql and loads the
raw customers/transactions data plus the final scored dataset produced
by the analysis pipeline. Run this after 08_export_powerbi.py, or run
python/run_pipeline.py which sequences everything correctly.

SQLite is used because it requires no server, no installation beyond
Python's standard library, and no cost, matching the project's
zero-budget, fully reproducible requirement. The schema is written in
standard SQL, so it can be pointed at PostgreSQL or MySQL with only
minor syntax changes if preferred.
"""

import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
SQL_DIR = os.path.join(BASE_DIR, "sql")
DB_PATH = os.path.join(BASE_DIR, "data", "fraud_analytics.db")


def build_schema(conn):
    with open(os.path.join(SQL_DIR, "01_schema.sql")) as f:
        conn.executescript(f.read())


def load_table(conn, csv_path, table_name):
    df = pd.read_csv(csv_path)
    df.to_sql(table_name, conn, if_exists="append", index=False)
    return len(df)


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    build_schema(conn)

    n_customers = load_table(conn, os.path.join(RAW_DIR, "customers.csv"), "customers")
    n_transactions = load_table(conn, os.path.join(RAW_DIR, "transactions.csv"), "transactions")
    n_scored = load_table(
        conn, os.path.join(PROCESSED_DIR, "powerbi_transactions.csv"), "risk_scored_transactions"
    )

    conn.commit()
    conn.close()

    print(f"Built {DB_PATH}")
    print(f"  customers: {n_customers} rows")
    print(f"  transactions: {n_transactions} rows")
    print(f"  risk_scored_transactions: {n_scored} rows")


if __name__ == "__main__":
    main()
