from __future__ import annotations

from pathlib import Path

import pytest

from foundation.orchestration.refresh_contracts import (
    ALLOWED_R3_FINDINGS,
    RefreshContractError,
    get_domain_refresh_contract,
    load_refresh_contracts,
)


ROOT = Path(__file__).resolve().parents[1]


def test_r1_contracts_cover_exactly_certified_domains():
    contracts = load_refresh_contracts(ROOT)
    assert [contract.domain_id for contract in contracts.domains] == [
        "crypto",
        "metals",
        "mtg",
    ]
    assert contracts.milestone == "UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS"
    assert len(contracts.required_cycle_evidence) == 19


def test_r1_external_domains_use_source_owned_workflows():
    mtg = get_domain_refresh_contract(ROOT, "mtg")
    crypto = get_domain_refresh_contract(ROOT, "crypto")

    assert mtg.producer_repository == "dlockar1mtg/mtg-investment-terminal"
    assert mtg.producer_trigger["type"] == "github_workflow_dispatch"
    assert mtg.producer_trigger["workflow"] == ".github/workflows/mtg-marketplace-production.yml"
    assert mtg.producer_trigger["inputs"]["live_execution"] is True
    assert mtg.consumer_binding_state == "R2_COMPATIBILITY_PROOF_REQUIRED"

    assert crypto.producer_repository == "dlockar1mtg/CryptoIntelligencePlatform"
    assert crypto.producer_trigger["type"] == "github_workflow_dispatch"
    assert crypto.producer_trigger["workflow"] == ".github/workflows/crypto-production-cycle.yml"
    assert crypto.producer_trigger["inputs"]["full_refresh"] is True


def test_r1_metals_remains_uip_native_and_source_semantics_authoritative():
    contracts = load_refresh_contracts(ROOT)
    metals = get_domain_refresh_contract(ROOT, "metals")

    assert metals.ownership_type == "uip_native_domain"
    assert metals.producer_trigger == {
        "type": "uip_native_entrypoint",
        "entrypoint": "scripts/run_metals_production_cycle.py",
    }
    assert all(contract.native_semantics_authoritative for contract in contracts.domains)


def test_r1_unknown_domain_fails_closed():
    with pytest.raises(RefreshContractError):
        get_domain_refresh_contract(ROOT, "stocks")


def test_r1_preserves_r2_then_r3_sequence_without_decision_authority():
    contracts = load_refresh_contracts(ROOT)

    assert contracts.r2_milestone == "UIP_R2_REFRESHED_DATA_REHEARSAL"
    assert contracts.r3_milestone == "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW"
    assert contracts.r3_findings == ALLOWED_R3_FINDINGS
    assert contracts.r3_dimensions == (
        "freshness_and_completeness",
        "native_self_consistency",
        "distribution_and_outliers",
        "change_from_prior_plausibility",
        "uip_semantic_preservation",
        "decision_readiness",
        "investigation_routing",
    )
