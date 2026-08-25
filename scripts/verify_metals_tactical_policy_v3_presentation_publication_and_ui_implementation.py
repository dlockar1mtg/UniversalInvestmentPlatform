from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    extension = json.loads(read("config/presentation/dash_read_1_metals_tactical_extension.json"))
    projection = read("foundation/presentation/metals_tactical_projection.py")
    publication = read("foundation/presentation/publication_model.py")
    ui = read("foundation/production/dashboard_assets/metals_tactical_ui.js")

    assert extension["version"] == "1.1.0"
    assert extension["source_database_sha256"] == EXPECTED_DB_SHA
    assert extension["controls"]["tactical_posture_authorized"] is True
    assert extension["controls"]["cross_domain_rank_authorized"] is False
    assert extension["controls"]["allocation_policy_authorized"] is False
    assert extension["controls"]["automatic_execution_authorized"] is False
    surface = extension["surfaces"]["tactical_state"]
    assert surface["source"] == "metals_tactical_state_current"
    assert surface["asset_identity"] == "universal_asset_id"
    for field in (
        "universal_asset_id", "ticker", "as_of_date", "candidate_regime",
        "tactical_state", "state_available", "state_reason",
        "is_reference_control", "source_state_sha256",
        "source_materialization_manifest_sha256",
    ):
        assert field in surface["required_fields"]

    assert f'EXPECTED_SOURCE_SHA256 = "{EXPECTED_DB_SHA}"' in projection
    assert 'payload.get("version") != "1.1.0"' in projection
    assert 'len(surfaces) != 7' in projection
    assert '"tactical_posture_authorized": True' in projection
    assert "FROM metals_tactical_state_current ORDER BY universal_asset_id" in projection
    assert 'if bool(row.get("is_reference_control")):' in projection
    assert '_record("tactical_state", asset_id, asset_id, row)' in projection
    assert "records.extend(build_metals_tactical_records(repository_root, connection, source_sha256))" in publication

    assert 'const RECORD_TYPE="tactical_state"' in ui
    assert 'const DOMAIN="metals"' in ui
    assert "not a negative long-term thesis" in ui
    assert "sell signal" in ui
    assert "zero expected return" in ui
    assert "allocation instruction" in ui
    assert "does not replace the certified long-term recommendation" in ui
    assert "Reference/control vehicle; not an opportunity recommendation." in ui
    assert "window.UIPMetalsTactical" in ui

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "implementation_id": "METALS-TACTICAL-POLICY-V3-PRESENTATION-PUBLICATION-AND-UI-IMPLEMENTATION-1",
        "source_database_sha256": EXPECTED_DB_SHA,
        "record_type": "tactical_state",
        "domain_id": "metals",
        "source_relation": "metals_tactical_state_current",
        "presentation_projection_implemented": True,
        "ui_helper_implemented": True,
        "reference_control_excluded_from_opportunity_projection": True,
        "live_presentation_activation_authorized": False,
        "analytical_database_write_authorized": False,
        "next_decision": "CERTIFY_METALS_TACTICAL_POLICY_V3_PRESENTATION_PUBLICATION_AND_UI_IMPLEMENTATION",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
