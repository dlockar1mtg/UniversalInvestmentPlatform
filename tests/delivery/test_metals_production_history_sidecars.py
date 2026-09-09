from pathlib import Path


WORKFLOW = Path(".github/workflows/metals-production-cycle.yml")


def test_metals_production_cycle_builds_and_uploads_native_history_sidecars() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Build UIP-native rich history sidecars" in text
    assert "scripts/build_metals_native_history_sidecars.py" in text
    assert "--output-root data/operations/metals/native_rich_history" in text
    assert "data/operations/metals/native_rich_history/" in text


def test_metals_production_cycle_does_not_activate_presentation_publication() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "activate_presentation" not in text
    assert "production-publication-cycle" not in text
