from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/metals/tactical_policy_v3_decision_utility_source_resolution_audit.json"
SCRIPT = ROOT / "scripts/audit_metals_decision_utility_source_resolution.py"


def payload() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_identity_and_lineage() -> None:
    p = payload()
    assert p["audit_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-SOURCE-RESOLUTION-AUDIT-1"
    assert p["source_preview_head"] == "6d1d3d2aaac887d1c884e1f01f8606319d8541db"
    assert p["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_questions_are_exact() -> None:
    p = payload()
    assert p["questions"] == [
        "numeric_current_price",
        "dated_price_history",
        "commodity_forecast_lower_bound",
        "commodity_forecast_upper_bound",
        "vehicle_forecast_bounds",
        "asset_rationale_or_recommendation_explanation",
    ]


def test_semantic_guardrails() -> None:
    assert all(payload()["semantic_rules"].values())


def test_read_only_boundaries() -> None:
    assert all(value is False for value in payload()["controls"].values())


def test_decisions() -> None:
    p = payload()
    assert p["decision"] == "AUTHORIZE_READ_ONLY_METALS_DECISION_UTILITY_SOURCE_RESOLUTION_AUDIT"
    assert p["next_decision"] == "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES"


def test_script_is_read_only_and_non_overwriting() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "duckdb.connect(str(db), read_only=True)" in source
    assert "Refusing to overwrite audit evidence" in source
    assert "CREATE TABLE" not in source
    assert "INSERT INTO" not in source
    assert "UPDATE " not in source
    assert "DELETE FROM" not in source


def test_script_searches_price_history_bounds_and_rationale() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for token in (
        "current_price",
        "adjusted_close",
        "observation_date",
        "lower_bound",
        "upper_bound",
        "rationale",
        "explanation",
    ):
        assert token in source
