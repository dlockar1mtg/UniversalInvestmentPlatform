import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from foundation.presentation.metals_vehicle_implementation_projection import (
    build_metals_vehicle_implementation_records,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_metals_vehicle_ranking_evidence.py"
PRESENTATION = ROOT / "config" / "presentation"
NAMES = (
    "metals_vehicle_ranking_evidence_v1.json",
    "metals_vehicle_ranking_component_evidence_v1.json",
    "metals_vehicle_presentation_authorization_v1.json",
)
SOURCE = {"run_id": 1, "head_sha": "0" * 40, "artifact_name": "test", "artifact_digest": "sha256:" + "0" * 64}


def _module():
    spec = importlib.util.spec_from_file_location("build_metals_vehicle_ranking_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(name):
    return json.loads((PRESENTATION / name).read_text(encoding="utf-8-sig"))


def _templates():
    return tuple(_read(name) for name in NAMES)


def _committed_rehearsal_and_state():
    component = _read(NAMES[1])
    auth = _read(NAMES[2])
    rehearsal = {
        "status": "METALS_FOUR_FACTOR_RANKING_V1_REHEARSAL_PASS",
        "authority_id": component["ranking_authority_id"],
        "methodology_version": component["ranking_methodology_version"],
        "weights": component["weights"],
        "groups": [
            {"commodity_id": group["commodity_id"], "vehicles": [dict(row) for row in group["vehicles"]]}
            for group in component["groups"]
        ],
    }
    state = {
        item["commodity_id"]: {
            "recommendation": item["recommendation"],
            "tactical_state": item["tactical_state"],
            "adjusted_expected_return_12m": item["adjusted_expected_return_12m"],
        }
        for item in auth["commodities"]
    }
    return rehearsal, state


def _projection_root(tmp_path, outputs):
    root = tmp_path / "repo"
    (root / "config" / "presentation").mkdir(parents=True)
    (root / "config" / "metals").mkdir(parents=True)
    shutil.copy(ROOT / "config" / "metals" / "vehicles.json", root / "config" / "metals" / "vehicles.json")
    shutil.copy(PRESENTATION / "metals_vehicle_cost_evidence_snapshot_v1.json", root / "config" / "presentation")
    for name, document in zip(NAMES, outputs):
        (root / "config" / "presentation" / name).write_text(json.dumps(document), encoding="utf-8")
    return root


def test_rebuilding_committed_evidence_reproduces_it_and_the_projection_accepts_it(tmp_path):
    module = _module()
    rehearsal, state = _committed_rehearsal_and_state()
    outputs = module.build(rehearsal, state, _templates(), SOURCE)
    committed = {item["commodity_id"]: item for item in _read(NAMES[2])["commodities"]}
    for item in outputs[2]["commodities"]:
        before = committed[item["commodity_id"]]
        assert item["certified_vehicle_order"] == before["certified_vehicle_order"]
        assert item["authorized_preferred_vehicle"] == before["authorized_preferred_vehicle"]
        assert item["authorized_label"] == before["authorized_label"]
    records = build_metals_vehicle_implementation_records(_projection_root(tmp_path, outputs))
    assert len(records) == sum(len(item["certified_vehicle_order"]) for item in outputs[2]["commodities"])


def test_non_supportive_tactical_states_get_no_preferred_label_and_still_project(tmp_path):
    module = _module()
    rehearsal, state = _committed_rehearsal_and_state()
    for item in state.values():
        item["tactical_state"] = "TACTICAL_POSITIVE_BUT_MIXED"
    outputs = module.build(rehearsal, state, _templates(), SOURCE)
    assert all(item["authorized_label"] != module.PREFERRED_LABEL for item in outputs[2]["commodities"])
    assert build_metals_vehicle_implementation_records(_projection_root(tmp_path, outputs))


def test_missing_commodity_state_fails_closed():
    module = _module()
    rehearsal, state = _committed_rehearsal_and_state()
    state.pop(next(iter(state)))
    with pytest.raises(ValueError, match="no current recommendation"):
        module.build(rehearsal, state, _templates(), SOURCE)


def test_leader_below_the_liquidity_floor_is_not_preferred():
    module = _module()
    rehearsal, state = _committed_rehearsal_and_state()
    gold = next(group for group in rehearsal["groups"] if group["commodity_id"].endswith("gold"))
    gold["vehicles"][0]["liquidity_floor_passed"] = False
    state[gold["commodity_id"]].update(recommendation="STRONG_BUY", tactical_state="TACTICAL_SUPPORTIVE")
    _, _, auth = module.build(rehearsal, state, _templates(), SOURCE)
    item = next(entry for entry in auth["commodities"] if entry["commodity_id"] == gold["commodity_id"])
    assert item["authorized_preferred_vehicle"] is None
    assert item["presentation_state"] == "RANKING_INFORMATIONAL_ONLY_LEADER_BELOW_LIQUIDITY_FLOOR"
