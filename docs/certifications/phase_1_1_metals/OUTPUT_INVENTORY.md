# Output Inventory

The active v8 exporter writes nine CSVs from current-state views. See `OUTPUT_INVENTORY.csv` for exact row counts and columns from the supplied archive.

| Native output | Purpose | Universal destination |
|---|---|---|
| latest_metal_forecasts.csv | Multi-horizon return forecasts and uncertainty | forecasts |
| latest_forecast_model_components.csv | Ensemble component audit | supporting forecast detail / manifest attachment |
| latest_learned_regime_probabilities.csv | Learned state probabilities | forecast/risk supporting detail |
| latest_uncertainty_adjusted_views.csv | Penalized expected-return views | forecasts and recommendation evidence |
| latest_metal_opportunity_rankings.csv | Ranked opportunities and rationale | recommendations |
| latest_recommendation_change_explanations.csv | Action/weight/confidence deltas | recommendation history/audit |
| latest_data_freshness_details.csv | Source freshness diagnostics | platform_status and export_manifest evidence |
| latest_platform_health_score.csv | Overall pipeline health and grade | platform_status |
| latest_monthly_committee_report.csv | Human-report pointer and metadata | export_manifest |

The HTML committee report and data explorer are human-facing artifacts. They should be recorded in the manifest, not parsed as canonical data.
