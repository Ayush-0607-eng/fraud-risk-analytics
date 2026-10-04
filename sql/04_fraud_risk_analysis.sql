SELECT
    transaction_id,
    customer_id,
    timestamp,
    amount,
    LAG(timestamp) OVER (PARTITION BY customer_id ORDER BY timestamp) AS prev_txn_timestamp,
    ROUND(
        (CAST(strftime('%s', timestamp) AS REAL)
         - CAST(strftime('%s', LAG(timestamp) OVER (PARTITION BY customer_id ORDER BY timestamp)) AS REAL)
        ) / 60.0, 2
    ) AS minutes_since_prev_txn
FROM transactions
WHERE customer_id IN (
    SELECT DISTINCT customer_id FROM risk_scored_transactions WHERE risk_category = 'Critical'
)
ORDER BY customer_id, timestamp
LIMIT 50;

-- 2. Running total of transaction amount per customer (behavioral baseline
--    check, computed independently in SQL using a window frame).
SELECT
    customer_id,
    transaction_id,
    timestamp,
    amount,
    ROUND(AVG(amount) OVER (
        PARTITION BY customer_id ORDER BY timestamp
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ), 2) AS running_avg_amount_before_this_txn,
    ROUND(amount - AVG(amount) OVER (
        PARTITION BY customer_id ORDER BY timestamp
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ), 2) AS deviation_from_running_avg
FROM transactions
WHERE customer_id = (SELECT customer_id FROM risk_scored_transactions ORDER BY risk_score DESC LIMIT 1)
ORDER BY timestamp;

-- 3. Rank customers within each segment by fraud exposure value.
SELECT
    customer_segment,
    customer_id,
    fraud_exposure_value,
    RANK() OVER (PARTITION BY customer_segment ORDER BY fraud_exposure_value DESC) AS segment_rank
FROM (
    SELECT
        customer_segment,
        customer_id,
        ROUND(SUM(CASE WHEN is_fraud_synthetic = 1 THEN amount ELSE 0 END), 2) AS fraud_exposure_value
    FROM risk_scored_transactions
    GROUP BY customer_segment, customer_id
)
WHERE fraud_exposure_value > 0
ORDER BY customer_segment, segment_rank
LIMIT 30;

-- 4. Geography risk: transactions flagged as a new city or foreign
--    country, broken down by destination and outcome.
SELECT
    transaction_country,
    transaction_city,
    COUNT(*)                                              AS transactions,
    SUM(is_new_city_for_customer)                         AS new_geography_flags,
    SUM(is_foreign_transaction)                           AS foreign_txn_flags,
    SUM(is_fraud_synthetic)                                AS confirmed_fraud,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 3)   AS fraud_rate_pct
FROM risk_scored_transactions
GROUP BY transaction_country, transaction_city
HAVING transactions >= 20
ORDER BY fraud_rate_pct DESC
LIMIT 20;

-- 5. Rule co-occurrence: how many distinct rules fire together on average
--    for confirmed fraud vs non-fraud (approximated via rule_score bucket).
SELECT
    is_fraud_synthetic,
    CASE
        WHEN rule_score = 0 THEN '0 (no rule)'
        WHEN rule_score <= 20 THEN '1 rule (10-20)'
        WHEN rule_score <= 45 THEN '2 rules (25-45)'
        ELSE '3+ rules (50+)'
    END AS approx_rules_triggered,
    COUNT(*) AS transaction_count
FROM risk_scored_transactions
GROUP BY is_fraud_synthetic, approx_rules_triggered
ORDER BY is_fraud_synthetic, transaction_count DESC;

-- 6. Detection method comparison: rule-based vs anomaly-based vs blended,
--    computed directly in SQL as a cross-check on the Python evaluation.
SELECT
    'rule_flagged'  AS method,
    SUM(CASE WHEN rule_flagged = 1 AND is_fraud_synthetic = 1 THEN 1 ELSE 0 END) AS true_positives,
    SUM(CASE WHEN rule_flagged = 1 AND is_fraud_synthetic = 0 THEN 1 ELSE 0 END) AS false_positives,
    SUM(CASE WHEN rule_flagged = 0 AND is_fraud_synthetic = 1 THEN 1 ELSE 0 END) AS false_negatives
FROM risk_scored_transactions
UNION ALL
SELECT
    'is_anomaly',
    SUM(CASE WHEN is_anomaly = 1 AND is_fraud_synthetic = 1 THEN 1 ELSE 0 END),
    SUM(CASE WHEN is_anomaly = 1 AND is_fraud_synthetic = 0 THEN 1 ELSE 0 END),
    SUM(CASE WHEN is_anomaly = 0 AND is_fraud_synthetic = 1 THEN 1 ELSE 0 END)
FROM risk_scored_transactions
UNION ALL
SELECT
    'risk_flagged (blended)',
    SUM(CASE WHEN risk_flagged = 1 AND is_fraud_synthetic = 1 THEN 1 ELSE 0 END),
    SUM(CASE WHEN risk_flagged = 1 AND is_fraud_synthetic = 0 THEN 1 ELSE 0 END),
    SUM(CASE WHEN risk_flagged = 0 AND is_fraud_synthetic = 1 THEN 1 ELSE 0 END)
FROM risk_scored_transactions;
