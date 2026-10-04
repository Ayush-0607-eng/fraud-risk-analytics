-- 1. Signup cohort (by month) vs fraud incidence: does account tenure
--    relate to fraud exposure?
SELECT
    strftime('%Y-%m', c.signup_date)                        AS signup_cohort,
    COUNT(DISTINCT c.customer_id)                            AS customers_in_cohort,
    COUNT(t.transaction_id)                                  AS total_transactions,
    SUM(t.is_fraud_synthetic)                                AS confirmed_fraud,
    ROUND(100.0 * SUM(t.is_fraud_synthetic) / COUNT(t.transaction_id), 3) AS fraud_rate_pct
FROM customers c
JOIN risk_scored_transactions t ON c.customer_id = t.customer_id
GROUP BY signup_cohort
ORDER BY signup_cohort;

-- 2. Customer segmentation by spending behavior: bucket customers into
--    quartiles of average transaction amount and compare fraud exposure.
WITH customer_avg AS (
    SELECT
        customer_id,
        customer_segment,
        AVG(amount) AS avg_amount,
        SUM(is_fraud_synthetic) AS fraud_count,
        COUNT(*) AS txn_count
    FROM risk_scored_transactions
    GROUP BY customer_id, customer_segment
),
ranked AS (
    SELECT
        *,
        NTILE(4) OVER (ORDER BY avg_amount) AS spend_quartile
    FROM customer_avg
)
SELECT
    spend_quartile,
    COUNT(*)                              AS customers,
    ROUND(AVG(avg_amount), 2)             AS avg_spend_in_quartile,
    SUM(fraud_count)                      AS total_fraud_transactions,
    SUM(txn_count)                        AS total_transactions,
    ROUND(100.0 * SUM(fraud_count) / SUM(txn_count), 3) AS fraud_rate_pct
FROM ranked
GROUP BY spend_quartile
ORDER BY spend_quartile;

-- 3. Age band segmentation vs risk category mix.
SELECT
    CASE
        WHEN age < 25 THEN '18-24'
        WHEN age < 35 THEN '25-34'
        WHEN age < 45 THEN '35-44'
        WHEN age < 55 THEN '45-54'
        ELSE '55+'
    END AS age_band,
    risk_category,
    COUNT(*) AS transaction_count
FROM risk_scored_transactions
GROUP BY age_band, risk_category
ORDER BY age_band,
    CASE risk_category WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END;

-- 4. Account type vs fraud rate and average alert volume per customer.
SELECT
    account_type,
    COUNT(DISTINCT customer_id)                            AS customers,
    COUNT(*)                                               AS transactions,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 3)   AS fraud_rate_pct,
    ROUND(1.0 * SUM(risk_flagged) / COUNT(DISTINCT customer_id), 2) AS avg_flags_per_customer
FROM risk_scored_transactions
GROUP BY account_type
ORDER BY fraud_rate_pct DESC;

-- 5. Weekday vs weekend transaction and fraud pattern.
SELECT
    transaction_weekday,
    COUNT(*)                                             AS transactions,
    ROUND(100.0 * SUM(is_fraud_synthetic) / COUNT(*), 3) AS fraud_rate_pct,
    ROUND(AVG(risk_score), 2)                            AS avg_risk_score
FROM risk_scored_transactions
GROUP BY transaction_weekday
ORDER BY
    CASE transaction_weekday
        WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
        WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7
    END;
