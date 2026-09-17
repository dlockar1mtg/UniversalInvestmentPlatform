from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts" / "build_metals_commodity_technical_context_sidecar.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-commodity-technical-context-v1-rehearsal.yml"


def _load_builder():
    spec = importlib.util.spec_from_file_location("metals_commodity_technical_context_v1", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_exact_month_returns_and_drawdown_are_computed_without_imputation(tmp_path: Path) -> None:
    module = _load_builder()
    path = tmp_path / "history.csv"
    fieldnames = ["asset_id", "observation_date", "value", "source", "unit", "series_id"]
    rows = []
    for asset in module.SUPPORTED:
        for observed, value in (
            ("2026-01-01", 80),
            ("2026-02-01", 90),
            ("2026-03-01", 95),
            ("2026-04-01", 100),
            ("2026-05-01", 110),
            ("2026-06-01", 120),
            ("2026-07-01", 100),
        ):
            rows.append({"asset_id": asset, "observation_date": observed, "value": value, "source": "world_bank", "unit": "usd", "series_id": f"WORLD_BANK::{asset.upper()}_MONTHLY"})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    output = module.build_rows(path)
    assert len(output) == 8
    gold = next(row for row in output if row["asset_id"] == "gold")
    assert abs(gold["return_1m"] - (100 / 120 - 1)) < 1e-12
    assert abs(gold["return_3m"] - 0.0) < 1e-12
    assert abs(gold["return_6m"] - 0.25) < 1e-12
    assert abs(gold["current_drawdown"] - (100 / 120 - 1)) < 1e-12
    assert gold["ma50_supported"] is False
    assert gold["ma200_supported"] is False


def test_missing_exact_prior_month_fails_closed(tmp_path: Path) -> None:
    module = _load_builder()
    path = tmp_path / "history.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset_id", "observation_date", "value"])
        writer.writeheader()
        for asset in module.SUPPORTED:
            for observed, value in (("2026-01-01", 80), ("2026-04-01", 100), ("2026-06-01", 120), ("2026-07-01", 100)):
                writer.writerow({"asset_id": asset, "observation_date": observed, "value": value})
    try:
        module.build_rows(path)
    except RuntimeError as exc:
        assert "missing exact prior calendar month" in str(exc)
    else:
        raise AssertionError("missing exact month did not fail closed")


def test_rehearsal_is_manual_read_only_and_keeps_publication_closed() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "collect_metals_benchmark_history.py" in text
    assert "build_metals_commodity_technical_context_sidecar.py" in text
    assert "publication_staged" in text
    assert "publication_activated" in text
    assert "postgres_write" in text
    assert "production-publication-cycle" not in text
