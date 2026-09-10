import json
from pathlib import Path


CONTRACT = Path("config/presentation/metals_platform_health_v1.json")
WORKFLOW = Path(".github/workflows/metals-native-platform-health-v1-rehearsal.yml")
BUILDER = Path("scripts/build_metals_native_platform_health_sidecar.py")


def test_platform_health_v1_contract_is_explicitly_nonlegacy() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["authority_id"] == "UIP_NATIVE_METALS_PLATFORM_HEALTH_V1"
    assert contract["legacy_equivalent"] is False
    assert contract["required_output_fields"] == [
        "decision_run_id",
        "data_freshness_score",
        "model_confidence_score",
        "recommendation_quality_score",
        "pipeline_completeness_score",
        "overall_platform_health",
        "platform_grade",
        "explanation",
    ]
    assert abs(sum(contract["component_weights"].values()) - 1.0) < 1e-9


def test_platform_health_v1_rehearsal_uses_certified_metals_artifact_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Metals Production Cycle" in text
    assert "native_freshness_v1/metals_data_freshness.csv" in text
    assert "native_cycle/latest.json" in text
    assert "native_rich_history/manifest.json" in text
    assert "build_metals_native_platform_health_sidecar.py" in text
    assert "publication_staged" in text
    assert "publication_activated" in text


def test_platform_health_builder_does_not_publish() -> None:
    text = BUILDER.read_text(encoding="utf-8")
    assert '"publication_staged": False' in text
    assert '"publication_activated": False' in text
    assert '"postgres_write_performed": False' in text
    assert '"source_collection_performed": False' in text
    assert "activate_presentation" not in text
