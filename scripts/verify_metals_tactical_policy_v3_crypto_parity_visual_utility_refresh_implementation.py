from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/metals/tactical_policy_v3_crypto_parity_visual_utility_refresh_implementation.json"
REC_UI = ROOT / "foundation/production/dashboard_assets/recommendation_ui.js"
TACTICAL_UI = ROOT / "foundation/production/dashboard_assets/metals_tactical_ui.js"


def require(text: str, needle: str, message: str) -> None:
    if needle not in text:
        raise RuntimeError(message)


def main() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    rec = REC_UI.read_text(encoding="utf-8")
    tactical = TACTICAL_UI.read_text(encoding="utf-8")

    if payload["implementation_id"] != "METALS-TACTICAL-POLICY-V3-CRYPTO-PARITY-VISUAL-UTILITY-REFRESH-IMPLEMENTATION-1":
        raise RuntimeError("Unexpected implementation ID.")
    if payload["source_authorization_head"] != "187342ec1d4485df4aa6143f3232ffb5fc5d1bfb":
        raise RuntimeError("Unexpected implementation authorization HEAD.")
    if payload["production_main_baseline_head"] != "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd":
        raise RuntimeError("Unexpected production main baseline.")

    require(rec, "function renderMetalsDomain", "Metals card-first domain renderer is missing.")
    require(rec, "metals-card-grid", "Metals card grid is missing.")
    require(rec, "featured=filtered.filter(item=>!isBil(item))", "BIL featured-card exclusion is missing.")
    require(rec, "All Metals research · secondary evidence table", "Secondary Metals table is missing.")
    require(rec, "1M momentum", "1M momentum is missing.")
    require(rec, "3M momentum", "3M momentum is missing.")
    require(rec, "6M momentum", "6M momentum is missing.")
    require(rec, "Current drawdown", "Drawdown context is missing.")
    require(rec, "vs MA50", "MA50 context is missing.")
    require(rec, "vs MA200", "MA200 context is missing.")
    require(rec, "LONG-TERM METALS OUTLOOK", "Metals long-term hero is missing.")
    require(rec, "Forecast & model evidence", "Forecast/model evidence panel is missing.")
    require(rec, "Why this recommendation", "Rationale panel is missing.")
    require(rec, "Risk assessment", "Risk panel is missing.")
    require(rec, "await hydrateMetalsResearch()", "Metals detail hydration is missing.")
    require(rec, "window.UIPMetalsTactical?.renderTacticalPanel", "Tactical helper integration is missing.")
    require(rec, "No tactical overlay is not a sell signal", "No-overlay semantic guardrail is missing.")
    require(rec, 'REC_DOMAINS=["crypto","metals","mtg"]', "Domain boundary changed.")
    require(rec, "native_purchase_status", "MTG native semantics disappeared.")
    require(rec, "3-YEAR GROWTH OUTLOOK", "Crypto strategic view disappeared.")

    require(tactical, "metals-tactical-metrics", "Enriched tactical metrics are missing.")
    require(tactical, "return_1m_pct", "Tactical 1M momentum source is missing.")
    require(tactical, "distance_ma50_pct", "Tactical MA50 source is missing.")
    require(tactical, "current_drawdown_pct", "Tactical drawdown source is missing.")
    require(tactical, "NO_OVERLAY_COPY", "No-overlay semantic guardrail is missing.")

    boundaries = payload["boundaries"]
    if any(boundaries.values()):
        raise RuntimeError("Unauthorized downstream boundary enabled.")

    result = {
        "status": "PASS",
        "read_only": True,
        "implementation_id": payload["implementation_id"],
        "runtime_file_count": len(payload["runtime_files_changed"]),
        "card_first_metals_overview": True,
        "bil_excluded_from_featured": True,
        "secondary_table_retained": True,
        "momentum_and_drawdown_visuals_present": True,
        "long_term_detail_hero_present": True,
        "enriched_tactical_panel_present": True,
        "crypto_and_mtg_boundaries_preserved": True,
        "main_deployment_authorized": False,
        "next_decision": payload["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
