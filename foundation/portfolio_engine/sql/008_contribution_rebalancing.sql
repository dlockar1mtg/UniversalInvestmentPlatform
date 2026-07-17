-- Phase 2.5: Contribution and Rebalancing Engine
-- Target engine: DuckDB

CREATE TABLE IF NOT EXISTS portfolio.contribution_plans (
    contribution_plan_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_contribution DECIMAL(18, 2) NOT NULL,
    allocated_contribution DECIMAL(18, 2) NOT NULL,
    unallocated_cash DECIMAL(18, 2) NOT NULL,
    current_portfolio_value DECIMAL(18, 2) NOT NULL,
    projected_portfolio_value DECIMAL(18, 2) NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'generated',
    notes VARCHAR,
    CHECK (total_contribution >= 0),
    CHECK (allocated_contribution >= 0),
    CHECK (unallocated_cash >= 0),
    CHECK (allocated_contribution + unallocated_cash = total_contribution),
    CHECK (status IN ('generated', 'approved', 'executed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS portfolio.contribution_plan_lines (
    contribution_plan_line_id UUID PRIMARY KEY,
    contribution_plan_id UUID NOT NULL,
    portfolio_id UUID NOT NULL,
    category VARCHAR NOT NULL,
    current_value DECIMAL(18, 2) NOT NULL,
    current_weight DECIMAL(18, 12) NOT NULL,
    target_weight DECIMAL(18, 12) NOT NULL,
    projected_target_value DECIMAL(18, 2) NOT NULL,
    funding_deficit DECIMAL(18, 2) NOT NULL,
    requested_contribution DECIMAL(18, 2) NOT NULL,
    recommended_contribution DECIMAL(18, 2) NOT NULL,
    retained_cash DECIMAL(18, 2) NOT NULL,
    projected_value DECIMAL(18, 2) NOT NULL,
    projected_weight DECIMAL(18, 12) NOT NULL,
    projected_drift DECIMAL(18, 12) NOT NULL,
    remaining_deficit DECIMAL(18, 2) NOT NULL,
    contribution_status VARCHAR NOT NULL,
    constraint_reason VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (contribution_plan_id, category),
    CHECK (recommended_contribution >= 0),
    CHECK (retained_cash >= 0),
    CHECK (projected_weight BETWEEN 0 AND 1)
);

CREATE INDEX IF NOT EXISTS ix_contribution_plans_portfolio
ON portfolio.contribution_plans (portfolio_id, generated_at);

CREATE INDEX IF NOT EXISTS ix_contribution_plan_lines_plan
ON portfolio.contribution_plan_lines (contribution_plan_id, category);
