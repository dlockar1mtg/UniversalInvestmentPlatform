-- Phase 2.6: Performance and Analytics Engine
-- Target engine: DuckDB

CREATE TABLE IF NOT EXISTS portfolio.performance_runs (
    performance_run_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_return DECIMAL(18, 12),
    time_weighted_return DECIMAL(18, 12),
    money_weighted_return DECIMAL(18, 12),
    annualized_return DECIMAL(18, 12),
    annualized_volatility DECIMAL(18, 12),
    downside_deviation DECIMAL(18, 12),
    maximum_drawdown DECIMAL(18, 12),
    drawdown_peak_date DATE,
    drawdown_trough_date DATE,
    recovery_date DATE,
    recovery_days INTEGER,
    sharpe_ratio DECIMAL(18, 8),
    sortino_ratio DECIMAL(18, 8),
    calmar_ratio DECIMAL(18, 8),
    positive_period_percentage DECIMAL(18, 12),
    best_period_return DECIMAL(18, 12),
    worst_period_return DECIMAL(18, 12),
    benchmark_key VARCHAR,
    benchmark_return DECIMAL(18, 12),
    excess_return DECIMAL(18, 12),
    status VARCHAR NOT NULL DEFAULT 'completed',
    notes VARCHAR,
    CHECK (period_end >= period_start),
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS portfolio.performance_periods (
    performance_period_id UUID PRIMARY KEY,
    performance_run_id UUID NOT NULL,
    portfolio_id UUID NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    beginning_value DECIMAL(18, 2) NOT NULL,
    ending_value DECIMAL(18, 2) NOT NULL,
    net_external_cash_flow DECIMAL(18, 2) NOT NULL DEFAULT 0,
    period_return DECIMAL(18, 12) NOT NULL,
    CHECK (period_end >= period_start),
    CHECK (beginning_value >= 0),
    CHECK (ending_value >= 0)
);

CREATE TABLE IF NOT EXISTS portfolio.performance_attribution (
    attribution_id UUID PRIMARY KEY,
    performance_run_id UUID NOT NULL,
    portfolio_id UUID NOT NULL,
    attribution_level VARCHAR NOT NULL,
    attribution_key VARCHAR NOT NULL,
    beginning_weight DECIMAL(18, 12) NOT NULL,
    period_return DECIMAL(18, 12) NOT NULL,
    contribution_to_return DECIMAL(18, 12) NOT NULL,
    contribution_share DECIMAL(18, 12) NOT NULL,
    UNIQUE (performance_run_id, attribution_level, attribution_key)
);

CREATE TABLE IF NOT EXISTS portfolio.benchmark_history (
    benchmark_key VARCHAR NOT NULL,
    benchmark_date DATE NOT NULL,
    benchmark_value DECIMAL(28, 10) NOT NULL,
    currency VARCHAR NOT NULL DEFAULT 'USD',
    source VARCHAR,
    PRIMARY KEY (benchmark_key, benchmark_date),
    CHECK (benchmark_value >= 0),
    CHECK (length(currency) = 3)
);

CREATE TABLE IF NOT EXISTS portfolio.benchmark_returns (
    benchmark_key VARCHAR NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_return DECIMAL(18, 12) NOT NULL,
    PRIMARY KEY (benchmark_key, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS ix_performance_runs_portfolio
ON portfolio.performance_runs (portfolio_id, period_end);

CREATE INDEX IF NOT EXISTS ix_benchmark_history_key_date
ON portfolio.benchmark_history (benchmark_key, benchmark_date);
