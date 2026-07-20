# Phase 7.2 — Live Provider and Portfolio Integrations

Phase 7.2 adds secret-safe Alpha Vantage and FRED adapters plus strict CSV holdings ingestion.

## Holdings CSV

Start with `templates/portfolio_holdings_template.csv`. Required columns are `position_id`, `account_id`, `portfolio_group`, `asset_type`, `asset_id`, `quantity`, `cost_basis`, `market_value`, `currency`, and `as_of`. Optional columns are `symbol`, `name`, `provider_symbol`, `target_weight`, `liquidity_class`, and `notes`.

`portfolio_group` must be `crypto`, `etf`, `metals`, or `mtg`. Decimal values must be non-negative, `target_weight` is a decimal from 0 through 1, currency is a three-letter code, and `as_of` must include a timezone. Run `python scripts/validate_portfolio_csv.py holdings.csv` before import.

## Secrets and live check

Set `UIIP_ALPHA_VANTAGE_API_KEY` and `UIIP_FRED_API_KEY` in the process environment. Never place keys in CSV, source control, logs, or command output. Optional test selectors are `UIIP_ALPHA_VANTAGE_TEST_SYMBOL` (default `SPY`) and `UIIP_FRED_TEST_SERIES` (default `MORTGAGE30US`). Run `python scripts/check_live_providers.py` only when live connectivity is desired.
