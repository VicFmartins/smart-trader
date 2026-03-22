CREATE OR REPLACE VIEW analytics_position_facts AS
SELECT
    ph.id AS position_id,
    ph.reference_date,
    c.id AS client_id,
    c.name AS client_name,
    c.risk_profile,
    a.id AS account_id,
    a.broker,
    am.id AS asset_id,
    am.ticker,
    am.original_name,
    am.normalized_name,
    am.asset_class,
    am.cnpj,
    am.maturity_date,
    ph.quantity,
    ph.avg_price,
    ph.total_value
FROM positions_history ph
JOIN accounts a ON a.id = ph.account_id
JOIN clients c ON c.id = a.client_id
JOIN assets_master am ON am.id = ph.asset_id;

CREATE OR REPLACE VIEW analytics_allocation_by_asset_class AS
SELECT
    reference_date,
    asset_class,
    SUM(total_value) AS total_value,
    COUNT(*) AS positions_count,
    COUNT(DISTINCT client_id) AS clients_count
FROM analytics_position_facts
GROUP BY reference_date, asset_class;

CREATE OR REPLACE VIEW analytics_positions_by_broker AS
SELECT
    reference_date,
    broker,
    SUM(total_value) AS total_value,
    COUNT(*) AS positions_count,
    COUNT(DISTINCT client_id) AS clients_count
FROM analytics_position_facts
GROUP BY reference_date, broker;

CREATE OR REPLACE VIEW analytics_positions_by_client AS
SELECT
    reference_date,
    client_id,
    client_name,
    risk_profile,
    SUM(total_value) AS total_value,
    COUNT(*) AS positions_count,
    COUNT(DISTINCT broker) AS brokers_count,
    COUNT(DISTINCT asset_id) AS assets_count
FROM analytics_position_facts
GROUP BY reference_date, client_id, client_name, risk_profile;

CREATE OR REPLACE VIEW analytics_portfolio_totals_by_reference_date AS
SELECT
    reference_date,
    SUM(total_value) AS portfolio_total_value,
    COUNT(*) AS positions_count,
    COUNT(DISTINCT client_id) AS clients_count,
    COUNT(DISTINCT broker) AS brokers_count,
    COUNT(DISTINCT asset_id) AS assets_count
FROM analytics_position_facts
GROUP BY reference_date;
