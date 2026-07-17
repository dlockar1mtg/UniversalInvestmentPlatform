-- Phase 2.2 ledger inspection and audit views

CREATE OR REPLACE VIEW portfolio.v_active_ledger_entries AS
SELECT *
FROM portfolio.ledger_entries
WHERE entry_status = 'posted';

CREATE OR REPLACE VIEW portfolio.v_ledger_account_balances AS
SELECT
    portfolio_id,
    account_id,
    currency,
    SUM(net_amount) AS net_cash_flow,
    COUNT(*) AS entry_count,
    MIN(effective_at) AS first_entry_at,
    MAX(effective_at) AS latest_entry_at
FROM portfolio.v_active_ledger_entries
GROUP BY portfolio_id, account_id, currency;

CREATE OR REPLACE VIEW portfolio.v_ledger_asset_activity AS
SELECT
    portfolio_id,
    account_id,
    asset_id,
    asset_name,
    asset_category,
    currency,
    SUM(
        CASE
            WHEN transaction_type IN ('buy', 'transfer_in') THEN COALESCE(quantity, 0)
            WHEN transaction_type IN ('sell', 'transfer_out') THEN -COALESCE(quantity, 0)
            ELSE 0
        END
    ) AS net_quantity,
    SUM(
        CASE
            WHEN transaction_type = 'buy' THEN gross_amount + fees
            WHEN transaction_type = 'sell' THEN -(gross_amount - fees)
            ELSE 0
        END
    ) AS net_invested_cash,
    COUNT(*) AS entry_count,
    MAX(effective_at) AS latest_activity_at
FROM portfolio.v_active_ledger_entries
WHERE asset_id IS NOT NULL
GROUP BY portfolio_id, account_id, asset_id, asset_name, asset_category, currency;

CREATE OR REPLACE VIEW portfolio.v_ledger_audit_summary AS
SELECT
    portfolio_id,
    source_platform,
    COUNT(*) AS entry_count,
    COUNT(DISTINCT audit_hash) AS distinct_hash_count,
    COUNT(DISTINCT source_record_id) FILTER (
        WHERE source_record_id IS NOT NULL
    ) AS distinct_source_record_count,
    MIN(recorded_at) AS first_recorded_at,
    MAX(recorded_at) AS latest_recorded_at
FROM portfolio.ledger_entries
GROUP BY portfolio_id, source_platform;

CREATE OR REPLACE VIEW portfolio.v_ledger_reversals AS
SELECT
    reversal.ledger_entry_id AS reversal_entry_id,
    reversal.reversal_of_entry_id,
    original.transaction_type AS original_transaction_type,
    original.net_amount AS original_net_amount,
    reversal.net_amount AS reversal_net_amount,
    original.effective_at AS original_effective_at,
    reversal.effective_at AS reversal_effective_at
FROM portfolio.ledger_entries AS reversal
LEFT JOIN portfolio.ledger_entries AS original
    ON reversal.reversal_of_entry_id = original.ledger_entry_id
WHERE reversal.reversal_of_entry_id IS NOT NULL;
