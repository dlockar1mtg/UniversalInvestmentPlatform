-- Phase 2.4 allocation inspection views

CREATE OR REPLACE VIEW portfolio.v_category_allocation AS
SELECT *
FROM portfolio.current_allocations
WHERE allocation_level = 'category';

CREATE OR REPLACE VIEW portfolio.v_allocation_drift AS
SELECT
    portfolio_id,
    allocation_key AS category,
    market_value,
    actual_weight,
    target_weight,
    percentage_point_drift,
    relative_drift,
    dollar_variance,
    allocation_status,
    concentration_rank
FROM portfolio.v_category_allocation
ORDER BY portfolio_id, ABS(percentage_point_drift) DESC NULLS LAST;

CREATE OR REPLACE VIEW portfolio.v_underweight_categories AS
SELECT *
FROM portfolio.v_category_allocation
WHERE allocation_status = 'underweight'
ORDER BY dollar_variance ASC;

CREATE OR REPLACE VIEW portfolio.v_overweight_categories AS
SELECT *
FROM portfolio.v_category_allocation
WHERE allocation_status = 'overweight'
ORDER BY dollar_variance DESC;

CREATE OR REPLACE VIEW portfolio.v_allocation_data_quality AS
SELECT
    portfolio_id,
    SUM(stale_market_value) AS stale_market_value,
    SUM(unvalued_cost_basis) AS unvalued_cost_basis,
    SUM(position_count) AS position_count
FROM portfolio.v_category_allocation
GROUP BY portfolio_id;

CREATE OR REPLACE VIEW portfolio.v_latest_allocation_run AS
SELECT *
FROM portfolio.allocation_calculation_runs
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY portfolio_id
    ORDER BY calculated_at DESC
) = 1;
