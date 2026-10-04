# data/processed/

This folder holds pipeline output. Two kinds of files live here:

**Committed to the repo** (final, ready-to-use outputs):
- `customers_clean.csv` — validated customer dimension
- `powerbi_transactions.csv` — the main Power BI fact table (41 columns:
  raw transaction fields + engineered features + rule/anomaly/risk scores)
- `powerbi_customer_summary.csv` — customer-level rollup for Power BI
- `powerbi_date_dimension.csv` — date dimension table for Power BI

**Not committed** (regenerated automatically by `run_pipeline.py`, listed in
`.gitignore` to keep the repo lightweight):
- `transactions_clean.csv` — output of `02_data_cleaning.py`
- `transactions_features.csv` — output of `03_feature_engineering.py`
- `transactions_rules.csv` — output of `04_rule_based_detection.py`
- `transactions_anomaly.csv` — output of `05_anomaly_detection.py`
- `risk_scores.csv` — output of `06_statistical_analysis.py` (same data as
  `powerbi_transactions.csv` but before the customer-attribute join)

If you only see the committed files, run `python run_pipeline.py` from the
project root to regenerate the rest — this reproduces every intermediate
checkpoint deterministically (fixed random seed).
