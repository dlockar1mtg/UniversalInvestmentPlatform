from pathlib import Path
import json

CONFIG = Path("config/metals/tactical_policy_v3_external_price_package_recursive_resolution_audit.json")
SCRIPT = Path("scripts/audit_external_metals_price_package_recursive_resolution.py")


def _config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_identity_and_source_binding():
    cfg = _config()
    assert cfg["audit_id"] == "METALS-TACTICAL-POLICY-V3-EXTERNAL-PRICE-PACKAGE-RECURSIVE-RESOLUTION-AUDIT-1"
    assert cfg["source_row_level_audit_head"] == "871ba774f92aee3d1c8b10654ecf2b4ba91ace3e"
    assert cfg["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_read_only_and_controls_closed():
    cfg = _config()
    assert cfg["read_only"] is True
    assert all(value is False for value in cfg["controls"].values())


def test_required_checks_locked():
    cfg = _config()
    assert all(value is True for value in cfg["required_checks"].values())


def test_decision_and_next_decision():
    cfg = _config()
    assert cfg["decision"] == "AUTHORIZE_READ_ONLY_EXTERNAL_METALS_PRICE_PACKAGE_RECURSIVE_RESOLUTION_AUDIT"
    assert cfg["next_decision"] == "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES"


def test_script_is_recursive_and_read_only():
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'root.rglob("*")' in source
    assert 'suffix == ".csv"' in source
    assert 'suffix == ".json"' in source
    assert '"numeric_price_requires_identity_and_numeric_value": True' in source
    assert '"dated_history_requires_identity_date_and_numeric_value": True' in source
    assert '"no_data_is_synthesized": True' in source
    assert "INSERT " not in source.upper()
    assert "UPDATE " not in source.upper()
    assert "DELETE " not in source.upper()
