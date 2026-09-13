from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_metals_native_recommendation_change_sidecar.py"
CONTRACT = ROOT / "config" / "presentation" / "metals_recommendation_change_v1.json"

spec = importlib.util.spec_from_file_location("metals_rec_change_v1", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def row(asset: str, date: str, value: float, collected: str, source: str, run_id: str = "r1") -> dict:
    return {
        "series_id": asset,
        "observation_date": date,
        "value": value,
        "source": source,
        "collected_at_utc": collected,
        "run_id": run_id,
    }


def test_contract_freezes_nonlegacy_commodity_only_semantics() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["authority_id"] == "UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1"
    assert contract["schema_version"] == "1.0.0"
    assert contract["methodology_version"] == "1.0.0"
    assert contract["legacy_equivalent"] is False
    assert contract["scope"] == "BENCHMARK_COMMODITY_ASSET_ONLY"
    assert contract["first_observation_behavior"] == "BASELINE_ONLY_NO_CHANGE_EVENT"
    assert contract["no_op_behavior"] == "OMIT_REPEATED_RECOMMENDATION"
    assert contract["latest_state_parity_required"] is True
    assert contract["same_date_multi_source_policy"]["method"] == "LATEST_COLLECTED_REVISION_WINS"
    assert "COMMODITY_TO_VEHICLE_RECOMMENDATION_PROJECTION" in contract["forbidden_semantics"]
    assert "LEGACY_RECOMMENDATION_CHANGE_COPY_FORWARD" in contract["forbidden_semantics"]


def test_latest_collected_revision_wins() -> None:
    rows = [
        row("GOLD", "2026-01-01", 100.0, "2026-01-02T00:00:00Z", "source-a"),
        row("GOLD", "2026-01-01", 105.0, "2026-01-03T00:00:00Z", "source-b"),
    ]
    canonical, stats = module.canonicalize(
        rows,
        id_field="series_id",
        value_field="value",
        rel_tol=1e-9,
        abs_tol=1e-8,
    )
    assert len(canonical) == 1
    assert canonical[0]["value"] == 105.0
    assert stats["raw_row_count"] == 2
    assert stats["canonical_row_count"] == 1
    assert stats["duplicate_source_rows_collapsed"] == 1
    assert stats["superseded_conflicting_revision_rows"] == 1


def test_equivalent_latest_timestamp_tie_is_deterministic() -> None:
    rows = [
        row("GOLD", "2026-01-01", 105.0, "2026-01-03T00:00:00Z", "source-z"),
        row("GOLD", "2026-01-01", 105.0, "2026-01-03T00:00:00Z", "source-a"),
    ]
    canonical, _ = module.canonicalize(
        rows,
        id_field="series_id",
        value_field="value",
        rel_tol=1e-9,
        abs_tol=1e-8,
    )
    assert canonical[0]["source"] == "source-a"


def test_conflicting_latest_timestamp_tie_fails_closed() -> None:
    rows = [
        row("GOLD", "2026-01-01", 105.0, "2026-01-03T00:00:00Z", "source-a"),
        row("GOLD", "2026-01-01", 106.0, "2026-01-03T00:00:00Z", "source-b"),
    ]
    with pytest.raises(RuntimeError, match="conflicting latest-timestamp source values"):
        module.canonicalize(
            rows,
            id_field="series_id",
            value_field="value",
            rel_tol=1e-9,
            abs_tol=1e-8,
        )


def test_missing_or_naive_collected_timestamp_fails_closed() -> None:
    missing = [row("GOLD", "2026-01-01", 105.0, "", "source-a")]
    with pytest.raises(RuntimeError, match="missing collected_at_utc"):
        module.canonicalize(missing, id_field="series_id", value_field="value", rel_tol=1e-9, abs_tol=1e-8)

    naive = [row("GOLD", "2026-01-01", 105.0, "2026-01-03T00:00:00", "source-a")]
    with pytest.raises(RuntimeError, match="timezone-aware"):
        module.canonicalize(naive, id_field="series_id", value_field="value", rel_tol=1e-9, abs_tol=1e-8)
