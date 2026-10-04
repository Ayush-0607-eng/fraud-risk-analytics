"""
Builds the final flat, denormalized dataset for Power BI: joins
customer attributes onto the scored transactions and writes it to
data/processed/powerbi_dataset.csv together with a small customer-level
summary table for the dashboard's customer drill-down view.
"""

import os
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

TXN_COLUMNS = [
    "transaction_id", "customer_id", "timestamp", "amount", "currency",
    "merchant_category", "transaction_type", "channel", "transaction_city",
    "transaction_country", "device_id",
    "transaction_velocity_1h", "transaction_velocity_24h",
    "amount_zscore", "amount_ratio_to_avg",
    "is_new_city_for_customer", "is_new_device_for_customer",
    "is_unusual_category_for_customer", "is_odd_hour", "is_foreign_transaction",
    "rule_score", "alert_reasons", "rule_flagged",
    "anomaly_score", "is_anomaly",
    "risk_score", "risk_category", "risk_flagged",
    "is_fraud_synthetic",
]

CUSTOMER_COLUMNS = [
    "customer_id", "signup_date", "age", "gender", "home_city", "home_country",
    "account_type", "customer_segment",
]


def build_transactions_export():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "risk_scores.csv"), parse_dates=["timestamp"])
    customers = pd.read_csv(os.path.join(PROCESSED_DIR, "customers_clean.csv"))[CUSTOMER_COLUMNS]

    export = df[TXN_COLUMNS].merge(customers, on="customer_id", how="left")
    float_cols = export.select_dtypes(include="float").columns
    export[float_cols] = export[float_cols].round(3)
    export["transaction_date"] = export["timestamp"].dt.date
    export["transaction_month"] = export["timestamp"].dt.to_period("M").astype(str)
    export["transaction_week"] = export["timestamp"].dt.to_period("W").astype(str)
    export["transaction_hour"] = export["timestamp"].dt.hour
    export["transaction_weekday"] = export["timestamp"].dt.day_name()
    return export


def build_customer_summary(export):
    agg = export.groupby("customer_id").agg(
        total_transactions=("transaction_id", "count"),
        total_amount=("amount", "sum"),
        avg_amount=("amount", "mean"),
        max_risk_score=("risk_score", "max"),
        avg_risk_score=("risk_score", "mean"),
        critical_alerts=("risk_category", lambda s: (s == "Critical").sum()),
        high_alerts=("risk_category", lambda s: (s == "High").sum()),
        flagged_transactions=("risk_flagged", "sum"),
        confirmed_fraud_transactions=("is_fraud_synthetic", "sum"),
    ).reset_index()

    customer_attrs = export.drop_duplicates("customer_id")[
        ["customer_id", "customer_segment", "account_type", "home_city", "age", "gender"]
    ]
    summary = agg.merge(customer_attrs, on="customer_id", how="left")
    summary["risk_tier"] = pd.cut(
        summary["max_risk_score"], bins=[-0.01, 20, 40, 60, 100],
        labels=["Low", "Medium", "High", "Critical"]
    )
    return summary


def build_date_dimension(export):
    dates = pd.date_range(export["timestamp"].min().date(), export["timestamp"].max().date(), freq="D")
    dim = pd.DataFrame({"date": dates})
    dim["year"] = dim["date"].dt.year
    dim["month"] = dim["date"].dt.month
    dim["month_name"] = dim["date"].dt.month_name()
    dim["week"] = dim["date"].dt.isocalendar().week
    dim["weekday"] = dim["date"].dt.day_name()
    dim["is_weekend"] = dim["date"].dt.weekday >= 5
    return dim


def main():
    export = build_transactions_export()
    customer_summary = build_customer_summary(export)
    date_dim = build_date_dimension(export)

    export.to_csv(os.path.join(PROCESSED_DIR, "powerbi_transactions.csv"), index=False)
    customer_summary.to_csv(os.path.join(PROCESSED_DIR, "powerbi_customer_summary.csv"), index=False)
    date_dim.to_csv(os.path.join(PROCESSED_DIR, "powerbi_date_dimension.csv"), index=False)

    print(f"powerbi_transactions.csv: {len(export)} rows, {len(export.columns)} columns")
    print(f"powerbi_customer_summary.csv: {len(customer_summary)} rows")
    print(f"powerbi_date_dimension.csv: {len(date_dim)} rows")


if __name__ == "__main__":
    main()
