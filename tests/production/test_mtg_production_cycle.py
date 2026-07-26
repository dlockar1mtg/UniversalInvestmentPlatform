from pathlib import Path

from foundation.production.mtg.cycle import MTGProductionCycle
from foundation.production.mtg.readiness import evaluate_mtg_readiness


def test_readiness_fails_closed_without_live_gate(tmp_path: Path) -> None:
    source = tmp_path / "mtg-source"
    source.mkdir()
    config = tmp_path / "production.json"
    config.write_text("{}", encoding="utf-8")

    report = evaluate_mtg_readiness(source, config, {})

    assert report.status == "SAFE_HOLD"
    assert report.live_execution_enabled is False
    assert "MTG_LIVE_EXECUTION_DISABLED" in report.reason_codes


def test_cycle_publishes_safe_hold_evidence(tmp_path: Path) -> None:
    source = tmp_path / "mtg-source"
    source.mkdir()
    config = tmp_path / "production.json"
    config.write_text("{}", encoding="utf-8")
    output = tmp_path / "output"

    report = MTGProductionCycle(source, config, output).run("test-run", {})

    assert report.status == "SAFE_HOLD"
    assert report.mode == "NON_LIVE"
    assert (output / "latest.json").is_file()


def test_live_gate_does_not_execute_unimplemented_pipeline(tmp_path: Path) -> None:
    source = tmp_path / "mtg-source"
    source.mkdir()
    config = tmp_path / "production.json"
    config.write_text("{}", encoding="utf-8")

    report = MTGProductionCycle(source, config, tmp_path / "output").run(
        "test-live-gate",
        {"UIP_MTG_LIVE_EXECUTION": "true"},
    )

    assert report.status == "NOT_IMPLEMENTED"
    assert "LIVE_EXECUTION_PIPELINE_NOT_YET_IMPLEMENTED" in report.reason_codes
