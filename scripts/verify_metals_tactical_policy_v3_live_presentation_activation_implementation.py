from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTTP = ROOT / "foundation" / "production" / "http_service.py"
HTML = ROOT / "foundation" / "production" / "dashboard_assets" / "dashboard.html"
CLI = ROOT / "scripts" / "activate_metals_tactical_policy_v3_live_presentation.py"
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_fresh_live_presentation_activation_authorization.json"


def main() -> int:
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    http = HTTP.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    cli = CLI.read_text(encoding="utf-8")
    required_http = '@app.get("/dashboard/assets/metals_tactical_ui.js"'
    required_html = '<script src="/dashboard/assets/metals_tactical_ui.js" defer></script>'
    if required_http not in http or required_html not in html:
        raise RuntimeError("Metals tactical UI live wiring is incomplete.")
    for token in (
        "publish_presentation_bundle",
        "validate_publication_bundle",
        "UIIP_DATABASE_URL",
        "EXPECTED_FINGERPRINT",
        "EXPECTED_RECORD_COUNT = 4181",
        "EXPECTED_TACTICAL_COUNT = 10",
        "duckdb.connect(str(database), read_only=True)",
        "METALS-TACTICAL-POLICY-V3-FRESH-LIVE-PRESENTATION-ACTIVATION-AUTHORIZATION-1",
        "AUTHORIZE_ONE_FRESH_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION",
        "metals-v3-live-tactical-r2-20260825",
        "consumed_prior_authorization_may_be_reused",
        "failed_prior_publication_id_may_be_reused",
    ):
        if token not in cli:
            raise RuntimeError(f"Fresh live activation CLI missing required control: {token}")
    if "METALS-TACTICAL-POLICY-V3-LIVE-PRESENTATION-ACTIVATION-AUTHORIZATION-1" in cli:
        raise RuntimeError("CLI still accepts the consumed prior authorization ID.")
    if 'default="metals-v3-live-tactical-20260825"' in cli:
        raise RuntimeError("CLI still defaults to the failed prior publication ID.")
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "implementation_id": "METALS-TACTICAL-POLICY-V3-FRESH-LIVE-PRESENTATION-ACTIVATION-EXECUTABLE-BINDING-1",
        "source_authorization_id": auth["authorization_id"],
        "source_database_sha256": auth["source_database_sha256"],
        "certified_content_fingerprint": auth["certified_content_fingerprint"],
        "fresh_target_publication_id": auth["fresh_target_publication_id"],
        "execution_limit": auth["execution_limit"],
        "dashboard_asset_route_wired": True,
        "dashboard_html_script_wired": True,
        "bounded_activation_cli_implemented": True,
        "fresh_authorization_bound": True,
        "prior_consumed_authorization_rejected": True,
        "prior_failed_publication_rejected": True,
        "live_activation_executed": False,
        "analytical_database_write_authorized": False,
        "next_decision": "EXECUTE_ONE_FRESH_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION",
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
