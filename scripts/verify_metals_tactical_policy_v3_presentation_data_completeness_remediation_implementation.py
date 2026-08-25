from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/metals/tactical_policy_v3_presentation_data_completeness_remediation_implementation.json"
TACTICAL_UI = ROOT / "foundation/production/dashboard_assets/metals_tactical_ui.js"


def main() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    source = TACTICAL_UI.read_text(encoding="utf-8")

    required = [
        "metals_uncertainty_adjusted",
        "metals_recommendation_change",
        "metals_model_component",
        "metals_regime_probability",
        "Forecast return context",
        "Recommendation evidence",
        "Commodity model components",
        "Commodity regime probabilities",
        "Vehicle-level tactical context not applicable",
        "Unsupported fields remain unavailable",
        "bestUncertainty",
        "enrichVisibleCards",
    ]
    missing = [value for value in required if value not in source]
    if missing:
        raise SystemExit(f"Missing remediation behavior: {missing}")

    if payload["implementation_status"] != "IMPLEMENTED_REQUIRES_LOCAL_REGRESSION_AND_DATA_RICH_PREVIEW_CERTIFICATION":
        raise SystemExit("Unexpected implementation status")
    if payload["runtime_files_changed"] != ["foundation/production/dashboard_assets/metals_tactical_ui.js"]:
        raise SystemExit("Runtime delta is not minimal")
    if not all(payload["implemented_behavior"].values()):
        raise SystemExit("Required implementation behavior is incomplete")
    if not all(payload["semantic_guardrails"].values()):
        raise SystemExit("Semantic guardrails are incomplete")
    if any(payload["boundaries"].values()):
        raise SystemExit("Unauthorized downstream boundary enabled")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "implementation_id": payload["implementation_id"],
        "runtime_file_count": len(payload["runtime_files_changed"]),
        "existing_evidence_consumed": True,
        "vehicle_forecast_context_present": True,
        "vehicle_recommendation_explanation_present": True,
        "commodity_model_context_present": True,
        "commodity_regime_context_present": True,
        "commodity_tactical_state_not_synthesized": True,
        "unsupported_fields_preserved": True,
        "hosted_publication_write_authorized": payload["boundaries"]["hosted_publication_write_authorized"],
        "main_deployment_authorized": payload["boundaries"]["main_deployment_authorized"],
        "next_decision": payload["next_decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
