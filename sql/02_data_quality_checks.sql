-- 1. Duplicate transaction IDs (should be 0)
SELECT COUNT(*) AS duplicate_transaction_ids
FROM (
    SELECT transaction_id, COUNT(*) AS n
    FROM transactions
    GROUP BY transaction_id
    HAVING n > 1
);

-- 2. Transactions referencing an unknown customer (should be 0)
SELECT COUNT(*) AS orphan_transactions
FROM transactions t
LEFT JOIN customers c ON t.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- 3. Non-positive transaction amounts (should be 0)
SELECT COUNT(*) AS non_positive_amounts
FROM transactions
WHERE amount <= 0;

-- 4. Null checks on key columns
SELECT
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_customer_id,
    SUM(CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END) AS null_timestamp,
    SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) AS null_amount
FROM transactions;

-- 5. Customers with zero transactions (informational, not necessarily an error)
SELECT COUNT(*) AS customers_with_no_transactions
FROM customers c
LEFT JOIN transactions t ON c.customer_id = t.customer_id
WHERE t.transaction_id IS NULL;

-- 6. Row count reconciliation between raw and scored tables (should match)
SELECT
    (SELECT COUNT(*) FROM transactions) AS raw_transaction_count,
    (SELECT COUNT(*) FROM risk_scored_transactions) AS scored_transaction_count;
