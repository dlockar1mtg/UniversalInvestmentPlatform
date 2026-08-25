from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATERIALIZER = ROOT / "scripts" / "materialize_metals_tactical_policy_v3_current_state.py"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_current_state_materialization.py"
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization.json"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_materializer_and_verifier_parse() -> None:
    ast.parse(source(MATERIALIZER))
    ast.parse(source(VERIFIER))


def test_materializer_binds_exact_certified_source_hashes() -> None:
    text = source(MATERIALIZER)
    assert 'EXPECTED_HISTORY_SHA = "c3749acbcf3a6d11ee9a6ca392b8421e7654936af489fbb93a2f4ae659470f31"' in text
    assert 'EXPECTED_CURRENT_SHA = "e18ece1a8dbc5b23f6ec7bb2d014822bdccd8a7f82fca0b6c23d5fda3bc8a4ed"' in text
    assert 'EXPECTED_SOURCE_MANIFEST_SHA = "82ead8e711e0fde4b30fa4e0e7196681e41e7f0ffa363af201c0ee0737473dcf"' in text
    assert 'SOURCE_PACKAGE_ID = "metals-price-history-20260824"' in text


def test_materializer_reuses_locked_classifier_functions() -> None:
    text = source(MATERIALIZER)
    assert "build_vehicle_features" in text
    assert "classify_vehicle" in text
    assert "execute_metals_tactical_policy_v3_historical_regime_research" in text
    assert '"METALS-V3-REGIME-CANDIDATE-RULES-1"' in text
    assert '"METALS-V3-ACTION-MAPPING-1"' in text


def test_materializer_preserves_validated_mapping_exactly() -> None:
    text = source(MATERIALIZER)
    assert '"TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE"' in text
    assert '"MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE"' in text
    assert '"NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY"' in text


def test_materializer_is_offline_and_does_not_touch_duckdb_or_presentation() -> None:
    text = source(MATERIALIZER).lower()
    assert "yfinance" not in text
    assert "requests" not in text
    assert "duckdb" not in text
    assert "sqlalchemy" not in text
    assert "production_database_write_executed\": false" not in text
    assert '"production_database_write_executed": False' in source(MATERIALIZER)
    assert '"presentation_activation_executed": False' in source(MATERIALIZER)
    assert '"network_collection_executed": False' in source(MATERIALIZER)


def test_materializer_requires_absent_output_directory() -> None:
    text = source(MATERIALIZER)
    assert 'if output_dir.exists():' in text
    assert 'raise RuntimeError("current-state output directory already exists")' in text


def test_materializer_requires_exact_governed_vehicle_universe() -> None:
    text = source(MATERIALIZER)
    assert 'EXPECTED_TICKERS = ["BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]' in text
    assert 'if observed != EXPECTED_TICKERS:' in text


def test_bil_is_reference_only_and_cannot_be_directional_opportunity() -> None:
    text = source(MATERIALIZER)
    assert 'if is_reference:' in text
    assert 'tactical_state = "NO_TACTICAL_OVERLAY"' in text
    assert 'state_available = False' in text
    assert 'state_reason = "REFERENCE_CONTROL_NOT_AN_OPPORTUNITY"' in text


def test_live_output_has_required_governed_fields() -> None:
    text = source(MATERIALIZER)
    for field in [
        "asset_id", "ticker", "as_of_date", "candidate_regime", "tactical_state",
        "classifier_rule_version", "action_mapping_version", "price_semantics",
        "source_package_id", "state_available", "state_reason",
    ]:
        assert f'"{field}"' in text


def test_materialization_manifest_preserves_downstream_boundaries() -> None:
    text = source(MATERIALIZER)
    assert '"network_collection_executed": False' in text
    assert '"production_database_write_executed": False' in text
    assert '"presentation_activation_executed": False' in text
    assert '"automatic_execution_executed": False' in text
    assert '"next_decision": "REVIEW_METALS_TACTICAL_POLICY_V3_CURRENT_STATE_MATERIALIZATION"' in text


def test_verifier_recomputes_materialization_from_certified_history() -> None:
    text = source(VERIFIER)
    assert "load_history_jsonl" in text
    assert "materialize_rows" in text
    assert 'require(state_rows == expected_rows, "persisted current-state rows do not exactly match recomputation")' in text


def test_verifier_recomputes_and_checks_state_hash() -> None:
    text = source(VERIFIER)
    assert 'require(manifest["state_sha256"] == sha256_file(state_path), "current-state SHA-256 mismatch")' in text


def test_verifier_requires_exact_materialization_file_set() -> None:
    text = source(VERIFIER)
    assert '["manifest.json", "metals_v3_current_state.jsonl"]' in text
    assert "unexpected materialization files present" in text


def test_live_authorization_remains_source_authority() -> None:
    auth_text = source(AUTH)
    assert '"authorization_decision": "AUTHORIZE_BOUNDED_METALS_V3_LIVE_TACTICAL_INTERPRETATION"' in auth_text
    assert '"current_state_materialization_authorized": true' in auth_text
    assert '"live_tactical_posture_authorized": true' in auth_text
    assert '"production_database_write_authorized": false' in auth_text
    assert '"presentation_activation_authorized": false' in auth_text
    assert '"automatic_execution_authorized": false' in auth_text
