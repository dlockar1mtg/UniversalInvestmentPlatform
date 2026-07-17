# Metals Supported Run Order

## Full historical refresh path

1. `run_platform.py` — collect and normalize source data through the ETL pipeline.
2. Run the current prerequisite analytics/macro/vehicle/portfolio/risk pipeline when source data has changed materially. The supplied repository retains versioned orchestrators; v6.2 demonstrates the broad dependency sequence: macro → scoring → vehicles → optimizer/risk/portfolio → dashboard/inspection/export.
3. `run_v8_pipeline.py` — current v8 incremental decision layer.

## Exact v8 pipeline

1. `run_module8.py` — `ForecastingEngine`, then `UncertaintyAdjustedViewsEngine`.
2. `run_module7_v8.py` — `DecisionSupportEngineV8`.
3. `run_monthly_report_v8.py` — `MonthlyCommitteeReportEngine`.
4. `inspect_v8.py` — integrity and result inspection.
5. `export_v8.py` — export nine latest-state CSV files.

## Phase 1 integration extension

6. `[new] export_universal_metals.py` — transform native outputs into Universal contracts.
7. `[existing] scripts/validate_contracts.py` in Universal repository — validate all generated files.
8. `[new] write export_manifest.csv` — record source version, run IDs, row counts, checksums, timestamps, and validation result.
9. Copy or ingest the certified package into Universal integration storage.

A failed upstream step must stop the run. Universal export must never publish a package marked valid when required native outputs are missing or stale.
