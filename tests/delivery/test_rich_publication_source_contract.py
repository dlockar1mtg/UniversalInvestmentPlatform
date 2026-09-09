from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit_rich_publication_source_contract.py"


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
