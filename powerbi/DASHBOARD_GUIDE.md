# Power BI Investigation Dashboard — Build Guide

This project cannot generate a binary `.pbix` file directly, so this guide gives
you everything needed to build the dashboard yourself in Power BI Desktop
(free): the exact data to import, the table relationships, every DAX measure,
and the page-by-page layout. Following the steps below takes about 20-30
minutes.

## 1. Data to import

From `data/processed/`, import these three CSVs (Home > Get Data > Text/CSV):

| File | Role | Grain |
|---|---|---|
| `powerbi_transactions.csv` | Fact table | One row per transaction |
| `powerbi_customer_summary.csv` | Customer dimension / summary | One row per customer |
| `powerbi_date_dimension.csv` | Date dimension | One row per calendar day |

Rename them in Power BI's model view to `fact_transactions`, `dim_customers`,
and `dim_date` respectively (Power Query Editor > right-click table > Rename).

## 2. Relationships (Model view)

Create these relationships:

- `fact_transactions[customer_id]` → `dim_customers[customer_id]` (many-to-one)
- `fact_transactions[transaction_date]` → `dim_date[date]` (many-to-one)

Set `dim_date[date]` as a **Date table** (Table tools > Mark as date table).

## 3. Column type fixes

In Power Query, confirm:
- `fact_transactions[timestamp]` → Date/Time
- `fact_transactions[transaction_date]` → Date
- `dim_date[date]` → Date
- All `is_*`, `*_flagged`, `*_score` columns → Whole Number / Decimal Number as appropriate

## 4. DAX measures

Create a new table of measures for organization: Modeling > New Table, name it
`_Measures`, paste `= ROW("x", 0)`, then add each measure below to it
(Modeling > New Measure). Full list also in `powerbi/dax_measures.txt`.

```dax
Total Transactions = COUNTROWS(fact_transactions)

Total Transaction Value = SUM(fact_transactions[amount])

Avg Transaction Value = AVERAGE(fact_transactions[amount])

Confirmed Fraud Transactions = SUM(fact_transactions[is_fraud_synthetic])

Fraud Rate % =
DIVIDE([Confirmed Fraud Transactions], [Total Transactions], 0)

Fraud Exposure Value =
CALCULATE(SUM(fact_transactions[amount]), fact_transactions[is_fraud_synthetic] = 1)

Flagged Transactions = SUM(fact_transactions[risk_flagged])

Flag Rate % = DIVIDE([Flagged Transactions], [Total Transactions], 0)

Critical Alerts =
CALCULATE([Total Transactions], fact_transactions[risk_category] = "Critical")

High Alerts =
CALCULATE([Total Transactions], fact_transactions[risk_category] = "High")

Avg Risk Score = AVERAGE(fact_transactions[risk_score])

True Positive Alerts =
CALCULATE(
    [Total Transactions],
    fact_transactions[risk_flagged] = 1,
    fact_transactions[is_fraud_synthetic] = 1
)

Alert Precision % = DIVIDE([True Positive Alerts], [Flagged Transactions], 0)

Alert Recall % = DIVIDE([True Positive Alerts], [Confirmed Fraud Transactions], 0)

MoM Transaction Value =
CALCULATE(
    [Total Transaction Value],
    DATEADD(dim_date[date], -1, MONTH)
)

MoM Fraud Rate Change % = [Fraud Rate %] - CALCULATE([Fraud Rate %], DATEADD(dim_date[date], -1, MONTH))
```

## 5. Suggested dashboard pages

### Page 1 — Executive Overview
- KPI cards: Total Transactions, Total Transaction Value, Fraud Rate %,
  Fraud Exposure Value, Flagged Transactions
- Line chart: Total Transaction Value and Fraud Rate % by `transaction_month`
- Donut chart: Transaction count by `risk_category`
- Bar chart: Fraud Exposure Value by `customer_segment`
- Slicers: `transaction_month`, `customer_segment`, `channel`

### Page 2 — Risk Investigation (drill-down)
- Table/matrix: `transaction_id`, `customer_id`, `timestamp`, `amount`,
  `risk_score`, `risk_category`, `alert_reasons`, `channel`, `transaction_city`
  — sorted by `risk_score` descending, filtered to `risk_category` in
  {High, Critical} by default
- Bar chart: count of transactions by parsed `alert_reasons` (split the
  semicolon-delimited text in Power Query into rows if you want a clean
  single-reason-per-row breakdown, using Split Column > By Delimiter > Rows)
- Scatter chart: `transaction_velocity_1h` (X) vs `amount_zscore` (Y),
  colored by `risk_category`
- Slicers: `risk_category`, date range, `merchant_category`, `transaction_country`

### Page 3 — Customer Risk Profiles
- Table from `dim_customers`: `customer_id`, `customer_segment`, `total_transactions`,
  `total_amount`, `max_risk_score`, `critical_alerts`, `confirmed_fraud_transactions`
  sorted by `max_risk_score` descending
- Bar chart: Top 15 customers by `max_risk_score`
- Card: count of customers with `risk_tier` = "Critical"

### Page 4 — Model Performance
- Table comparing detection methods (type these three rows manually as a
  small table, or import `outputs/reports/statistical_summary.txt` values):
  Rule-based only, Isolation Forest only, Blended risk score — with
  Precision, Recall, F1 columns from the pipeline's evaluation output
- Card: Alert Precision %, Alert Recall % (computed live via DAX above)
- Column chart: fraud rate by `risk_category` (shows the risk-tier lift)

## 6. Formatting notes

- Use a consistent color scale for risk categories: Low = green, Medium =
  yellow, High = orange, Critical = red.
- Add a report-level filter to exclude test/demo rows if you later append
  new data (not needed for the shipped dataset, which is already clean).
- Publish to Power BI Service (free tier) only if you want to share a live
  link; the .pbix file itself is enough for a portfolio/GitHub screenshot.

## 7. Exporting a screenshot for your GitHub README

Once built, use File > Export > Export to PDF (or a screenshot) of each page
and drop the images into a `powerbi/screenshots/` folder, then reference them
in the main `README.md` so recruiters can see the dashboard without opening
Power BI Desktop.
