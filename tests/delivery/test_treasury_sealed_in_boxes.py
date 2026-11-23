"""Sealed MTG manual holdings (Nov 2026) appear in the Treasury's MTG chests, not as stock tiles."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REALM = ROOT / "foundation/production/dashboard_assets/rpg_realm.js"
HARNESS = ROOT / "tests/js/treasury_sealed_harness.js"


@pytest.fixture(scope="module")
def tiles():
    if not shutil.which("node"):
        pytest.skip("node is not installed")
    out = subprocess.run(["node", str(HARNESS), str(REALM)], capture_output=True, text=True, check=True, timeout=30)
    return {t["symbol"]: t for t in json.loads(out.stdout)}


def test_play_booster_display_joins_the_boxes_chest(tiles):
    boxes = tiles["BOXES"]
    assert boxes["count"] == "7" and boxes["paid"] == 1100 and boxes["worth"] == 1120
    assert set(boxes["members"]) == {"Test Set Collector Booster Display", "Test Set - Play Booster Display"}
    assert "TCGplayer market price" in boxes["ledger"]


def test_other_sealed_goes_to_other_and_nothing_becomes_a_stock_tile(tiles):
    assert tiles["OTHER"]["members"] == ["Test Starter Kit"]
    assert "111" not in tiles and "222" not in tiles
    assert tiles["VTEST"]["kind"] == "charter"          # ETFs still show as their own tiles
    assert tiles["LAIRS"]["members"] == ["Test Lair"]
