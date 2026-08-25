import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config/metals/tactical_policy_v3_crypto_parity_visual_utility_refresh_implementation_authorization.json"

data = json.loads(PATH.read_text(encoding="utf-8"))

assert data["authorization_id"] == "METALS-TACTICAL-POLICY-V3-CRYPTO-PARITY-VISUAL-UTILITY-REFRESH-IMPLEMENTATION-AUTHORIZATION-1"
assert data["source_design_id"] == "METALS-TACTICAL-POLICY-V3-CRYPTO-PARITY-VISUAL-UTILITY-REFRESH-DESIGN-1"
assert data["source_design_head"] == "aaf9278aa6d973a78663836174849bf78df7a447"
assert data["production_main_baseline_head"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
assert data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH_IMPLEMENTATION"
assert len(data["authorized_runtime_files"]) == 3
assert data["required_behavior"]["card_first_metals_overview"] is True
assert data["required_behavior"]["all_metals_table_retained_as_secondary_view"] is True
assert data["required_behavior"]["tactical_context_separate_from_long_term_thesis"] is True
assert data["required_behavior"]["bil_reference_control_only"] is True
assert data["required_behavior"]["bil_excluded_from_featured_opportunities"] is True
assert data["required_behavior"]["no_tactical_overlay_not_sell"] is True
assert data["implementation_boundaries"]["runtime_implementation_authorized"] is True
for key, value in data["implementation_boundaries"].items():
    if key != "runtime_implementation_authorized":
        assert value is False
assert data["implementation_strategy"]["preserve_crypto_behavior"] is True
assert data["implementation_strategy"]["preserve_mtg_behavior"] is True
assert data["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH"

print(json.dumps({
    "status": "PASS",
    "read_only": True,
    "authorization_id": data["authorization_id"],
    "authorization_decision": data["authorization_decision"],
    "runtime_implementation_authorized": data["implementation_boundaries"]["runtime_implementation_authorized"],
    "main_deployment_authorized": data["implementation_boundaries"]["main_deployment_authorized"],
    "authorized_runtime_file_count": len(data["authorized_runtime_files"]),
    "card_first_metals_overview": data["required_behavior"]["card_first_metals_overview"],
    "tactical_layer_separate": data["required_behavior"]["tactical_context_separate_from_long_term_thesis"],
    "bil_reference_control_only": data["required_behavior"]["bil_reference_control_only"],
    "next_decision": data["next_decision"],
}, indent=2, sort_keys=True))
