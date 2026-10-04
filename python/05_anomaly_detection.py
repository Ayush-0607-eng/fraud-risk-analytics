"""
Unsupervised anomaly detection with Isolation Forest.

Fraud labels are NOT used as a training input anywhere in this step;
the model only sees behavioral features, which is what makes it able
to catch fraud patterns that were not explicitly written as rules.
The synthetic label is used only afterward, to evaluate how well the
unsupervised score aligns with known fraud.
"""

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

FEATURE_COLUMNS = [
    "amount",
    "transaction_velocity_1h",
    "transaction_velocity_24h",
    "amount_zscore",
    "amount_ratio_to_avg",
    "is_new_city_for_customer",
    "is_new_device_for_customer",
    "is_unusual_category_for_customer",
    "is_odd_hour",
    "is_foreign_transaction",
    "hours_since_last_txn",
]

CONTAMINATION = 0.01
RANDOM_STATE = 42


def main():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "transactions_rules.csv"), parse_dates=["timestamp"])

    X = df[FEATURE_COLUMNS].copy()
    X["hours_since_last_txn"] = X["hours_since_last_txn"].clip(upper=168)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    raw_scores = model.decision_function(X_scaled)
    df["anomaly_score_raw"] = raw_scores
    df["is_anomaly"] = (model.predict(X_scaled) == -1).astype(int)

    min_s, max_s = raw_scores.min(), raw_scores.max()
    df["anomaly_score"] = 100 * (max_s - raw_scores) / (max_s - min_s)

    output_path = os.path.join(PROCESSED_DIR, "transactions_anomaly.csv")
    df.to_csv(output_path, index=False)

    evaluate(df)
    print(f"Saved to {output_path}")


def evaluate(df):
    tp = ((df["is_anomaly"] == 1) & (df["is_fraud_synthetic"] == 1)).sum()
    fp = ((df["is_anomaly"] == 1) & (df["is_fraud_synthetic"] == 0)).sum()
    fn = ((df["is_anomaly"] == 0) & (df["is_fraud_synthetic"] == 1)).sum()
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    print(f"Isolation Forest flagged: {df['is_anomaly'].sum()} transactions "
          f"({df['is_anomaly'].mean() * 100:.2f}%)")
    print(f"Isolation Forest precision: {precision:.3f}, recall: {recall:.3f} "
          f"(evaluated against synthetic ground-truth labels, for validation only)")

    overlap = ((df["is_anomaly"] == 1) & (df["rule_flagged"] == 1)).sum()
    print(f"Overlap between rule-flagged and model-flagged transactions: {overlap}")


if __name__ == "__main__":
    main()
