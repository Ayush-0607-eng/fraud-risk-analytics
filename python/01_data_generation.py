"""
Generates synthetic customers and transactions datasets for the
Financial Fraud & Risk Intelligence Analytics project.

The data is fully synthetic. Fraud patterns are injected deliberately
(velocity attacks, card testing, geographic anomalies, amount anomalies)
so the downstream rule-based and anomaly-detection logic has real signal
to find. A ground-truth label is kept only for model evaluation and is
not used as an input feature anywhere in the detection pipeline.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

SEED = 42
np.random.seed(SEED)
rng = np.random.default_rng(SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

N_CUSTOMERS = 800
N_MONTHS = 5
START_DATE = datetime(2025, 4, 1)
END_DATE = START_DATE + timedelta(days=30 * N_MONTHS)

CITIES = {
    "Mumbai": "India", "Delhi": "India", "Bengaluru": "India", "Chennai": "India",
    "Hyderabad": "India", "Pune": "India", "Kolkata": "India", "Ahmedabad": "India",
    "Jaipur": "India", "Lucknow": "India", "Singapore": "Singapore", "Dubai": "UAE",
    "London": "UK", "New York": "USA", "Bangkok": "Thailand"
}
HOME_CITIES = [c for c in CITIES if CITIES[c] == "India"]
FOREIGN_CITIES = [c for c in CITIES if CITIES[c] != "India"]

MERCHANT_CATEGORIES = [
    "Grocery", "Electronics", "Travel", "Dining", "Utilities", "Fashion",
    "Healthcare", "Entertainment", "Fuel", "Education", "Jewellery", "Transfer"
]
CHANNELS = ["online", "pos", "atm", "mobile_app"]
TXN_TYPES = ["purchase", "transfer", "withdrawal", "bill_payment"]
ACCOUNT_TYPES = ["Savings", "Checking", "Premium"]
SEGMENTS = ["Retail", "Premium", "Business"]
GENDERS = ["Male", "Female", "Other"]


def generate_customers():
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        signup_date = START_DATE - timedelta(days=int(rng.integers(30, 1500)))
        age = int(np.clip(rng.normal(38, 12), 18, 75))
        segment = rng.choice(SEGMENTS, p=[0.72, 0.18, 0.10])
        account_type = rng.choice(ACCOUNT_TYPES, p=[0.55, 0.30, 0.15])
        home_city = rng.choice(HOME_CITIES)
        avg_amount = float(np.clip(rng.normal(
            2500 if segment == "Retail" else (6000 if segment == "Premium" else 15000),
            1200), 200, 90000))
        avg_txns_per_week = float(np.clip(rng.normal(3.5, 1.5), 0.5, 15))
        rows.append({
            "customer_id": f"CUST{i:05d}",
            "signup_date": signup_date.date().isoformat(),
            "age": age,
            "gender": rng.choice(GENDERS, p=[0.49, 0.49, 0.02]),
            "home_city": home_city,
            "home_country": "India",
            "account_type": account_type,
            "customer_segment": segment,
            "baseline_avg_amount": round(avg_amount, 2),
            "baseline_txns_per_week": round(avg_txns_per_week, 2),
        })
    return pd.DataFrame(rows)


def random_timestamp(day):
    hour_weights = np.array([
        0.3, 0.2, 0.15, 0.1, 0.1, 0.2, 0.5, 1.0, 1.5, 1.8, 1.9, 2.0,
        2.1, 2.0, 1.8, 1.7, 1.8, 2.0, 2.3, 2.2, 1.8, 1.3, 0.8, 0.5
    ])
    hour_weights = hour_weights / hour_weights.sum()
    hour = rng.choice(24, p=hour_weights)
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    return day.replace(hour=int(hour), minute=minute, second=second)


def generate_normal_transactions(customers):
    txns = []
    txn_counter = 1
    for _, cust in customers.iterrows():
        n_weeks = N_MONTHS * 4.3
        n_txns = int(max(1, rng.poisson(cust["baseline_txns_per_week"] * n_weeks)))
        active_days = sorted(rng.integers(0, (END_DATE - START_DATE).days, size=n_txns))
        device_pool = [f"DEV-{cust['customer_id']}-{k}" for k in range(rng.integers(1, 3))]
        for d in active_days:
            day = START_DATE + timedelta(days=int(d))
            ts = random_timestamp(day)
            amount = float(np.clip(rng.lognormal(
                mean=np.log(max(cust["baseline_avg_amount"], 50)), sigma=0.6), 30, 250000))
            travel = rng.random() < 0.03
            city = rng.choice(FOREIGN_CITIES) if travel else cust["home_city"]
            country = CITIES[city]
            txns.append({
                "transaction_id": f"TXN{txn_counter:07d}",
                "customer_id": cust["customer_id"],
                "timestamp": ts.isoformat(sep=" "),
                "amount": round(amount, 2),
                "currency": "INR",
                "merchant_category": rng.choice(MERCHANT_CATEGORIES),
                "transaction_type": rng.choice(TXN_TYPES, p=[0.7, 0.15, 0.1, 0.05]),
                "channel": rng.choice(CHANNELS, p=[0.4, 0.35, 0.1, 0.15]),
                "transaction_city": city,
                "transaction_country": country,
                "device_id": rng.choice(device_pool),
                "is_fraud_synthetic": 0,
            })
            txn_counter += 1
    return pd.DataFrame(txns), txn_counter


def inject_fraud(customers, txn_counter):
    fraud_customers = customers.sample(frac=0.06, random_state=SEED)
    fraud_rows = []
    for _, cust in fraud_customers.iterrows():
        pattern = rng.choice(["velocity_attack", "card_testing", "geo_anomaly", "amount_spike"])
        event_day = START_DATE + timedelta(days=int(rng.integers(10, (END_DATE - START_DATE).days - 5)))
        fraud_device = f"DEV-FRAUD-{cust['customer_id']}-{rng.integers(1000, 9999)}"

        if pattern == "velocity_attack":
            base_ts = event_day.replace(hour=int(rng.integers(1, 4)), minute=int(rng.integers(0, 59)))
            n = int(rng.integers(5, 12))
            for k in range(n):
                ts = base_ts + timedelta(minutes=int(rng.integers(1, 6)) * k)
                amount = float(np.clip(rng.normal(cust["baseline_avg_amount"] * 1.8, 800), 200, 150000))
                fraud_rows.append(_row(txn_counter, cust, ts, amount, "Transfer", "transfer", "online",
                                        rng.choice(FOREIGN_CITIES), fraud_device))
                txn_counter += 1

        elif pattern == "card_testing":
            base_ts = event_day.replace(hour=int(rng.integers(0, 23)), minute=0)
            n = int(rng.integers(6, 15))
            for k in range(n):
                ts = base_ts + timedelta(seconds=int(rng.integers(20, 180)) * k)
                amount = float(np.clip(rng.normal(45, 20), 5, 150))
                fraud_rows.append(_row(txn_counter, cust, ts, amount, "Electronics", "purchase", "online",
                                        cust["home_city"], fraud_device))
                txn_counter += 1
            big_ts = base_ts + timedelta(minutes=45)
            big_amount = float(np.clip(rng.normal(cust["baseline_avg_amount"] * 6, 2000), 3000, 200000))
            fraud_rows.append(_row(txn_counter, cust, big_ts, big_amount, "Electronics", "purchase", "online",
                                    cust["home_city"], fraud_device))
            txn_counter += 1

        elif pattern == "geo_anomaly":
            ts = event_day.replace(hour=int(rng.integers(0, 5)), minute=int(rng.integers(0, 59)))
            foreign_city = rng.choice(FOREIGN_CITIES)
            amount = float(np.clip(rng.normal(cust["baseline_avg_amount"] * 4, 1500), 1000, 180000))
            fraud_rows.append(_row(txn_counter, cust, ts, amount, "Jewellery", "purchase", "pos",
                                    foreign_city, fraud_device))
            txn_counter += 1
            ts2 = ts + timedelta(minutes=int(rng.integers(10, 40)))
            amount2 = float(np.clip(rng.normal(cust["baseline_avg_amount"] * 3, 1200), 800, 150000))
            fraud_rows.append(_row(txn_counter, cust, ts2, amount2, "Electronics", "purchase", "online",
                                    foreign_city, fraud_device))
            txn_counter += 1

        else:  # amount_spike
            ts = event_day.replace(hour=int(rng.integers(9, 22)), minute=int(rng.integers(0, 59)))
            amount = float(np.clip(rng.normal(cust["baseline_avg_amount"] * 9, 3000), 5000, 300000))
            fraud_rows.append(_row(txn_counter, cust, ts, amount, "Transfer", "transfer", "mobile_app",
                                    cust["home_city"], fraud_device))
            txn_counter += 1

    return pd.DataFrame(fraud_rows), txn_counter


def _row(counter, cust, ts, amount, category, txn_type, channel, city, device):
    return {
        "transaction_id": f"TXN{counter:07d}",
        "customer_id": cust["customer_id"],
        "timestamp": ts.isoformat(sep=" "),
        "amount": round(float(amount), 2),
        "currency": "INR",
        "merchant_category": category,
        "transaction_type": txn_type,
        "channel": channel,
        "transaction_city": city,
        "transaction_country": CITIES[city],
        "device_id": device,
        "is_fraud_synthetic": 1,
    }


def main():
    customers = generate_customers()
    normal_txns, txn_counter = generate_normal_transactions(customers)
    fraud_txns, _ = inject_fraud(customers, txn_counter)

    all_txns = pd.concat([normal_txns, fraud_txns], ignore_index=True)
    all_txns["timestamp"] = pd.to_datetime(all_txns["timestamp"])
    all_txns = all_txns.sort_values("timestamp").reset_index(drop=True)
    all_txns["transaction_id"] = [f"TXN{i:07d}" for i in range(1, len(all_txns) + 1)]

    customers_public = customers.drop(columns=["baseline_avg_amount", "baseline_txns_per_week"])

    customers_public.to_csv(os.path.join(OUTPUT_DIR, "customers.csv"), index=False)
    all_txns.to_csv(os.path.join(OUTPUT_DIR, "transactions.csv"), index=False)

    print(f"Customers generated: {len(customers_public)}")
    print(f"Transactions generated: {len(all_txns)}")
    print(f"Fraud transactions: {all_txns['is_fraud_synthetic'].sum()} "
          f"({all_txns['is_fraud_synthetic'].mean() * 100:.2f}%)")


if __name__ == "__main__":
    main()
