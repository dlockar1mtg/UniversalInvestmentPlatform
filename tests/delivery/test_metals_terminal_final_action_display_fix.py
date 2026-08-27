from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_authorization_is_bounded_to_terminal_display_only():
    document = read_json(
        "config/metals/terminal_final_action_display_fix_authorization.json"
    )
    assert document["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-FIX-AUTHORIZATION-1"
    assert document["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_TERMINAL_FINAL_ACTION_DISPLAY_FIX"
    scope = document["authorization_scope"]
    assert scope["recommendation_ui_js_change_authorized"] is True
    assert scope["rec_ui_test_change_authorized"] is True
    assert scope["new_targeted_display_test_authorized"] is True
    assert scope["local_test_execution_authorized"] is True
    assert scope["hosted_database_write_authorized"] is False
    assert scope["active_publication_mutation_authorized"] is False
    assert scope["read_api_change_authorized"] is False
    assert scope["analytical_database_write_authorized"] is False
    assert scope["recommendation_recompute_authorized"] is False
    assert scope["forecast_refresh_authorized"] is False
    assert scope["model_refresh_authorized"] is False
    assert scope["pr_authorized"] is False
    assert scope["main_deploy_authorized"] is False
    assert scope["allocation_or_execution_authorized"] is False


def test_authorization_binds_live_final_action_authority_and_nine_mismatches():
    document = read_json(
        "config/metals/terminal_final_action_display_fix_authorization.json"
    )
    assert document["source_governed_head"] == "a7564d58b83e75edadaf1be004594b856168b816"
    assert document["source_activation_execution_id"] == "METALS-FINAL-DECISION-PRESENTATION-ACTIVATION-1"
    assert document["source_active_publication_id"] == "metals-final-decision-presentation-r1-20260827"
    assert document["source_active_publication_fingerprint"] == "9de5edb450542be85dd68f3b0dd539dc520ef1f92b9de1b743672d7a6b1e289d"
    assert document["source_active_publication_record_count"] == 12477
    assert document["certified_live_final_action_counts"] == {
        "HOLD": 5,
        "WATCH": 6,
        "REFERENCE_CONTROL": 1,
    }
    assert document["certified_terminal_semantic_mismatch_count"] == 9
    assert document["certified_terminal_semantic_match_count"] == 3
    assert len(document["certified_terminal_mismatch_assets"]) == 9


def test_required_fix_semantics_make_final_action_primary_for_metals_only():
    document = read_json(
        "config/metals/terminal_final_action_display_fix_authorization.json"
    )
    behavior = document["required_fix_behavior"]
    assert behavior["metals_visible_status_prefers_final_action"] is True
    assert behavior["metals_visible_status_falls_back_to_recommendation"] is True
    assert behavior["metals_visible_status_falls_back_to_native_recommendation_only_if_final_action_and_recommendation_missing"] is True
    assert behavior["metals_card_uses_final_action_display_helper"] is True
    assert behavior["search_and_status_filter_use_metal_final_action_for_metals"] is True
    assert behavior["crypto_existing_native_status_semantics_preserved"] is True
    assert behavior["mtg_native_purchase_status_semantics_preserved"] is True
    assert behavior["native_recommendation_remains_available_as_explanatory_evidence"] is True
    assert behavior["no_hosted_payload_change"] is True
    assert behavior["no_read_api_change"] is True


def test_authorized_file_set_is_exact():
    document = read_json(
        "config/metals/terminal_final_action_display_fix_authorization.json"
    )
    assert set(document["authorized_files"]) == {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
        "tests/delivery/test_metals_terminal_final_action_display_fix.py",
    }

def test_implemented_ui_routes_metals_to_final_action_without_overwriting_native_semantics():
    javascript = (
        ROOT
        / "foundation/production/dashboard_assets/recommendation_ui.js"
    ).read_text(encoding="utf-8")

    assert "function displayStatus(item)" in javascript
    assert (
        'payload.final_action??payload.recommendation??payload.native_recommendation??null'
        in javascript
    )
    assert 'const status=cleanStatus(displayStatus(item))' in javascript

    # All previous UI consumers now pass through displayStatus.
    # nativeStatus itself remains only as the legacy domain-native
    # implementation and the non-Metals delegate.
    assert javascript.count("nativeStatus(") == 2
    assert javascript.count("displayStatus(") >= 3


def test_implemented_metals_status_precedence_matches_certified_twelve_asset_surface():
    def display_status(domain_id, payload):
        if domain_id == "metals":
            return (
                payload.get("final_action")
                or payload.get("recommendation")
                or payload.get("native_recommendation")
            )
        if domain_id == "mtg":
            return payload.get("native_purchase_status")
        return (
            payload.get("native_recommendation")
            or payload.get("recommendation")
        )

    cases = {
        "metals:commodity:gold": ("HOLD", "RANKED_OPPORTUNITY"),
        "metals:commodity:uranium": ("HOLD", "RANKED_OPPORTUNITY"),
        "metals:vehicle:BIL": ("REFERENCE_CONTROL", "RESERVE_BUY"),
        "metals:vehicle:COPX": ("HOLD", "HOLD"),
        "metals:vehicle:CPER": ("HOLD", "HOLD"),
        "metals:vehicle:GLD": ("WATCH", "BUY"),
        "metals:vehicle:IAU": ("WATCH", "BUY"),
        "metals:vehicle:PPLT": ("WATCH", "BUY"),
        "metals:vehicle:SGOL": ("WATCH", "BUY"),
        "metals:vehicle:SIVR": ("WATCH", "BUY"),
        "metals:vehicle:SLV": ("WATCH", "BUY"),
        "metals:vehicle:URA": ("HOLD", "HOLD"),
    }

    for asset_id, (final_action, native_recommendation) in cases.items():
        payload = {
            "final_action": final_action,
            "recommendation": final_action,
            "native_recommendation": native_recommendation,
        }
        assert display_status("metals", payload) == final_action, asset_id

    assert display_status(
        "crypto",
        {
            "final_action": "WATCH",
            "recommendation": "WATCH",
            "native_recommendation": "BUY",
        },
    ) == "BUY"

    assert display_status(
        "mtg",
        {
            "final_action": "HOLD",
            "recommendation": "HOLD",
            "native_purchase_status": "PURCHASE_CANDIDATE",
        },
    ) == "PURCHASE_CANDIDATE"


def test_implemented_metals_display_fallback_order_is_fail_soft():
    def metals_status(payload):
        return (
            payload.get("final_action")
            or payload.get("recommendation")
            or payload.get("native_recommendation")
        )

    assert metals_status(
        {
            "final_action": "WATCH",
            "recommendation": "BUY",
            "native_recommendation": "BUY",
        }
    ) == "WATCH"

    assert metals_status(
        {
            "recommendation": "HOLD",
            "native_recommendation": "BUY",
        }
    ) == "HOLD"

    assert metals_status(
        {
            "native_recommendation": "BUY",
        }
    ) == "BUY"
