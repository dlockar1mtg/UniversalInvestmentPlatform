from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/metals/tactical_policy_v3_external_price_package_jsonl_authority_resolution_audit.json"
SCRIPT = ROOT / "scripts/audit_external_metals_price_package_jsonl_authority_resolution.py"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_identity_and_lineage() -> None:
    cfg = load_config()
    assert cfg["audit_id"] == "METALS-TACTICAL-POLICY-V3-EXTERNAL-PRICE-PACKAGE-JSONL-AUTHORITY-RESOLUTION-AUDIT-1"
    assert cfg["source_recursive_audit_head"] == "110e926e84ad58307dd18d24c30f2dbe6793bdf8"
    assert cfg["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert cfg["read_only"] is True


def test_required_jsonl_files_are_explicit() -> None:
    cfg = load_config()
    assert cfg["required_files"] == ["metals_current_price.jsonl", "metals_price_history.jsonl"]


def test_required_checks_are_all_true() -> None:
    cfg = load_config()
    assert cfg["required_checks"]
    assert all(value is True for value in cfg["required_checks"].values())


def test_semantic_rules_are_all_true() -> None:
    cfg = load_config()
    assert cfg["semantic_rules"]
    assert all(value is True for value in cfg["semantic_rules"].values())


def test_controls_are_all_false() -> None:
    cfg = load_config()
    assert cfg["controls"]
    assert all(value is False for value in cfg["controls"].values())


def test_decisions() -> None:
    cfg = load_config()
    assert cfg["decision"] == "AUTHORIZE_READ_ONLY_EXTERNAL_METALS_PRICE_PACKAGE_JSONL_AUTHORITY_RESOLUTION_AUDIT"
    assert cfg["next_decision"] == "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES"


def test_script_is_jsonl_aware_and_fail_closed() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for text in [
        "read_jsonl",
        "json.loads(line)",
        "metals_current_price.jsonl",
        "metals_price_history.jsonl",
        "current_price_authority_resolved",
        "dated_history_authority_resolved",
        "identity_columns",
        "date_columns",
        "price_columns",
        "Refusing to overwrite existing audit evidence",
    ]:
        assert text in source
