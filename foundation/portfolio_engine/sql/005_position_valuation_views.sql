-- Phase 2.3 inspection and portfolio summary views

CREATE OR REPLACE VIEW portfolio.v_current_positions AS
SELECT *
FROM portfolio.current_positions
WHERE quantity > 0;

CREATE OR REPLACE VIEW portfolio.v_portfolio_position_summary AS
SELECT
    portfolio_id,
    asset_category,
    currency,
    SUM(market_value) AS market_value,
    SUM(cost_basis) AS cost_basis,
    SUM(unrealized_gain_loss) AS unrealized_gain_loss,
    SUM(realized_gain_loss) AS realized_gain_loss,
    COUNT(*) AS position_count,
    SUM(CASE WHEN is_stale THEN market_value ELSE 0 END) AS stale_market_value
FROM portfolio.v_current_positions
GROUP BY portfolio_id, asset_category, currency;

CREATE OR REPLACE VIEW portfolio.v_unvalued_positions AS
SELECT *
FROM portfolio.v_current_positions
WHERE valued_at IS NULL OR latest_price = 0;

CREATE OR REPLACE VIEW portfolio.v_stale_positions AS
SELECT *
FROM portfolio.v_current_positions
WHERE is_stale;

CREATE OR REPLACE VIEW portfolio.v_portfolio_total_value AS
SELECT
    p.portfolio_id,
    COALESCE(SUM(p.market_value), 0) AS invested_market_value,
    COALESCE(c.cash_balance, 0) AS cash_balance,
    COALESCE(SUM(p.market_value), 0) + COALESCE(c.cash_balance, 0) AS total_portfolio_value,
    COALESCE(SUM(p.cost_basis), 0) AS total_cost_basis,
    COALESCE(SUM(p.unrealized_gain_loss), 0) AS unrealized_gain_loss
FROM portfolio.v_current_positions AS p
LEFT JOIN (
    SELECT portfolio_id, SUM(cash_balance) AS cash_balance
    FROM portfolio.cash_balances
    GROUP BY portfolio_id
) AS c
    ON p.portfolio_id = c.portfolio_id
GROUP BY p.portfolio_id, c.cash_balance;
