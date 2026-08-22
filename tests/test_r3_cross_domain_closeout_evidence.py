from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "docs"
    / "project_control"
    / "generated"
    / "r3_cross_domain_closeout"
    / "r3_cross_domain_closeout_certification.json"
)


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_r3_cross_domain_closeout_status_and_sequence() -> None:
    evidence = _evidence()

    assert evidence["status"] == (
        "UIP_R3_CROSS_DOMAIN_RECONCILIATION_AND_CLOSEOUT_PASS"
    )
    assert evidence["disposition"] == "UIP_R3_CERTIFIED_COMPLETE"
    assert evidence["next_gate"] == "UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY"
    assert evidence["final_certification"]["status"] == (
        "R3_AUTHORITATIVE_PLATFORM_REGISTRY_RECONCILIATION_GATE_PASS"
    )
    assert evidence["final_certification"]["failure_count"] == 0
    assert evidence["final_certification"]["unresolved_warning_count"] == 0


def test_r3_cross_domain_closeout_has_canonical_healthy_registry() -> None:
    evidence = _evidence()

    assert evidence["domain_health"] == {
        "crypto": "HEALTHY",
        "metals": "HEALTHY",
        "mtg": "HEALTHY",
    }
    registry = evidence["canonical_registry"]
    assert registry["platform_ids"] == ["crypto", "metals", "mtg"]
    assert registry["latest_successful_import_rows_per_domain"] == 1
    assert registry["latest_import_attempt_rows_per_domain"] == 1
    assert registry["all_operational_domains_active"] is True
    assert registry["all_latest_imports_imported"] is True
    assert registry["all_import_health_healthy"] is True
    assert registry["operational_status_complete"] is True


def test_r3_cross_domain_closeout_preserves_domain_authority() -> None:
    evidence = _evidence()
    current = evidence["generic_current_authority"]

    assert current["asset_master_current"] == {
        "crypto": 6,
        "metals": 16,
        "mtg": 0,
    }
    assert current["forecasts_current"] == {
        "crypto": 120,
        "metals": 16,
        "mtg": 0,
    }
    assert current["recommendations_current"] == {
        "crypto": 6,
        "metals": 12,
        "mtg": 0,
    }
    assert current["risk_metrics_current"] == {
        "crypto": 6,
        "metals": 11,
        "mtg": 0,
    }

    mtg = evidence["mtg_native_authority"]
    assert mtg["current_rows"] == 968
    assert mtg["history_rows"] == 968
    assert mtg["canonical_platform_id"] == "mtg"
    assert mtg["generic_current_authority_rows"] == 0


def test_r3_cross_domain_closeout_preserves_lineage_and_history() -> None:
    evidence = _evidence()
    lineage = evidence["mtg_lineage_reconciliation"]

    assert lineage["legacy_uppercase_platform_rows"] == 19679
    assert lineage["legacy_uppercase_rows_mapped_to_domain_mtg"] == 19679
    assert lineage["native_lowercase_platform_rows"] == 969
    assert lineage["native_lowercase_rows_mapped_to_domain_mtg"] == 969
    assert lineage["unmapped_rows"] == 0
    assert lineage["historical_case_variants_preserved"] is True
    assert lineage["canonical_domain_mapping_case_insensitive"] is True

    history = evidence["history_preservation"]
    assert history["migration_010_changed_history"] is False
    assert history["mtg_native_authority_history_rows"] == 968


def test_r3_cross_domain_closeout_keeps_global_decision_authority_closed() -> None:
    controls = _evidence()["cross_domain_boundaries"]

    assert controls["non_mtg_analytical_authority_changed"] is False
    assert controls["native_domain_semantics_reinterpreted"] is False
    assert controls["missing_values_synthesized"] is False
    assert controls["universal_cross_domain_rank_created"] is False
    assert controls["cross_domain_allocation_policy_created"] is False
    assert controls["automatic_execution_authorized"] is False
    assert controls["mtg_execution_ready_purchase_authority"] is False
