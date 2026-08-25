import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "tactical_policy_v3_crypto_parity_visual_utility_refresh_design.json"

doc = json.loads(PATH.read_text(encoding="utf-8"))

assert doc["design_id"] == "METALS-TACTICAL-POLICY-V3-CRYPTO-PARITY-VISUAL-UTILITY-REFRESH-DESIGN-1"
assert doc["source_recovery_review_head"] == "6351738eeff72270d6490ca2db7cb47380b22ccf"
assert doc["production_main_baseline_head"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
assert doc["objective"] == "ADAPT_CERTIFIED_CRYPTO_PRESENTATION_PATTERNS_TO_METALS_WITH_METALS_NATIVE_ANALYTICAL_SEMANTICS"
assert all(doc["visual_principles"].values())
assert all(doc["reuse_targets"].values())
assert doc["metals_overview"]["featured_opportunity_cards_required"] is True
assert doc["metals_overview"]["all_metals_table_retained_as_secondary_view"] is True
assert doc["metals_overview"]["reference_control_handling"]["bil_is_reference_control"] is True
assert doc["metals_overview"]["reference_control_handling"]["bil_must_not_be_presented_as_featured_opportunity"] is True
assert doc["metals_detail"]["hero_long_term_thesis_required"] is True
assert doc["metals_detail"]["tactical_context_panel_required"] is True
assert all(doc["semantic_guardrails"].values())
assert doc["implementation_boundaries"]["visual_design_authorized"] is True
for key, value in doc["implementation_boundaries"].items():
    if key != "visual_design_authorized":
        assert value is False, key
assert doc["candidate_runtime_files"] == [
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/dashboard.css",
]
assert doc["design_decision"] == "APPROVE_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH_DESIGN_FOR_IMPLEMENTATION_CONSIDERATION"
assert doc["next_decision"] == "AUTHORIZE_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH_IMPLEMENTATION"

print(json.dumps({
    "status": "PASS",
    "read_only": True,
    "design_id": doc["design_id"],
    "crypto_visual_reference": True,
    "metals_native_semantics_preserved": True,
    "featured_cards_required": True,
    "secondary_table_retained": True,
    "bil_reference_control": True,
    "candidate_runtime_file_count": len(doc["candidate_runtime_files"]),
    "runtime_implementation_authorized": doc["implementation_boundaries"]["runtime_implementation_authorized"],
    "next_decision": doc["next_decision"],
}, indent=2, sort_keys=True))
