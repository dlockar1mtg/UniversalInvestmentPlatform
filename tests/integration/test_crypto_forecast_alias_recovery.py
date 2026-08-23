from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_crypto_forecast_alias_recovery_is_current_package_scoped_and_fail_closed():
    source = read("scripts/repair_r3_crypto_forecast_alias_backfill.py")
    assert 'WHERE lower(platform_id) = \'crypto\'' in source
    assert "last_package_id" in source
    assert "last_import_id" in source
    assert "HEALTHY" in source
    assert "ACTIVE" in source
    assert "successful_import_id" in source
    assert "dataset_name = 'forecasts'" in source
    assert '("PASS", "PASS", "IMPORTED")' in source
    assert "duplicate asset/horizon/method keys" in source
    assert "Refusing to overwrite non-null" in source
    assert 'con.execute("BEGIN TRANSACTION")' in source
    assert 'con.execute("ROLLBACK")' in source


def test_crypto_forecast_alias_recovery_uses_governed_contract_aliases_only():
    source = read("scripts/repair_r3_crypto_forecast_alias_backfill.py")
    aliases = {
        '"forecast_value_base": "point_forecast"',
        '"forecast_value_bear": "lower_bound"',
        '"forecast_value_bull": "upper_bound"',
        '"expected_total_return": "expected_return"',
        '"probability_positive_return": "probability_positive"',
        '"forecast_confidence": "confidence_score"',
        '"scenario_name": "scenario"',
    }
    for alias in aliases:
        assert alias in source
    assert '"synthetic_values_created": False' in source
    assert '"native_model_rerun": False' in source
    assert '"source_refresh": False' in source


def test_generic_loader_already_supports_crypto_forecast_alias_contract():
    loader = read("foundation/import_engine/loader.py")
    assert '"forecast_value_base": "point_forecast"' in loader
    assert '"expected_total_return": "expected_return"' in loader
    assert '"forecast_confidence": "confidence_score"' in loader
    assert '"scenario_name": "scenario"' in loader
