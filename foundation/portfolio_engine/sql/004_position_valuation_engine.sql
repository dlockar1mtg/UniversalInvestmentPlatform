-- Phase 2.3: Position and Valuation Engine
-- Target engine: DuckDB

CREATE TABLE IF NOT EXISTS portfolio.current_positions (
    position_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    account_id UUID NOT NULL,
    asset_id VARCHAR NOT NULL,
    asset_name VARCHAR NOT NULL,
    asset_category VARCHAR NOT NULL,
    quantity DECIMAL(28, 10) NOT NULL,
    average_unit_cost DECIMAL(28, 10) NOT NULL DEFAULT 0,
    cost_basis DECIMAL(18, 2) NOT NULL,
    latest_price DECIMAL(28, 10) NOT NULL DEFAULT 0,
    market_value DECIMAL(18, 2) NOT NULL,
    unrealized_gain_loss DECIMAL(18, 2) NOT NULL DEFAULT 0,
    realized_gain_loss DECIMAL(18, 2) NOT NULL DEFAULT 0,
    portfolio_weight DECIMAL(18, 12) NOT NULL DEFAULT 0,
    currency VARCHAR NOT NULL DEFAULT 'USD',
    liquidity_tier VARCHAR NOT NULL DEFAULT 'unknown',
    valued_at TIMESTAMP,
    valuation_source VARCHAR,
    valuation_confidence VARCHAR,
    valuation_age_days INTEGER,
    is_stale BOOLEAN NOT NULL DEFAULT TRUE,
    as_of TIMESTAMP NOT NULL,
    UNIQUE (portfolio_id, account_id, asset_id),
    CHECK (quantity >= 0),
    CHECK (cost_basis >= 0),
    CHECK (latest_price >= 0),
    CHECK (market_value >= 0),
    CHECK (portfolio_weight BETWEEN 0 AND 1),
    CHECK (length(currency) = 3)
);

CREATE TABLE IF NOT EXISTS portfolio.position_rebuild_runs (
    rebuild_run_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    as_of TIMESTAMP NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    ledger_entry_count INTEGER NOT NULL DEFAULT 0,
    position_count INTEGER NOT NULL DEFAULT 0,
    stale_position_count INTEGER NOT NULL DEFAULT 0,
    unvalued_position_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'running',
    notes VARCHAR,
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS portfolio.cash_balances (
    portfolio_id UUID NOT NULL,
    account_id UUID NOT NULL,
    currency VARCHAR NOT NULL,
    cash_balance DECIMAL(18, 2) NOT NULL,
    as_of TIMESTAMP NOT NULL,
    PRIMARY KEY (portfolio_id, account_id, currency),
    CHECK (length(currency) = 3)
);

CREATE INDEX IF NOT EXISTS ix_current_positions_portfolio
ON portfolio.current_positions (portfolio_id, asset_category);

CREATE INDEX IF NOT EXISTS ix_valuations_asset_time
ON portfolio.valuations (asset_id, valued_at);
