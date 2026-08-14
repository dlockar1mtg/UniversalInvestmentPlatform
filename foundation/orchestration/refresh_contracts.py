"""Governed R1 domain refresh and orchestration contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("config/orchestration/r1_domain_refresh_contracts.json")
EXPECTED_DOMAINS = ("crypto", "metals", "mtg")
ALLOWED_R3_FINDINGS = (
    "PASS",
    "PASS_WITH_GOVERNED_GAPS",
    "REVIEW",
    "DOMAIN_INVESTIGATION_REQUIRED",
)


class RefreshContractError(RuntimeError):
    """Raised when the governed R1 refresh contract is invalid."""


@dataclass(frozen=True)
class DomainRefreshContract:
    domain_id: str
    ownership_type: str
    producer_repository: str
    producer_ref: str
    producer_trigger: dict[str, Any]
    producer_execution_owner: str
    uip_consumer_boundary: str
    consumer_binding_state: str
    native_semantics_authoritative: bool
    known_governed_requirements: tuple[str, ...]


@dataclass(frozen=True)
class RefreshContractSet:
    contract_version: str
    milestone: str
    required_cycle_evidence: tuple[str, ...]
    domains: tuple[DomainRefreshContract, ...]
    r2_milestone: str
    r3_milestone: str
    r3_findings: tuple[str, ...]
    r3_dimensions: tuple[str, ...]


def _require_bool(mapping: dict[str, Any], key: str, expected: bool) -> None:
    if mapping.get(key) is not expected:
        raise RefreshContractError(f"Expected {key}={expected}.")


def load_refresh_contracts(repository_root: Path) -> RefreshContractSet:
    """Load and fail-closed validate the governed R1 contract."""

    path = repository_root.resolve() / CONTRACT_PATH
    if not path.is_file():
        raise RefreshContractError(f"R1 contract not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract_version") != "1.0.0":
        raise RefreshContractError("Unsupported R1 contract version.")
    if payload.get("milestone") != "UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS":
        raise RefreshContractError("Unexpected R1 milestone.")

    global_controls = payload.get("global_controls")
    if not isinstance(global_controls, dict):
        raise RefreshContractError("global_controls is missing or invalid.")

    _require_bool(global_controls, "uip_may_trigger_source_owned_workflows", True)
    _require_bool(global_controls, "uip_may_invoke_external_collectors_directly", False)
    _require_bool(global_controls, "source_domain_owns_native_model_execution", True)
    _require_bool(global_controls, "failed_cycle_preserves_previous_certified_state", True)
    _require_bool(global_controls, "partial_activation_authorized", False)
    _require_bool(global_controls, "missing_authority_may_be_synthesized", False)
    _require_bool(global_controls, "permanent_asset_population_counts_allowed", False)
    _require_bool(global_controls, "cross_asset_ranking_authorized", False)
    _require_bool(global_controls, "allocation_policy_authorized", False)
    _require_bool(global_controls, "automatic_execution_authorized", False)

    evidence = global_controls.get("required_cycle_evidence")
    if not isinstance(evidence, list) or not evidence or len(evidence) != len(set(evidence)):
        raise RefreshContractError("required_cycle_evidence must be unique and non-empty.")

    raw_domains = payload.get("domains")
    if not isinstance(raw_domains, dict) or tuple(sorted(raw_domains)) != EXPECTED_DOMAINS:
        raise RefreshContractError("R1 must define exactly crypto, metals, and mtg.")

    domains: list[DomainRefreshContract] = []
    for domain_id in EXPECTED_DOMAINS:
        raw = raw_domains[domain_id]
        if not isinstance(raw, dict):
            raise RefreshContractError(f"Invalid domain contract: {domain_id}")
        if raw.get("native_semantics_authoritative") is not True:
            raise RefreshContractError(f"Native semantics are not authoritative for {domain_id}.")
        requirements = raw.get("known_governed_requirements")
        if not isinstance(requirements, list) or not requirements:
            raise RefreshContractError(f"Governed requirements missing for {domain_id}.")
        trigger = raw.get("producer_trigger")
        if not isinstance(trigger, dict) or not trigger.get("type"):
            raise RefreshContractError(f"Producer trigger missing for {domain_id}.")
        if domain_id in {"mtg", "crypto"}:
            if raw.get("direct_uip_collector_invocation_authorized") is not False:
                raise RefreshContractError(
                    f"UIP direct collector invocation must remain false for {domain_id}."
                )
            if trigger.get("type") != "github_workflow_dispatch":
                raise RefreshContractError(
                    f"External domain {domain_id} must use a source-owned workflow trigger."
                )
        domains.append(
            DomainRefreshContract(
                domain_id=domain_id,
                ownership_type=str(raw["ownership_type"]),
                producer_repository=str(raw["producer_repository"]),
                producer_ref=str(raw["producer_ref"]),
                producer_trigger=dict(trigger),
                producer_execution_owner=str(raw["producer_execution_owner"]),
                uip_consumer_boundary=str(raw["uip_consumer_boundary"]),
                consumer_binding_state=str(raw["consumer_binding_state"]),
                native_semantics_authoritative=True,
                known_governed_requirements=tuple(str(value) for value in requirements),
            )
        )

    r2 = payload.get("r2_gate")
    r3 = payload.get("r3_gate")
    if not isinstance(r2, dict) or not isinstance(r3, dict):
        raise RefreshContractError("R2/R3 gates are missing.")
    if r2.get("milestone") != "UIP_R2_REFRESHED_DATA_REHEARSAL":
        raise RefreshContractError("Unexpected R2 milestone.")
    if r3.get("milestone") != "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW":
        raise RefreshContractError("Unexpected R3 milestone.")
    if tuple(r3.get("allowed_findings") or ()) != ALLOWED_R3_FINDINGS:
        raise RefreshContractError("Unexpected R3 findings vocabulary.")
    _require_bool(r3, "cross_asset_ranking_authorized", False)
    _require_bool(r3, "allocation_policy_authorized", False)
    _require_bool(r3, "hard_gate_before_e1_or_dashboard_decision_logic", True)

    dimensions = r3.get("required_review_dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != 7:
        raise RefreshContractError("R3 must define seven review dimensions.")

    return RefreshContractSet(
        contract_version="1.0.0",
        milestone=str(payload["milestone"]),
        required_cycle_evidence=tuple(str(value) for value in evidence),
        domains=tuple(domains),
        r2_milestone=str(r2["milestone"]),
        r3_milestone=str(r3["milestone"]),
        r3_findings=tuple(str(value) for value in r3["allowed_findings"]),
        r3_dimensions=tuple(str(value) for value in dimensions),
    )


def get_domain_refresh_contract(
    repository_root: Path,
    domain_id: str,
) -> DomainRefreshContract:
    """Return one governed domain refresh contract or fail closed."""

    normalized = domain_id.strip().lower()
    matches = [
        contract
        for contract in load_refresh_contracts(repository_root).domains
        if contract.domain_id == normalized
    ]
    if len(matches) != 1:
        raise RefreshContractError(f"Unknown governed refresh domain: {domain_id}")
    return matches[0]
