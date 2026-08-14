from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "docs"
    / "project_control"
    / "generated"
    / "d1_common_domain_registry"
    / "d1_common_domain_registry_certification.json"
)


def load_evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_d1_certification_status_and_transition() -> None:
    evidence = load_evidence()

    assert evidence["certification_status"] == (
        "UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_CERTIFICATION_PASS"
    )
    assert evidence["next_authorized_milestone"] == (
        "UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS"
    )


def test_d1_certified_domain_registry_boundary() -> None:
    registry = load_evidence()["domain_registry"]

    assert registry["certified_domains"] == ["crypto", "metals", "mtg"]
    assert registry["certified_domain_count"] == 3
    assert registry["fresh_database_initializes_registry"] is True
    assert registry["python_interface_read_only"] is True
    assert registry["unknown_domain_fails_closed"] is True
    assert registry["permanent_asset_population_counts_stored"] is False


def test_d1_certified_lineage_preserves_native_semantics() -> None:
    evidence = load_evidence()
    lineage = evidence["lineage_interface"]
    semantic = evidence["semantic_certification"]

    assert lineage["mtg_native_authority_included"] is True
    assert lineage["mtg_native_semantics_flattened"] is False
    assert lineage["native_domain_semantics_preserved"] is True
    assert semantic["single_static_domain_authority"] is True
    assert semantic["native_models_changed"] is False
    assert semantic["native_ranking_semantics_redefined"] is False
    assert semantic["native_recommendation_semantics_redefined"] is False
    assert semantic["missing_values_synthesized"] is False
    assert semantic["cross_asset_ranking_created"] is False
    assert semantic["allocation_policy_created"] is False
    assert semantic["automatic_purchase_execution_created"] is False


def test_d1_certified_schema_and_runtime_boundary() -> None:
    evidence = load_evidence()
    schema = evidence["schema_control"]
    runtime = evidence["runtime_boundary"]

    assert schema["canonical_migration_count"] == 6
    assert schema["canonical_database_object_count"] == 31
    assert schema["d1_schema_object_count"] == 4
    assert schema["schema_control_generation_pass"] is True
    assert schema["schema_control_validate_only_pass"] is True
    assert runtime["production_uip_database_modified"] is False
    assert runtime["native_domain_databases_modified"] is False
    assert runtime["native_model_execution_performed"] is False
    assert runtime["native_data_collection_performed"] is False
