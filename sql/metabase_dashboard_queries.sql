-- CarteiraConsol Metabase dashboard queries
-- Copy each query into a Metabase SQL question and save it with the recommended name.
-- Configure the variables as Field Filters when applicable.

-- ---------------------------------------------------------------------------
-- 1. Portfolio AUM
-- Chart: KPI
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    COALESCE(SUM(total_value), 0) AS portfolio_aum
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]];


-- ---------------------------------------------------------------------------
-- 2. Client Base
-- Chart: KPI
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    COUNT(DISTINCT client_id) AS client_base
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]];


-- ---------------------------------------------------------------------------
-- 3. Broker Network
-- Chart: KPI
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    COUNT(DISTINCT broker) AS broker_network
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]];


-- ---------------------------------------------------------------------------
-- 4. Tracked Positions
-- Chart: KPI
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    COUNT(*) AS tracked_positions
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]];


-- ---------------------------------------------------------------------------
-- 5. Capital Allocation
-- Chart: Donut
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    SUM(total_value) AS total_value
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]]
GROUP BY asset_class
ORDER BY total_value DESC;


-- ---------------------------------------------------------------------------
-- 6. Allocation Mix (optional companion question)
-- Chart: Horizontal Bar
-- Source: analytics_allocation_by_asset_class
-- ---------------------------------------------------------------------------
SELECT
    asset_class,
    total_value,
    positions_count,
    clients_count
FROM analytics_allocation_by_asset_class
WHERE 1 = 1
[[AND {{reference_date}}]]
ORDER BY total_value DESC;


-- ---------------------------------------------------------------------------
-- 7. Broker Exposure
-- Chart: Horizontal Bar
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    broker,
    SUM(total_value) AS total_value
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]]
GROUP BY broker
ORDER BY total_value DESC;


-- ---------------------------------------------------------------------------
-- 8. Broker Footprint (optional companion question)
-- Chart: Table
-- Source: analytics_positions_by_broker
-- ---------------------------------------------------------------------------
SELECT
    broker,
    total_value,
    positions_count,
    clients_count
FROM analytics_positions_by_broker
WHERE 1 = 1
[[AND {{reference_date}}]]
ORDER BY total_value DESC;


-- ---------------------------------------------------------------------------
-- 9. Client Exposure
-- Chart: Horizontal Bar
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    client_name,
    SUM(total_value) AS total_value
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]]
GROUP BY client_name
ORDER BY total_value DESC
LIMIT 10;


-- ---------------------------------------------------------------------------
-- 10. Client Concentration (optional companion question)
-- Chart: Table
-- Source: analytics_positions_by_client
-- ---------------------------------------------------------------------------
SELECT
    client_name,
    risk_profile,
    total_value,
    positions_count,
    brokers_count,
    assets_count
FROM analytics_positions_by_client
WHERE 1 = 1
[[AND {{reference_date}}]]
ORDER BY total_value DESC;


-- ---------------------------------------------------------------------------
-- 11. Portfolio Trajectory
-- Chart: Line
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    reference_date,
    SUM(total_value) AS portfolio_total_value
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]]
GROUP BY reference_date
ORDER BY reference_date;


-- ---------------------------------------------------------------------------
-- 12. Position Ledger
-- Chart: Table
-- Source: analytics_position_facts
-- ---------------------------------------------------------------------------
SELECT
    reference_date,
    client_name,
    risk_profile,
    broker,
    asset_class,
    ticker,
    normalized_name,
    quantity,
    avg_price,
    total_value
FROM analytics_position_facts
WHERE 1 = 1
[[AND {{reference_date}}]]
[[AND {{client_name}}]]
[[AND {{broker}}]]
[[AND {{asset_class}}]]
[[AND {{risk_profile}}]]
ORDER BY reference_date DESC, total_value DESC, client_name ASC;
