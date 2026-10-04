"""
Cleans and validates the raw customers and transactions data.
Performs data-quality checks (nulls, duplicates, negative amounts,
invalid timestamps) and writes cleaned CSVs to data/processed/.
"""

import os
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def load_raw():
    customers = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    transactions = pd.read_csv(os.path.join(RAW_DIR, "transactions.csv"), parse_dates=["timestamp"])
    return customers, transactions


def quality_report(customers, transactions):
    print("--- Data Quality Report ---")
    print(f"Customers: {len(customers)} rows, {customers.duplicated('customer_id').sum()} duplicate IDs")
    print(f"Customer nulls:\n{customers.isnull().sum()[customers.isnull().sum() > 0]}")
    print(f"Transactions: {len(transactions)} rows, "
          f"{transactions.duplicated('transaction_id').sum()} duplicate IDs")
    print(f"Transaction nulls:\n{transactions.isnull().sum()[transactions.isnull().sum() > 0]}")
    print(f"Negative/zero amounts: {(transactions['amount'] <= 0).sum()}")
    orphan_txns = ~transactions["customer_id"].isin(customers["customer_id"])
    print(f"Transactions with unknown customer_id: {orphan_txns.sum()}")


def clean(customers, transactions):
    customers = customers.drop_duplicates("customer_id").dropna(subset=["customer_id"])
    transactions = transactions.drop_duplicates("transaction_id")
    transactions = transactions[transactions["amount"] > 0]
    transactions = transactions[transactions["customer_id"].isin(customers["customer_id"])]
    transactions = transactions.dropna(subset=["timestamp", "amount", "customer_id"])
    transactions = transactions.sort_values("timestamp").reset_index(drop=True)
    return customers, transactions


def main():
    customers, transactions = load_raw()
    quality_report(customers, transactions)

    customers_clean, transactions_clean = clean(customers, transactions)

    rows_dropped = len(transactions) - len(transactions_clean)
    print(f"\nRows dropped during cleaning: {rows_dropped}")

    customers_clean.to_csv(os.path.join(PROCESSED_DIR, "customers_clean.csv"), index=False)
    transactions_clean.to_csv(os.path.join(PROCESSED_DIR, "transactions_clean.csv"), index=False)

    print(f"Saved cleaned data: {len(customers_clean)} customers, {len(transactions_clean)} transactions")


if __name__ == "__main__":
    main()
