-- Phase 2.4: Universal Allocation Engine
-- Target engine: DuckDB

CREATE TABLE IF NOT EXISTS portfolio.current_allocations (
    allocation_id UUID PRIMARY KEY,
    calculation_run_id UUID NOT NULL,
    portfolio_id UUID NOT NULL,
    allocation_level VARCHAR NOT NULL,
    allocation_key VARCHAR NOT NULL,
    market_value DECIMAL(18, 2) NOT NULL,
    actual_weight DECIMAL(18, 12) NOT NULL,
    target_weight DECIMAL(18, 12),
    minimum_weight DECIMAL(18, 12),
    maximum_weight DECIMAL(18, 12),
    percentage_point_drift DECIMAL(18, 12),
    relative_drift DECIMAL(18, 12),
    target_value DECIMAL(18, 2),
    dollar_variance DECIMAL(18, 2),
    allocation_status VARCHAR NOT NULL,
    stale_market_value DECIMAL(18, 2) NOT NULL DEFAULT 0,
    unvalued_cost_basis DECIMAL(18, 2) NOT NULL DEFAULT 0,
    position_count INTEGER NOT NULL DEFAULT 0,
    concentration_rank INTEGER,
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (portfolio_id, allocation_level, allocation_key),
    CHECK (market_value >= 0),
    CHECK (actual_weight BETWEEN 0 AND 1),
    CHECK (position_count >= 0)
);

CREATE TABLE IF NOT EXISTS portfolio.allocation_calculation_runs (
    calculation_run_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    invested_value DECIMAL(18, 2) NOT NULL,
    cash_value DECIMAL(18, 2) NOT NULL,
    total_wealth DECIMAL(18, 2) NOT NULL,
    stale_market_value DECIMAL(18, 2) NOT NULL,
    unvalued_cost_basis DECIMAL(18, 2) NOT NULL,
    unvalued_position_count INTEGER NOT NULL,
    largest_category_weight DECIMAL(18, 12) NOT NULL,
    top_three_category_weight DECIMAL(18, 12) NOT NULL,
    herfindahl_index DECIMAL(18, 12) NOT NULL,
    effective_category_count DECIMAL(18, 8) NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'completed',
    notes VARCHAR,
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_current_allocations_portfolio
ON portfolio.current_allocations (portfolio_id, allocation_level);

CREATE INDEX IF NOT EXISTS ix_current_allocations_status
ON portfolio.current_allocations (allocation_status);
