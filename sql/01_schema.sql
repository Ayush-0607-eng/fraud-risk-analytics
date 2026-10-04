DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    customer_id       TEXT PRIMARY KEY,
    signup_date       DATE,
    age               INTEGER,
    gender            TEXT,
    home_city         TEXT,
    home_country      TEXT,
    account_type      TEXT,
    customer_segment  TEXT
);

DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
    transaction_id       TEXT PRIMARY KEY,
    customer_id           TEXT REFERENCES customers(customer_id),
    timestamp              DATETIME,
    amount                 REAL,
    currency               TEXT,
    merchant_category     TEXT,
    transaction_type       TEXT,
    channel                TEXT,
    transaction_city       TEXT,
    transaction_country    TEXT,
    device_id              TEXT,
    is_fraud_synthetic     INTEGER
);

DROP TABLE IF EXISTS risk_scored_transactions;
CREATE TABLE risk_scored_transactions (
    transaction_id                     TEXT PRIMARY KEY,
    customer_id                        TEXT REFERENCES customers(customer_id),
    timestamp                          DATETIME,
    amount                             REAL,
    currency                           TEXT,
    merchant_category                  TEXT,
    transaction_type                   TEXT,
    channel                            TEXT,
    transaction_city                   TEXT,
    transaction_country                TEXT,
    device_id                          TEXT,
    transaction_velocity_1h            INTEGER,
    transaction_velocity_24h           INTEGER,
    amount_zscore                      REAL,
    amount_ratio_to_avg                REAL,
    is_new_city_for_customer           INTEGER,
    is_new_device_for_customer         INTEGER,
    is_unusual_category_for_customer   INTEGER,
    is_odd_hour                        INTEGER,
    is_foreign_transaction             INTEGER,
    rule_score                         INTEGER,
    alert_reasons                      TEXT,
    rule_flagged                       INTEGER,
    anomaly_score                      REAL,
    is_anomaly                         INTEGER,
    risk_score                         REAL,
    risk_category                      TEXT,
    risk_flagged                       INTEGER,
    is_fraud_synthetic                 INTEGER,
    signup_date                        DATE,
    age                                INTEGER,
    gender                             TEXT,
    home_city                          TEXT,
    home_country                       TEXT,
    account_type                       TEXT,
    customer_segment                   TEXT,
    transaction_date                   DATE,
    transaction_month                  TEXT,
    transaction_week                   TEXT,
    transaction_hour                   INTEGER,
    transaction_weekday                TEXT
);

CREATE INDEX idx_txn_customer ON transactions(customer_id);
CREATE INDEX idx_txn_timestamp ON transactions(timestamp);
CREATE INDEX idx_risk_customer ON risk_scored_transactions(customer_id);
CREATE INDEX idx_risk_category ON risk_scored_transactions(risk_category);
