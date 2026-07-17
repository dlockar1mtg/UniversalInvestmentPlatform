-- Phase 2.6 performance analytics views

CREATE OR REPLACE VIEW portfolio.v_latest_performance_run AS
SELECT *
FROM portfolio.performance_runs
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY portfolio_id
    ORDER BY calculated_at DESC
) = 1;

CREATE OR REPLACE VIEW portfolio.v_portfolio_performance_summary AS
SELECT
    portfolio_id,
    period_start,
    period_end,
    period_return,
    time_weighted_return,
    money_weighted_return,
    annualized_return,
    annualized_volatility,
    maximum_drawdown,
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
    benchmark_key,
    benchmark_return,
    excess_return
FROM portfolio.v_latest_performance_run;

CREATE OR REPLACE VIEW portfolio.v_performance_attribution AS
SELECT
    performance_run_id,
    portfolio_id,
    attribution_level,
    attribution_key,
    beginning_weight,
    period_return,
    contribution_to_return,
    contribution_share
FROM portfolio.performance_attribution
ORDER BY performance_run_id, contribution_to_return DESC;

CREATE OR REPLACE VIEW portfolio.v_performance_risk_flags AS
SELECT
    portfolio_id,
    period_end,
    annualized_volatility,
    maximum_drawdown,
    sharpe_ratio,
    sortino_ratio,
    CASE
        WHEN maximum_drawdown <= -0.30 THEN 'high_drawdown'
        WHEN annualized_volatility >= 0.35 THEN 'high_volatility'
        WHEN sharpe_ratio < 0 THEN 'negative_risk_adjusted_return'
        ELSE 'normal'
    END AS risk_flag
FROM portfolio.v_latest_performance_run;

CREATE OR REPLACE VIEW portfolio.v_benchmark_comparison AS
SELECT
    portfolio_id,
    benchmark_key,
    period_start,
    period_end,
    period_return AS portfolio_return,
    benchmark_return,
    excess_return
FROM portfolio.v_latest_performance_run
WHERE benchmark_key IS NOT NULL;
