-- Phase 2.2: Universal Portfolio Ledger
-- Target engine: DuckDB
-- Hotfix: DuckDB-compatible source-record lookup index.

CREATE SCHEMA IF NOT EXISTS portfolio;

CREATE TABLE IF NOT EXISTS portfolio.ledger_import_batches (
    import_run_id UUID PRIMARY KEY,
    source_platform VARCHAR NOT NULL,
    source_file VARCHAR,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    received_count INTEGER NOT NULL DEFAULT 0,
    posted_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'running',
    notes VARCHAR,
    CHECK (received_count >= 0),
    CHECK (posted_count >= 0),
    CHECK (duplicate_count >= 0),
    CHECK (rejected_count >= 0),
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS portfolio.ledger_entries (
    ledger_entry_id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    account_id UUID NOT NULL,
    asset_id VARCHAR,
    asset_name VARCHAR,
    asset_category VARCHAR,
    transaction_type VARCHAR NOT NULL,
    effective_at TIMESTAMP NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    quantity DECIMAL(28, 10),
    unit_price DECIMAL(28, 10),
    gross_amount DECIMAL(18, 2) NOT NULL,
    fees DECIMAL(18, 2) NOT NULL DEFAULT 0,
    net_amount DECIMAL(18, 2) NOT NULL,
    currency VARCHAR NOT NULL DEFAULT 'USD',
    source_platform VARCHAR,
    source_file VARCHAR,
    source_record_id VARCHAR,
    import_run_id UUID,
    reversal_of_entry_id UUID,
    audit_hash VARCHAR NOT NULL,
    entry_status VARCHAR NOT NULL DEFAULT 'posted',
    metadata_json JSON,
    UNIQUE (audit_hash),
    CHECK (gross_amount >= 0),
    CHECK (fees >= 0),
    CHECK (quantity IS NULL OR quantity >= 0),
    CHECK (unit_price IS NULL OR unit_price >= 0),
    CHECK (length(currency) = 3),
    CHECK (entry_status IN ('posted', 'reversed', 'rejected'))
);

-- DuckDB does not currently support partial indexes. Source-record
-- idempotency is enforced by LedgerService/LedgerRepository before insert.
-- This ordinary composite index accelerates those source-key lookups.
CREATE INDEX IF NOT EXISTS ix_ledger_source_record
ON portfolio.ledger_entries (source_platform, source_record_id);

CREATE INDEX IF NOT EXISTS ix_ledger_portfolio_effective
ON portfolio.ledger_entries (portfolio_id, effective_at);

CREATE INDEX IF NOT EXISTS ix_ledger_account_asset
ON portfolio.ledger_entries (account_id, asset_id);

CREATE TABLE IF NOT EXISTS portfolio.ledger_rejections (
    rejection_id UUID PRIMARY KEY,
    import_run_id UUID,
    source_platform VARCHAR,
    source_file VARCHAR,
    source_record_id VARCHAR,
    raw_record_json JSON,
    rejection_reason VARCHAR NOT NULL,
    rejected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio.ledger_reconciliation_results (
    reconciliation_id UUID PRIMARY KEY,
    import_run_id UUID,
    portfolio_id UUID NOT NULL,
    account_id UUID,
    reconciliation_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expected_count INTEGER NOT NULL,
    actual_count INTEGER NOT NULL,
    expected_net_amount DECIMAL(18, 2) NOT NULL,
    actual_net_amount DECIMAL(18, 2) NOT NULL,
    count_difference INTEGER NOT NULL,
    amount_difference DECIMAL(18, 2) NOT NULL,
    status VARCHAR NOT NULL,
    notes VARCHAR,
    CHECK (status IN ('reconciled', 'variance'))
);
