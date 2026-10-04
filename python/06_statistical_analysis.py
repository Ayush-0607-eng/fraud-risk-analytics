"""
Combines the rule-based score and the Isolation Forest anomaly score
into a single blended risk_score, assigns risk categories, and runs
statistical validation:

- Model comparison: rule-based vs anomaly-based vs blended precision/recall.
- Welch's t-test comparing transaction amounts for fraud vs non-fraud.
- Chi-square test of independence between risk category and channel.
- 95% confidence interval on the overall fraud rate.
- Correlation matrix of the numeric risk features.

Findings are written to outputs/reports/statistical_summary.txt and are
strictly derived from the computed data (no hard-coded conclusions).
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
REPORTS_DIR = os.path.join(BASE_DIR, "outputs", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

RISK_WEIGHTS = {"rule": 0.5, "anomaly": 0.5}

# Fixed thresholds on the 0-100 blended risk_score, chosen by evaluating
# precision/recall/F1 against the synthetic ground-truth labels across a
# threshold sweep (see docs/notebooks history). They balance a workable
# investigation queue size against fraud recall.
RISK_CUTS = {"medium": 20, "high": 40, "critical": 60}


def assign_risk_category(score):
    if score >= RISK_CUTS["critical"]:
        return "Critical"
    if score >= RISK_CUTS["high"]:
        return "High"
    if score >= RISK_CUTS["medium"]:
        return "Medium"
    return "Low"


def combined_score_and_categories(df):
    df["risk_score"] = (
        RISK_WEIGHTS["rule"] * df["rule_score"] + RISK_WEIGHTS["anomaly"] * df["anomaly_score"]
    ).round(2)
    df["risk_category"] = df["risk_score"].apply(assign_risk_category)
    return df, RISK_CUTS


def evaluate_method(df, flag_col, name, lines):
    tp = ((df[flag_col] == 1) & (df["is_fraud_synthetic"] == 1)).sum()
    fp = ((df[flag_col] == 1) & (df["is_fraud_synthetic"] == 0)).sum()
    fn = ((df[flag_col] == 0) & (df["is_fraud_synthetic"] == 1)).sum()
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    flag_rate = df[flag_col].mean() * 100
    line = (f"{name:<28} flag_rate={flag_rate:6.2f}%  precision={precision:.3f}  "
            f"recall={recall:.3f}  f1={f1:.3f}")
    print(line)
    lines.append(line)


def amount_ttest(df, lines):
    fraud_amounts = df.loc[df["is_fraud_synthetic"] == 1, "amount"]
    normal_amounts = df.loc[df["is_fraud_synthetic"] == 0, "amount"]
    t_stat, p_value = stats.ttest_ind(fraud_amounts, normal_amounts, equal_var=False)
    line = (f"\nWelch's t-test on transaction amount (fraud vs non-fraud):\n"
            f"  fraud mean = {fraud_amounts.mean():.2f}, non-fraud mean = {normal_amounts.mean():.2f}\n"
            f"  t = {t_stat:.3f}, p = {p_value:.6f} -> "
            f"{'statistically significant difference' if p_value < 0.05 else 'no significant difference'} "
            f"at alpha=0.05")
    print(line)
    lines.append(line)


def fraud_rate_confidence_interval(df, lines):
    n = len(df)
    p = df["is_fraud_synthetic"].mean()
    se = np.sqrt(p * (1 - p) / n)
    ci_low, ci_high = p - 1.96 * se, p + 1.96 * se
    line = (f"\nOverall fraud rate: {p * 100:.3f}% "
            f"(95% CI: {ci_low * 100:.3f}% - {ci_high * 100:.3f}%, n={n})")
    print(line)
    lines.append(line)


def channel_chi_square(df, lines):
    contingency = pd.crosstab(df["risk_category"], df["channel"])
    chi2, p_value, dof, _ = stats.chi2_contingency(contingency)
    line = (f"\nChi-square test: risk_category vs channel\n"
            f"  chi2 = {chi2:.2f}, dof = {dof}, p = {p_value:.6f} -> "
            f"{'significant association' if p_value < 0.05 else 'no significant association'} "
            f"at alpha=0.05")
    print(line)
    lines.append(line)


def correlation_summary(df, lines):
    numeric_cols = [
        "amount", "transaction_velocity_1h", "transaction_velocity_24h", "amount_zscore",
        "amount_ratio_to_avg", "is_new_city_for_customer", "is_new_device_for_customer",
        "is_odd_hour", "is_foreign_transaction", "rule_score", "anomaly_score", "risk_score",
    ]
    corr = df[numeric_cols].corr(numeric_only=True)["risk_score"].sort_values(ascending=False)
    line = "\nCorrelation of each feature with final risk_score:\n" + corr.drop("risk_score").to_string()
    print(line)
    lines.append(line)
    return corr


def main():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "transactions_anomaly.csv"), parse_dates=["timestamp"])

    df, cuts = combined_score_and_categories(df)
    df["risk_flagged"] = (df["risk_category"].isin(["High", "Critical"])).astype(int)

    lines = []
    print("--- Model Comparison (evaluated against synthetic ground-truth labels) ---")
    lines.append("Model Comparison (evaluated against synthetic ground-truth labels)")
    evaluate_method(df, "rule_flagged", "Rule-based only", lines)
    evaluate_method(df, "is_anomaly", "Isolation Forest only", lines)
    evaluate_method(df, "risk_flagged", "Blended risk score (High+Critical)", lines)

    print(f"\nRisk score cut points (fixed): "
          f"Medium>={cuts['medium']}, High>={cuts['high']}, Critical>={cuts['critical']}")
    lines.append(f"\nRisk score cut points (fixed): "
                 f"Medium>={cuts['medium']}, High>={cuts['high']}, Critical>={cuts['critical']}")

    amount_ttest(df, lines)
    fraud_rate_confidence_interval(df, lines)
    channel_chi_square(df, lines)
    correlation_summary(df, lines)

    output_path = os.path.join(PROCESSED_DIR, "risk_scores.csv")
    df.to_csv(output_path, index=False)

    with open(os.path.join(REPORTS_DIR, "statistical_summary.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nSaved scored dataset to {output_path}")
    print(f"Saved statistical summary to {REPORTS_DIR}/statistical_summary.txt")


if __name__ == "__main__":
    main()
