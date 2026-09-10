from pathlib import Path


WORKFLOW = Path(".github/workflows/metals-native-freshness-v1-rehearsal.yml")
CONTRACT = Path("config/presentation/metals_data_freshness_v1.json")


def test_rehearsal_builds_native_freshness_without_publication_activation() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/build_metals_native_freshness_sidecar.py" in text
    assert "metals_data_freshness_v1.json" in text
    assert "metals-native-freshness-v1-${{ github.run_id }}" in text
    forbidden = (
        "activate_presentation",
        "stage_presentation",
        "restore-rich-presentation",
        "production-publication-cycle",
    )
    assert not any(token in text for token in forbidden)


def test_contract_is_explicitly_new_native_authority() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert '"authority_id": "UIP_NATIVE_METALS_DATA_FRESHNESS_V1"' in text
    assert '"legacy_equivalent": false' in text
    assert '"frequency": "DAILY"' in text
    assert '"stale_after_days": 5' in text
