"""
Engineers behavioral and transaction-level risk features:

- transaction_velocity_1h / 24h: number of transactions by the same
  customer in the preceding 1h / 24h window.
- amount_zscore: deviation of the transaction amount from the
  customer's own historical mean/std (computed on prior transactions
  only, so there is no look-ahead leakage).
- amount_ratio_to_avg: transaction amount vs customer's running average.
- is_new_geography: transaction city not previously seen for this
  customer, or transaction country differs from home country.
- is_new_device: device_id not previously seen for this customer.
- hours_since_last_txn / is_odd_hour: timing behavior features.
- merchant_category_change: whether the category differs from the
  customer's most frequent category so far.

All rolling/historical statistics use only past transactions relative
to each row (expanding windows computed after sorting by time), which
is what makes these features usable in a real-time fraud system.
"""

import os
import numpy as np
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

ODD_HOURS = set(range(0, 5))


def load_clean():
    customers = pd.read_csv(os.path.join(PROCESSED_DIR, "customers_clean.csv"))
    transactions = pd.read_csv(os.path.join(PROCESSED_DIR, "transactions_clean.csv"), parse_dates=["timestamp"])
    return customers, transactions


def compute_velocity(transactions):
    transactions = transactions.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)
    vel_1h = np.zeros(len(transactions), dtype=int)
    vel_24h = np.zeros(len(transactions), dtype=int)

    for _, idx in transactions.groupby("customer_id").groups.items():
        idx = list(idx)
        times = transactions.loc[idx, "timestamp"].values
        times = pd.to_datetime(times)
        start_1h = 0
        start_24h = 0
        for i in range(len(idx)):
            while times[i] - times[start_1h] > pd.Timedelta(hours=1):
                start_1h += 1
            while times[i] - times[start_24h] > pd.Timedelta(hours=24):
                start_24h += 1
            vel_1h[idx[i]] = i - start_1h + 1
            vel_24h[idx[i]] = i - start_24h + 1

    transactions["transaction_velocity_1h"] = vel_1h
    transactions["transaction_velocity_24h"] = vel_24h
    return transactions


def compute_amount_behavior(transactions):
    transactions = transactions.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)
    grp = transactions.groupby("customer_id")["amount"]

    expanding_mean = grp.apply(lambda s: s.shift().expanding().mean())
    expanding_std = grp.apply(lambda s: s.shift().expanding().std())

    expanding_mean.index = transactions.index
    expanding_std.index = transactions.index

    transactions["hist_avg_amount"] = expanding_mean.fillna(transactions["amount"])
    transactions["hist_std_amount"] = expanding_std.fillna(0)

    # Floor the std at 10% of the historical mean (min 5) so customers with a
    # very stable early history don't produce division-by-near-zero blow-ups.
    min_std = np.maximum(transactions["hist_avg_amount"] * 0.10, 5)
    safe_std = transactions["hist_std_amount"].clip(lower=min_std)
    transactions["amount_zscore"] = (
        (transactions["amount"] - transactions["hist_avg_amount"]) / safe_std
    ).clip(-10, 10).fillna(0)
    transactions["amount_ratio_to_avg"] = (
        transactions["amount"] / transactions["hist_avg_amount"].replace(0, np.nan)
    ).fillna(1)
    return transactions


def compute_geography_and_device(transactions):
    transactions = transactions.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)
    is_new_city = np.zeros(len(transactions), dtype=int)
    is_new_device = np.zeros(len(transactions), dtype=int)
    is_new_category = np.zeros(len(transactions), dtype=int)

    for _, idx in transactions.groupby("customer_id").groups.items():
        idx = list(idx)
        seen_cities, seen_devices, cat_counts = set(), set(), {}
        for i in idx:
            city = transactions.at[i, "transaction_city"]
            device = transactions.at[i, "device_id"]
            category = transactions.at[i, "merchant_category"]

            is_new_city[i] = 0 if city in seen_cities else (1 if seen_cities else 0)
            is_new_device[i] = 0 if device in seen_devices else (1 if seen_devices else 0)
            if cat_counts:
                top_category = max(cat_counts, key=cat_counts.get)
                is_new_category[i] = int(category != top_category)

            seen_cities.add(city)
            seen_devices.add(device)
            cat_counts[category] = cat_counts.get(category, 0) + 1

    transactions["is_new_city_for_customer"] = is_new_city
    transactions["is_new_device_for_customer"] = is_new_device
    transactions["is_unusual_category_for_customer"] = is_new_category
    return transactions


def compute_timing_features(transactions, customers):
    transactions = transactions.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)
    transactions["hours_since_last_txn"] = (
        transactions.groupby("customer_id")["timestamp"].diff().dt.total_seconds() / 3600
    ).fillna(9999)
    transactions["hour_of_day"] = transactions["timestamp"].dt.hour
    transactions["is_odd_hour"] = transactions["hour_of_day"].isin(ODD_HOURS).astype(int)

    transactions = transactions.merge(customers[["customer_id", "home_country"]], on="customer_id", how="left")
    transactions["is_foreign_transaction"] = (
        transactions["transaction_country"] != transactions["home_country"]
    ).astype(int)
    return transactions


def main():
    customers, transactions = load_clean()

    transactions = compute_velocity(transactions)
    transactions = compute_amount_behavior(transactions)
    transactions = compute_geography_and_device(transactions)
    transactions = compute_timing_features(transactions, customers)

    output_path = os.path.join(PROCESSED_DIR, "transactions_features.csv")
    transactions.to_csv(output_path, index=False)

    print(f"Engineered features for {len(transactions)} transactions")
    print("Feature columns added:")
    new_cols = [
        "transaction_velocity_1h", "transaction_velocity_24h", "amount_zscore",
        "amount_ratio_to_avg", "is_new_city_for_customer", "is_new_device_for_customer",
        "is_unusual_category_for_customer", "hours_since_last_txn", "is_odd_hour",
        "is_foreign_transaction",
    ]
    for c in new_cols:
        print(f"  - {c}")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
