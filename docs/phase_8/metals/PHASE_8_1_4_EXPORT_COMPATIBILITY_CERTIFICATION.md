# Phase 8.1.4 — Metals v8 Export Gap Analysis and Compatibility Certification

## Certification decision

**PASS — the certified Metals adapter release 1.2.2 remains compatible with the live Metals v8.1 export surface.**

No adapter compatibility upgrade is required before implementing the newly identified provider and vehicle-constraint capabilities.

## Validation execution

Evaluation date: 2026-07-20

Native command:

    python export_v8.py

Universal command:

    python scripts/run_metals_universal_export.py --metals-root C:\Users\DevonLockard\metals

Result:

    METALS UNIVERSAL EXPORT: PASS

Certified package:

    metals-20260720T212007Z-b67a1a03

Source interface: `metals-native-v8`

Contract version: `v1`

Validation issues: none

## Native v8 output verification

| Native output | Rows | Integration treatment |
|---|---:|---|
| latest_metal_forecasts.csv | 16 | Transformed into universal forecasts |
| latest_forecast_model_components.csv | 64 | Supporting forecast evidence |
| latest_learned_regime_probabilities.csv | 12 | Supporting forecast and regime evidence |
| latest_uncertainty_adjusted_views.csv | 32 | Supporting recommendation evidence |
| latest_recommendation_change_explanations.csv | 10 | Supporting recommendation audit |
| latest_metal_opportunity_rankings.csv | 2 | Transformed into universal recommendations |
| latest_data_freshness_details.csv | 21 | Supporting status and freshness evidence |
| latest_platform_health_score.csv | 1 | Supporting platform-status evidence |
| latest_monthly_committee_report.csv | 1 | Supporting report metadata |

All native row counts match the Phase 1 frozen output inventory.

## Universal contract outputs

The adapter generated and validated:

- `asset_master.csv`
- `forecasts.csv`
- `platform_status.csv`
- `portfolio_positions.csv`
- `recommendations.csv`
- `risk_metrics.csv`
- `export_manifest.csv`

The package also retained seven native evidence files under `supporting_native`.

## Gap assessment

### Resolved by transformation

- Stable universal asset identifiers
- Forecast horizon and method alignment
- Recommendation score and confidence normalization
- Platform status normalization
- Contract validation and package provenance
- Checksums and manifest generation

### Resolved through narrow read-only access

Native v8 does not export complete portfolio-position or risk datasets. Adapter 1.2.2 continues to obtain those surfaces through narrowly scoped read-only DuckDB queries and transforms them into universal contracts.

This remains compatible with the certified integration boundary because the adapter does not modify the Metals database or import Metals runtime modules.

### Intentionally retained as supporting evidence

Model components, regime probabilities, uncertainty-adjusted views, recommendation changes, data freshness, platform health detail, and committee-report metadata remain evidence rather than new first-class universal tables.

This avoids duplicating the universal forecasting, risk, status, and reporting domains.

## Compatibility conclusion

The live Metals v8.1 source has not drifted from the Phase 1 certified interface. The universal adapter produces a complete valid package without source modification, contract exceptions, or missing required datasets.

Phase 8 implementation may proceed without redesigning the file-based adapter.

## Phase 8.1 completion status

- Source health baseline: PASS
- External component inventory: COMPLETE
- Capability decision matrix: COMPLETE
- Canonical export compatibility: PASS
- Universal regression baseline: 1,028 tests passed
- Blocking issues: none

## Authorized next phase

Proceed to **Phase 8.2 — Metals Official Provider Adapters**, beginning with deterministic EIA uranium and World Bank parser contracts and offline fixtures.
