"""
Generates supporting charts for the README and interview walkthrough.
These are static PNGs; the interactive investigation dashboard itself
is built in Power BI from the exported dataset.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
FIG_DIR = os.path.join(BASE_DIR, "outputs", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

sns.set_theme(style="whitegrid")


def load():
    return pd.read_csv(os.path.join(PROCESSED_DIR, "risk_scores.csv"), parse_dates=["timestamp"])


def plot_risk_category_distribution(df):
    order = ["Low", "Medium", "High", "Critical"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.countplot(data=df, x="risk_category", order=order, hue="risk_category",
                  palette="YlOrRd", legend=False, ax=ax)
    ax.set_title("Transaction Volume by Risk Category")
    ax.set_xlabel("Risk Category")
    ax.set_ylabel("Transaction Count")
    ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "risk_category_distribution.png"), dpi=150)
    plt.close(fig)


def plot_fraud_concentration(df):
    order = ["Low", "Medium", "High", "Critical"]
    rate = df.groupby("risk_category")["is_fraud_synthetic"].mean().reindex(order) * 100
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(x=rate.index, y=rate.values, hue=rate.index, palette="YlOrRd", legend=False, ax=ax)
    ax.set_title("Actual Fraud Rate by Risk Category (Model Validation)")
    ax.set_xlabel("Risk Category")
    ax.set_ylabel("Fraud Rate (%)")
    for i, v in enumerate(rate.values):
        ax.text(i, v + 0.5, f"{v:.2f}%", ha="center")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fraud_concentration_by_category.png"), dpi=150)
    plt.close(fig)


def plot_amount_distribution(df):
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    sns.kdeplot(data=df[df["amount"] < df["amount"].quantile(0.99)], x="amount",
                hue="is_fraud_synthetic", common_norm=False, fill=True, alpha=0.4, ax=ax)
    ax.set_title("Transaction Amount Distribution: Fraud vs Non-Fraud")
    ax.set_xlabel("Transaction Amount (INR)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "amount_distribution_fraud_vs_normal.png"), dpi=150)
    plt.close(fig)


def plot_velocity_vs_risk(df):
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    sample = df.sample(min(8000, len(df)), random_state=42)
    sns.scatterplot(data=sample, x="transaction_velocity_1h", y="amount_zscore",
                     hue="risk_category", hue_order=["Low", "Medium", "High", "Critical"],
                     palette="YlOrRd", alpha=0.6, s=25, ax=ax)
    ax.set_title("Transaction Velocity vs Amount Deviation, Colored by Risk Category")
    ax.set_xlabel("Transactions in Prior 1 Hour")
    ax.set_ylabel("Amount Z-Score vs Customer History")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "velocity_vs_amount_deviation.png"), dpi=150)
    plt.close(fig)


def plot_monthly_trend(df):
    monthly = df.set_index("timestamp").resample("W")["is_fraud_synthetic"].agg(["sum", "count"])
    monthly["rate"] = monthly["sum"] / monthly["count"] * 100
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(monthly.index, monthly["rate"], marker="o", color="#c0392b")
    ax.set_title("Weekly Fraud Rate Trend")
    ax.set_xlabel("Week")
    ax.set_ylabel("Fraud Rate (%)")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "weekly_fraud_trend.png"), dpi=150)
    plt.close(fig)


def plot_correlation_heatmap(df):
    numeric_cols = [
        "amount", "transaction_velocity_1h", "transaction_velocity_24h", "amount_zscore",
        "amount_ratio_to_avg", "is_new_city_for_customer", "is_new_device_for_customer",
        "is_odd_hour", "is_foreign_transaction", "rule_score", "anomaly_score", "risk_score",
    ]
    corr = df[numeric_cols].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlation Matrix of Risk Features")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "feature_correlation_heatmap.png"), dpi=150)
    plt.close(fig)


def main():
    df = load()
    plot_risk_category_distribution(df)
    plot_fraud_concentration(df)
    plot_amount_distribution(df)
    plot_velocity_vs_risk(df)
    plot_monthly_trend(df)
    plot_correlation_heatmap(df)
    print(f"Saved 6 charts to {FIG_DIR}")


if __name__ == "__main__":
    main()
