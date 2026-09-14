from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rehearse_metals_vehicle_adv_v1.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-vehicle-adv-v1-rehearsal.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("metals_vehicle_adv_v1_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_adv_revision_policy_selects_latest_governed_revision():
    module = _load_module()
    rows = [
        {
            "ticker": "GLD",
            "asset_id": "metals:vehicle:GLD",
            "observation_date": "2026-07-23",
            "close_usd": "100",
            "volume": "10",
            "source_authority": module.SOURCE_AUTHORITY,
            "source_run_id": "run-old",
            "collected_at_utc": "2026-07-23T12:00:00+00:00",
        },
        {
            "ticker": "GLD",
            "asset_id": "metals:vehicle:GLD",
            "observation_date": "2026-07-23",
            "close_usd": "101",
            "volume": "11",
            "source_authority": module.SOURCE_AUTHORITY,
            "source_run_id": "run-new",
            "collected_at_utc": "2026-08-24T12:00:00+00:00",
        },
    ]
    selected = module._select_latest_revision(rows)
    assert selected["source_run_id"] == "run-new"
    assert selected["close_usd"] == "101"


def test_adv_calculation_uses_latest_30_distinct_sessions(tmp_path: Path):
    module = _load_module()
    rows = []
    for day in range(1, 32):
        rows.append(
            {
                "ticker": "GLD",
                "asset_id": "metals:vehicle:GLD",
                "observation_date": f"2026-08-{day:02d}",
                "close_usd": str(100 + day),
                "volume": "1000",
                "source_authority": module.SOURCE_AUTHORITY,
                "source_run_id": "run-1",
                "collected_at_utc": f"2026-08-{day:02d}T20:00:00+00:00",
            }
        )
    result = module._calculate_adv(rows, "GLD")
    assert result["window_sessions"] == 30
    assert result["window_start_date"] == "2026-08-02"
    assert result["window_end_date"] == "2026-08-31"
    expected = sum((100 + day) * 1000 for day in range(2, 32)) / 30
    assert result["average_dollar_volume_usd"] == expected


def test_adv_script_is_read_only_and_fail_closed_for_spread():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"quoted_spread_evidence_complete": False' in text
    assert '"preferred_vehicle_ranking_ready": False' in text
    assert '"network_collection_performed": False' in text
    assert '"publication_write_performed": False' in text
    assert '"ranking_created": False' in text
    assert "high_low" not in text
    assert "bid" not in text.lower()
    assert "ask" not in text.lower()


def test_workflow_is_manual_only_and_pins_certified_metals_run():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "run-id: 34849676771" in text
    assert "metals-production-34849676771" in text
    assert "rehearse_metals_vehicle_adv_v1.py" in text
    assert "METALS_VEHICLE_ADV_V1_REHEARSAL=PASS" in text
