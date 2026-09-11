from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_rich_publication_source_contract.py"
WORKFLOW = ROOT / ".github" / "workflows" / "rich-publication-contract-rehearsal.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("rich_source_contract", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_mtg_contracts_pin_exact_certified_hashes():
    module = _load_module()
    expected = module.EXPECTED_MTG
    assert expected["premium"]["rows"] == 787
    assert expected["premium"]["sha256"] == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    assert expected["collector"]["sha256"] == "b81ee16a310f8a4f9dcbccf21047e31396df9810d53291cdb9b631fbe046d457"
    assert expected["collector_horizon"]["sha256"] == "585257520197fff9700c0a9f1d1d517af60c1792d944f3f4dab1f65c564cf3e8"
    assert expected["precollector"]["sha256"] == "80d8a60ffcc35d688e6560ee94f2d1f910fb3cd961eea097d5ffd00862034f81"
    assert expected["precollector_scenario"]["sha256"] == "74caad4f8d39ce255455854ab5a5459779f6e73adc0afebc8269e769858aed0a"


def test_metals_native_contracts_cover_exactly_five_certified_families():
    module = _load_module()
    contracts = module.NATIVE_METALS_CERTIFIED_CONTRACTS
    assert set(contracts) == {
        "current_price",
        "price_history",
        "data_freshness",
        "platform_health",
        "model_component",
    }
    assert contracts["current_price"]["expected_rows"] == 11
    assert contracts["data_freshness"]["expected_rows"] == 20
    assert contracts["platform_health"]["expected_rows"] == 1
    assert contracts["model_component"]["expected_rows"] == 81
    assert contracts["data_freshness"]["manifest_authority"] == "UIP_NATIVE_METALS_DATA_FRESHNESS_V1"
    assert contracts["platform_health"]["manifest_authority"] == "UIP_NATIVE_METALS_PLATFORM_HEALTH_V1"
    assert contracts["model_component"]["manifest_authority"] == "UIP_NATIVE_METALS_MODEL_COMPONENT_V1"
    assert contracts["model_component"]["expected_source_model_ids"] == ["uip-metals-native-trend-v1"]


def test_metals_native_contracts_require_publication_safety_flags():
    module = _load_module()
    assert module.SAFETY_FALSE_KEYS == (
        "postgres_write_performed",
        "publication_staged",
        "publication_activated",
    )
    for family in ("data_freshness", "platform_health", "model_component"):
        assert module.NATIVE_METALS_CERTIFIED_CONTRACTS[family]["require_nonlegacy"] is True


def test_rehearsal_certifies_five_of_ten_without_opening_publication_gate():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert 'assert evidence["status"] == "FAIL_CLOSED"' in workflow
    assert 'assert evidence["metals_certified_family_count"] == 5' in workflow
    assert 'assert evidence["metals_required_family_count"] == 10' in workflow
    assert 'assert evidence["metals_remaining_family_count"] == 5' in workflow
    assert 'test "${{ steps.rich_audit.outputs.audit_status }}" = "1"' in workflow
    assert "RICH_PUBLICATION_RECOVERY_STATE=5_OF_10_FAIL_CLOSED_PASS" in workflow
