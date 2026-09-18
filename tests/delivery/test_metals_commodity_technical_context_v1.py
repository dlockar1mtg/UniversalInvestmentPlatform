from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts" / "build_metals_commodity_technical_context_sidecar.py"
COLLECTOR = ROOT / "scripts" / "collect_metals_benchmark_history.py"
CONTRACT = ROOT / "config" / "presentation" / "metals_commodity_technical_context_v1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-commodity-technical-context-v1-rehearsal.yml"


def _load_builder():
    spec = importlib.util.spec_from_file_location("metals_commodity_technical_context_v1", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _write_history(path: Path, module) -> None:
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
            rows.append({
                "asset_id": asset,
                "observation_date": observed,
                "value": value,
                "source": "world_bank",
                "unit": "usd",
                "series_id": f"WORLD_BANK::{asset.upper()}_MONTHLY",
            })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_exact_month_returns_drawdown_and_authority_fields(tmp_path: Path) -> None:
    module = _load_builder()
    path = tmp_path / "history.csv"
    _write_history(path, module)

    output = module.build_rows(path, CONTRACT)
    assert len(output) == 8
    gold = next(row for row in output if row["asset_id"] == "gold")
    assert abs(gold["return_1m"] - (100 / 120 - 1)) < 1e-12
    assert abs(gold["return_3m"] - 0.0) < 1e-12
    assert abs(gold["return_6m"] - 0.25) < 1e-12
    assert abs(gold["current_drawdown"] - (100 / 120 - 1)) < 1e-12
    assert gold["source_provider"] == "world_bank"
    assert gold["source_series_id"] == "WORLD_BANK::GOLD_MONTHLY"
    assert gold["observation_count"] == 7
    assert gold["historical_peak_value"] == 120
    assert gold["historical_peak_date"] == "2026-06-01"
    assert gold["methodology_version"] == "1.0.0"
    assert gold["presentation_semantics"] == "DESCRIPTIVE_COMMODITY_TECHNICAL_CONTEXT_NOT_RECOMMENDATION_NOT_EXECUTION"
    assert gold["ma50_supported"] is False
    assert gold["ma200_supported"] is False


def test_missing_exact_prior_month_fails_closed(tmp_path: Path) -> None:
    module = _load_builder()
    path = tmp_path / "history.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset_id", "observation_date", "value", "source", "series_id"])
        writer.writeheader()
        for asset in module.SUPPORTED:
            for observed, value in (("2026-01-01", 80), ("2026-04-01", 100), ("2026-05-01", 110), ("2026-07-01", 100)):
                writer.writerow({
                    "asset_id": asset,
                    "observation_date": observed,
                    "value": value,
                    "source": "world_bank",
                    "series_id": f"WORLD_BANK::{asset.upper()}_MONTHLY",
                })
    try:
        module.build_rows(path, CONTRACT)
    except RuntimeError as exc:
        assert "missing exact prior calendar month" in str(exc)
        assert "2026-06-01" in str(exc)
    else:
        raise AssertionError("missing exact month did not fail closed")


def test_history_collector_does_not_import_eager_production_package() -> None:
    text = COLLECTOR.read_text(encoding="utf-8")
    assert "from foundation.production.providers import" not in text
    assert 'spec_from_file_location("uip_metals_provider_module"' in text
    assert 'ROOT / "foundation" / "production" / "providers.py"' in text
    assert "sys.modules[spec.name] = module" in text


def test_rehearsal_validates_authority_contract_and_keeps_publication_closed() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "collect_metals_benchmark_history.py" in text
    assert "build_metals_commodity_technical_context_sidecar.py" in text
    assert "--contract config/presentation/metals_commodity_technical_context_v1.json" in text
    assert 'required = set(contract["required_output_fields"])' in text
    assert 'manifest["source_history_row_count"] == 6400' in text
    assert 'manifest["postgres_write_performed"] is False' in text
    assert 'manifest["publication_staged"] is False' in text
    assert 'manifest["publication_activated"] is False' in text
    assert "production-publication-cycle" not in text
