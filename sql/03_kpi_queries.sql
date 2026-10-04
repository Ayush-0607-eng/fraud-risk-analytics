-- 1. Headline volume and value KPIs
SELECT
    COUNT(*)                                    AS total_transactions,
    ROUND(SUM(amount), 2)                        AS total_transaction_value,
    ROUND(AVG(amount), 2)                        AS avg_transaction_value,
    SUM(is_fraud_synthetic)                      AS confirmed_fraud_transactions,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 3) AS fraud_rate_pct,
    ROUND(SUM(CASE WHEN is_fraud_synthetic = 1 THEN amount ELSE 0 END), 2) AS fraud_exposure_value
FROM risk_scored_transactions;

-- 2. Risk category breakdown: volume, value, and detection precision
SELECT
    risk_category,
    COUNT(*)                                                    AS transaction_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM risk_scored_transactions), 2) AS pct_of_all_transactions,
    ROUND(SUM(amount), 2)                                       AS total_amount,
    SUM(is_fraud_synthetic)                                     AS confirmed_fraud_count,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 2)        AS fraud_rate_within_category
FROM risk_scored_transactions
GROUP BY risk_category
ORDER BY
    CASE risk_category WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END;

-- 3. Fraud exposure and alert volume by customer segment
SELECT
    customer_segment,
    COUNT(*)                                             AS transactions,
    SUM(risk_flagged)                                    AS flagged_transactions,
    SUM(is_fraud_synthetic)                              AS confirmed_fraud,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 3) AS fraud_rate_pct,
    ROUND(SUM(CASE WHEN is_fraud_synthetic = 1 THEN amount ELSE 0 END), 2) AS fraud_exposure_value
FROM risk_scored_transactions
GROUP BY customer_segment
ORDER BY fraud_exposure_value DESC;

-- 4. Fraud exposure by transaction channel
SELECT
    channel,
    COUNT(*)                                             AS transactions,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 3) AS fraud_rate_pct,
    ROUND(SUM(CASE WHEN is_fraud_synthetic = 1 THEN amount ELSE 0 END), 2) AS fraud_exposure_value
FROM risk_scored_transactions
GROUP BY channel
ORDER BY fraud_exposure_value DESC;

-- 5. Monthly trend of transaction volume, value and fraud rate
SELECT
    transaction_month,
    COUNT(*)                                             AS transactions,
    ROUND(SUM(amount), 2)                                AS total_amount,
    SUM(is_fraud_synthetic)                              AS confirmed_fraud,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 3) AS fraud_rate_pct
FROM risk_scored_transactions
GROUP BY transaction_month
ORDER BY transaction_month;

-- 6. Top 15 alert reasons by frequency (only rows with a rule triggered)
SELECT
    alert_reasons,
    COUNT(*) AS occurrences
FROM risk_scored_transactions
WHERE alert_reasons <> 'No rule triggered'
GROUP BY alert_reasons
ORDER BY occurrences DESC
LIMIT 15;

-- 7. Top 20 highest-risk customers by peak risk score
SELECT
    customer_id,
    customer_segment,
    COUNT(*)                          AS total_transactions,
    SUM(risk_flagged)                 AS flagged_transactions,
    ROUND(MAX(risk_score), 2)         AS peak_risk_score,
    ROUND(AVG(risk_score), 2)         AS avg_risk_score,
    SUM(is_fraud_synthetic)           AS confirmed_fraud_transactions
FROM risk_scored_transactions
GROUP BY customer_id, customer_segment
ORDER BY peak_risk_score DESC
LIMIT 20;
