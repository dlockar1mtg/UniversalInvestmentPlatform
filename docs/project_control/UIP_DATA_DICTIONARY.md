# UIP Data Dictionary

## Purpose

This dictionary defines the semantic meaning of canonical UIP database objects. Physical columns and types are generated in `generated/UIP_DATABASE_SCHEMA_CATALOG.md`.

## Authority and usage

- Ordered migrations control physical schema changes.
- The generated catalog records the observed database implementation.
- This dictionary controls semantic interpretation.
- Source systems own native facts; certified packages own published snapshots; UIP owns imported canonical and portfolio-level truth.
- History tables preserve observations. Current views select the applicable latest record.

## Shared terms

| Term | Meaning |
|---|---|
| Run | One identifiable source publication, import, or UIP processing execution. |
| Package | Immutable certified delivery snapshot with identifiers, hashes, and validation evidence. |
| Platform | Registered source domain or UIP-owned publishing subsystem. |
| Universal asset ID | Canonical cross-domain asset identifier used inside UIP. |
| History table | Append-oriented record of observations across runs. |
| Current view | Deterministic latest applicable record derived from history. |
| Eligibility | Whether an asset or analytical record may participate in a stated process. |
| Suppression | Explicit exclusion with a reason; never silent disappearance. |
| Lineage | Evidence linking a result to source, package, run, model, contract, and transformation. |

## Canonical objects

### `main.asset_master_current`

Current canonical asset view derived from asset_master_history.

- Physical type: `VIEW`
- Observed rows during generation: `1174`
- Column definitions: see the generated schema catalog.

### `main.asset_master_history`

Append-only canonical history of assets published by source domains. Each row represents an observed asset record for a platform run.

- Physical type: `BASE TABLE`
- Observed rows during generation: `8199`
- Column definitions: see the generated schema catalog.

### `main.forecasts_current`

Current forecast view derived from forecasts_history.

- Physical type: `VIEW`
- Observed rows during generation: `1499`
- Column definitions: see the generated schema catalog.

### `main.forecasts_history`

Append-only history of source and UIP forecast observations.

- Physical type: `BASE TABLE`
- Observed rows during generation: `5254`
- Column definitions: see the generated schema catalog.

### `main.macro_signals_current`

Current macro-signal view.

- Physical type: `VIEW`
- Observed rows during generation: `0`
- Column definitions: see the generated schema catalog.

### `main.macro_signals_history`

Append-only history of canonical macroeconomic or market signals.

- Physical type: `BASE TABLE`
- Observed rows during generation: `0`
- Column definitions: see the generated schema catalog.

### `main.platform_status_current`

Current platform-status view.

- Physical type: `VIEW`
- Observed rows during generation: `3`
- Column definitions: see the generated schema catalog.

### `main.platform_status_history`

Append-only history of source-platform publication and run status.

- Physical type: `BASE TABLE`
- Observed rows during generation: `24`
- Column definitions: see the generated schema catalog.

### `main.portfolio_positions_current`

Current canonical portfolio-position view.

- Physical type: `VIEW`
- Observed rows during generation: `12`
- Column definitions: see the generated schema catalog.

### `main.portfolio_positions_history`

Append-only history of canonical portfolio positions imported or derived for a platform run.

- Physical type: `BASE TABLE`
- Observed rows during generation: `66`
- Column definitions: see the generated schema catalog.

### `main.recommendations_current`

Current recommendation view derived from recommendations_history.

- Physical type: `VIEW`
- Observed rows during generation: `1169`
- Column definitions: see the generated schema catalog.

### `main.recommendations_history`

Append-only history of recommendations and recommendation evidence.

- Physical type: `BASE TABLE`
- Observed rows during generation: `5285`
- Column definitions: see the generated schema catalog.

### `main.risk_metrics_current`

Current risk-metric view derived from risk_metrics_history.

- Physical type: `VIEW`
- Observed rows during generation: `1168`
- Column definitions: see the generated schema catalog.

### `main.risk_metrics_history`

Append-only history of asset-level risk measurements.

- Physical type: `BASE TABLE`
- Observed rows during generation: `2439`
- Column definitions: see the generated schema catalog.

### `main.universal_import_datasets`

Dataset-level evidence for universal import attempts.

- Physical type: `BASE TABLE`
- Observed rows during generation: `132`
- Column definitions: see the generated schema catalog.

### `main.universal_import_error_summary`

Aggregated current import-error summary.

- Physical type: `VIEW`
- Observed rows during generation: `1`
- Column definitions: see the generated schema catalog.

### `main.universal_import_errors`

Detailed import-validation and activation errors.

- Physical type: `BASE TABLE`
- Observed rows during generation: `1`
- Column definitions: see the generated schema catalog.

### `main.universal_import_health`

Current import-health view by source platform.

- Physical type: `VIEW`
- Observed rows during generation: `3`
- Column definitions: see the generated schema catalog.

### `main.universal_imports`

Import-attempt registry containing package, platform, timing, and outcome evidence.

- Physical type: `BASE TABLE`
- Observed rows during generation: `25`
- Column definitions: see the generated schema catalog.

### `main.universal_latest_import_attempt`

Latest import attempt per platform.

- Physical type: `VIEW`
- Observed rows during generation: `3`
- Column definitions: see the generated schema catalog.

### `main.universal_latest_successful_import`

Latest successfully activated import per platform.

- Physical type: `VIEW`
- Observed rows during generation: `3`
- Column definitions: see the generated schema catalog.

### `main.universal_packages`

Registry of received and validated universal delivery packages.

- Physical type: `BASE TABLE`
- Observed rows during generation: `24`
- Column definitions: see the generated schema catalog.

### `main.universal_platform_registry`

Canonical registry of integrated source platforms.

- Physical type: `BASE TABLE`
- Observed rows during generation: `3`
- Column definitions: see the generated schema catalog.

## Null, status, and coverage rules

- Missing analytics must use nulls and explicit status, confidence, eligibility, or suppression fields where the contract provides them.
- An asset must not silently disappear because a forecast, recommendation, risk metric, price, or historical-performance record is unavailable.
- Current views must be deterministic and traceable to history rows.
- Decision-relevant records require complete lineage.

## Historical-performance reserved semantic contract

`historical_performance_history` and `historical_performance_current` are not present in the inspected baseline database. They are reserved for the controlled MTG historical-performance reconstruction and must not be treated as active schema until an ordered migration, universal contract, tests, and certification are approved.

Expected semantic purpose:

- preserve point-in-time performance evidence published by a source domain;
- distinguish eligible from suppressed performance observations;
- retain horizon, period, benchmark, quality, and lineage context;
- support current performance views without overwriting history;
- prohibit unknown universal asset identifiers.

## Change control

A semantic change requires a change-ledger entry when it materially alters cross-domain meaning, portfolio behavior, certification, lineage, or user interpretation.
