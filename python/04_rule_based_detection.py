"""
Rule-based anomaly detection layer.

Each rule encodes a domain heuristic a risk analyst would recognize.
A transaction can trigger multiple rules; the alert reasons are kept
as a readable list for the Power BI drill-down view. Rule weights are
additive and produce a bounded rule_score (0-100) that is later
blended with the statistical anomaly score in the risk scoring step.
"""

import os
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

RULES = [
    ("High velocity (1h)", lambda df: df["transaction_velocity_1h"] >= 4, 25),
    ("High velocity (24h)", lambda df: df["transaction_velocity_24h"] >= 8, 15),
    ("Extreme amount deviation", lambda df: df["amount_zscore"] >= 3, 25),
    ("Large jump vs average spend", lambda df: df["amount_ratio_to_avg"] >= 4, 20),
    ("New device used", lambda df: df["is_new_device_for_customer"] == 1, 15),
    ("New geography for customer", lambda df: df["is_new_city_for_customer"] == 1, 15),
    ("Foreign country transaction", lambda df: df["is_foreign_transaction"] == 1, 10),
    ("Odd-hour transaction (12am-5am)", lambda df: df["is_odd_hour"] == 1, 10),
    ("Rapid re-transaction (<2 min)", lambda df: (df["hours_since_last_txn"] * 60) < 2, 15),
]


def build_alert_reasons(df):
    reason_lists = [[] for _ in range(len(df))]
    for name, condition, _ in RULES:
        triggered = condition(df).to_numpy()
        for i, t in enumerate(triggered):
            if t:
                reason_lists[i].append(name)
    return ["; ".join(r) if r else "No rule triggered" for r in reason_lists]


def precision_recall_summary(df):
    tp = ((df["rule_flagged"] == 1) & (df["is_fraud_synthetic"] == 1)).sum()
    fp = ((df["rule_flagged"] == 1) & (df["is_fraud_synthetic"] == 0)).sum()
    fn = ((df["rule_flagged"] == 0) & (df["is_fraud_synthetic"] == 1)).sum()
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    print(f"Rule-based precision: {precision:.3f}, recall: {recall:.3f} "
          f"(evaluated against synthetic ground-truth labels, for validation only)")


def main():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "transactions_features.csv"), parse_dates=["timestamp"])

    df["rule_score"] = 0
    for _, condition, weight in RULES:
        df["rule_score"] += condition(df).astype(int) * weight
    df["rule_score"] = df["rule_score"].clip(0, 100)
    df["alert_reasons"] = build_alert_reasons(df)
    df["rule_flagged"] = (df["rule_score"] >= 45).astype(int)

    output_path = os.path.join(PROCESSED_DIR, "transactions_rules.csv")
    df.to_csv(output_path, index=False)

    print(f"Transactions flagged by rules: {df['rule_flagged'].sum()} "
          f"({df['rule_flagged'].mean() * 100:.2f}%)")
    precision_recall_summary(df)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
