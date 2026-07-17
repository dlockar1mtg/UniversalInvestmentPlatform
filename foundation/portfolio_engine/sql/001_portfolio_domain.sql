-- Universal Investment Intelligence Platform
-- Phase 2.1: Universal Portfolio Domain Model
-- Target engine: DuckDB

CREATE SCHEMA IF NOT EXISTS portfolio;

CREATE TABLE IF NOT EXISTS portfolio.portfolios (
    portfolio_id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    base_currency VARCHAR NOT NULL DEFAULT 'USD',
    monthly_contribution DECIMAL(18, 2) NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(base_currency) = 3),
    CHECK (monthly_contribution >= 0),
    CHECK (status IN ('active', 'inactive', 'archived'))
);

CREATE TABLE IF NOT EXISTS portfolio.accounts (
    account_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    name VARCHAR NOT NULL,
    institution VARCHAR NOT NULL,
    account_type VARCHAR NOT NULL,
    external_account_id VARCHAR,
    currency VARCHAR NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (portfolio_id, institution, name),
    CHECK (length(currency) = 3)
);

CREATE TABLE IF NOT EXISTS portfolio.transactions (
    transaction_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    account_id UUID NOT NULL,
    transaction_type VARCHAR NOT NULL,
    transaction_at TIMESTAMP NOT NULL,
    asset_id VARCHAR,
    asset_name VARCHAR,
    asset_category VARCHAR,
    quantity DECIMAL(28, 10),
    unit_price DECIMAL(28, 10),
    amount DECIMAL(18, 2) NOT NULL,
    fees DECIMAL(18, 2) NOT NULL DEFAULT 0,
    currency VARCHAR NOT NULL DEFAULT 'USD',
    source_platform VARCHAR,
    source_record_id VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_platform, source_record_id),
    CHECK (amount >= 0),
    CHECK (fees >= 0),
    CHECK (quantity IS NULL OR quantity >= 0),
    CHECK (unit_price IS NULL OR unit_price >= 0),
    CHECK (length(currency) = 3)
);

CREATE TABLE IF NOT EXISTS portfolio.valuations (
    valuation_id UUID PRIMARY KEY,
    asset_id VARCHAR NOT NULL,
    account_id UUID,
    price DECIMAL(28, 10) NOT NULL,
    currency VARCHAR NOT NULL DEFAULT 'USD',
    valued_at TIMESTAMP NOT NULL,
    source VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL DEFAULT 'unknown',
    source_reference VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (price >= 0),
    CHECK (length(currency) = 3)
);

CREATE TABLE IF NOT EXISTS portfolio.positions (
    position_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    account_id UUID NOT NULL,
    asset_id VARCHAR NOT NULL,
    asset_name VARCHAR NOT NULL,
    asset_category VARCHAR NOT NULL,
    quantity DECIMAL(28, 10) NOT NULL,
    average_unit_cost DECIMAL(28, 10) NOT NULL DEFAULT 0,
    cost_basis DECIMAL(18, 2) NOT NULL,
    market_value DECIMAL(18, 2) NOT NULL,
    unrealized_gain_loss DECIMAL(18, 2) NOT NULL DEFAULT 0,
    realized_gain_loss DECIMAL(18, 2) NOT NULL DEFAULT 0,
    portfolio_weight DECIMAL(12, 8) NOT NULL DEFAULT 0,
    liquidity_tier VARCHAR NOT NULL DEFAULT 'unknown',
    as_of TIMESTAMP NOT NULL,
    UNIQUE (portfolio_id, account_id, asset_id, as_of),
    CHECK (quantity >= 0),
    CHECK (cost_basis >= 0),
    CHECK (market_value >= 0),
    CHECK (portfolio_weight BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS portfolio.allocation_targets (
    target_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    category VARCHAR NOT NULL,
    target_weight DECIMAL(12, 8) NOT NULL,
    minimum_weight DECIMAL(12, 8) NOT NULL,
    maximum_weight DECIMAL(12, 8) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    minimum_purchase_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    allow_fractional BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (portfolio_id, category),
    CHECK (minimum_weight BETWEEN 0 AND 1),
    CHECK (target_weight BETWEEN 0 AND 1),
    CHECK (maximum_weight BETWEEN 0 AND 1),
    CHECK (minimum_weight <= target_weight),
    CHECK (target_weight <= maximum_weight),
    CHECK (minimum_purchase_amount >= 0)
);

CREATE TABLE IF NOT EXISTS portfolio.portfolio_snapshots (
    snapshot_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    snapshot_at TIMESTAMP NOT NULL,
    total_market_value DECIMAL(18, 2) NOT NULL,
    total_cost_basis DECIMAL(18, 2) NOT NULL,
    cash_balance DECIMAL(18, 2) NOT NULL DEFAULT 0,
    total_unrealized_gain_loss DECIMAL(18, 2) NOT NULL DEFAULT 0,
    total_realized_gain_loss DECIMAL(18, 2) NOT NULL DEFAULT 0,
    stale_valuation_value DECIMAL(18, 2) NOT NULL DEFAULT 0,
    position_count INTEGER NOT NULL,
    UNIQUE (portfolio_id, snapshot_at),
    CHECK (total_market_value >= 0),
    CHECK (total_cost_basis >= 0),
    CHECK (position_count >= 0)
);

CREATE TABLE IF NOT EXISTS portfolio.asset_classification_overrides (
    override_id UUID PRIMARY KEY,
    asset_id VARCHAR NOT NULL,
    source_platform VARCHAR,
    asset_category VARCHAR NOT NULL,
    liquidity_tier VARCHAR NOT NULL DEFAULT 'unknown',
    notes VARCHAR,
    effective_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_to TIMESTAMP,
    UNIQUE (asset_id, source_platform, effective_from)
);

CREATE OR REPLACE VIEW portfolio.v_allocation_target_totals AS
SELECT
    portfolio_id,
    SUM(target_weight) AS target_weight_total,
    SUM(minimum_weight) AS minimum_weight_total,
    SUM(maximum_weight) AS maximum_weight_total,
    COUNT(*) AS category_count
FROM portfolio.allocation_targets
GROUP BY portfolio_id;

CREATE OR REPLACE VIEW portfolio.v_latest_valuations AS
SELECT *
FROM portfolio.valuations
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY asset_id, COALESCE(CAST(account_id AS VARCHAR), '')
    ORDER BY valued_at DESC, created_at DESC
) = 1;
