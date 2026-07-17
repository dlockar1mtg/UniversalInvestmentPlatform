-- Phase 2.5 contribution plan views

CREATE OR REPLACE VIEW portfolio.v_latest_contribution_plan AS
SELECT *
FROM portfolio.contribution_plans
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY portfolio_id
    ORDER BY generated_at DESC
) = 1;

CREATE OR REPLACE VIEW portfolio.v_latest_contribution_plan_lines AS
SELECT line.*
FROM portfolio.contribution_plan_lines AS line
JOIN portfolio.v_latest_contribution_plan AS plan
    ON line.contribution_plan_id = plan.contribution_plan_id;

CREATE OR REPLACE VIEW portfolio.v_contribution_recommendations AS
SELECT
    portfolio_id,
    category,
    current_value,
    current_weight,
    target_weight,
    funding_deficit,
    recommended_contribution,
    projected_value,
    projected_weight,
    projected_drift,
    remaining_deficit,
    contribution_status,
    constraint_reason
FROM portfolio.v_latest_contribution_plan_lines
ORDER BY recommended_contribution DESC, category;

CREATE OR REPLACE VIEW portfolio.v_contribution_plan_summary AS
SELECT
    contribution_plan_id,
    portfolio_id,
    generated_at,
    total_contribution,
    allocated_contribution,
    unallocated_cash,
    current_portfolio_value,
    projected_portfolio_value,
    CASE
        WHEN total_contribution = 0 THEN 0
        ELSE allocated_contribution / total_contribution
    END AS allocation_efficiency,
    status
FROM portfolio.v_latest_contribution_plan;

CREATE OR REPLACE VIEW portfolio.v_blocked_contributions AS
SELECT *
FROM portfolio.v_latest_contribution_plan_lines
WHERE contribution_status = 'blocked_constraint'
   OR retained_cash > 0
ORDER BY retained_cash DESC;
