"""Validate Metals runtime independence and GitHub-hosted migration readiness."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

_ALLOWED_STATES = {"IMPLEMENTED", "PLANNED", "BLOCKED", "RETIRED"}
_COMPLETE_STATES = {"IMPLEMENTED", "RETIRED"}


@dataclass(frozen=True)
class MigrationCapability:
    capability_id: str
    required: bool
    legacy_source: str
    uip_target: str
    migration_state: str
    github_hosted_compatible: bool


@dataclass(frozen=True)
class MigrationReport:
    status: str
    capability_count: int
    implemented_count: int
    planned_count: int
    blocked_count: int
    missing_target_count: int
    external_dependency_count: int
    reason_codes: tuple[str, ...]
    capabilities: tuple[MigrationCapability, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        payload["capabilities"] = [asdict(item) for item in self.capabilities]
        return payload


def load_contract(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate_contract(contract: dict[str, object], repository_root: Path) -> MigrationReport:
    reasons: list[str] = []
    raw_capabilities = contract.get("capabilities")
    if not isinstance(raw_capabilities, list) or not raw_capabilities:
        raw_capabilities = []
        reasons.append("MISSING_CAPABILITIES")

    capabilities: list[MigrationCapability] = []
    identifiers: set[str] = set()
    missing_targets = 0
    external_dependencies = 0

    for raw in raw_capabilities:
        capability = MigrationCapability(
            capability_id=str(raw.get("capability_id", "")).strip(),
            required=bool(raw.get("required", False)),
            legacy_source=str(raw.get("legacy_source", "")).strip(),
            uip_target=str(raw.get("uip_target", "")).strip(),
            migration_state=str(raw.get("migration_state", "")).strip().upper(),
            github_hosted_compatible=bool(raw.get("github_hosted_compatible", False)),
        )
        capabilities.append(capability)
        if not capability.capability_id:
            reasons.append("MISSING_CAPABILITY_ID")
        elif capability.capability_id in identifiers:
            reasons.append("DUPLICATE_CAPABILITY_ID")
        identifiers.add(capability.capability_id)
        if capability.migration_state not in _ALLOWED_STATES:
            reasons.append("INVALID_MIGRATION_STATE")
        if capability.required and not capability.uip_target:
            reasons.append("MISSING_UIP_TARGET")
        if capability.required and not capability.github_hosted_compatible:
            reasons.append("NOT_GITHUB_HOSTED_COMPATIBLE")
        if capability.migration_state in _COMPLETE_STATES and capability.uip_target:
            if not (repository_root / capability.uip_target).exists():
                missing_targets += 1
        if capability.migration_state in _COMPLETE_STATES and (
            "C:/Users/" in capability.uip_target or "C:\\Users\\" in capability.uip_target
        ):
            external_dependencies += 1

    if missing_targets:
        reasons.append("IMPLEMENTED_TARGET_MISSING")
    if external_dependencies:
        reasons.append("EXTERNAL_RUNTIME_DEPENDENCY")

    implemented = sum(item.migration_state in _COMPLETE_STATES for item in capabilities)
    planned = sum(item.migration_state == "PLANNED" for item in capabilities)
    blocked = sum(item.migration_state == "BLOCKED" for item in capabilities)
    required_incomplete = any(
        item.required and item.migration_state not in _COMPLETE_STATES for item in capabilities
    )

    if blocked or any(code in reasons for code in ("INVALID_MIGRATION_STATE", "IMPLEMENTED_TARGET_MISSING", "EXTERNAL_RUNTIME_DEPENDENCY")):
        status = "FAILED"
    elif reasons or required_incomplete:
        status = "INCOMPLETE"
        if required_incomplete:
            reasons.append("REQUIRED_CAPABILITIES_INCOMPLETE")
    else:
        status = "PASS"
        reasons.append("RUNTIME_MIGRATION_COMPLETE")

    return MigrationReport(
        status=status,
        capability_count=len(capabilities),
        implemented_count=implemented,
        planned_count=planned,
        blocked_count=blocked,
        missing_target_count=missing_targets,
        external_dependency_count=external_dependencies,
        reason_codes=tuple(dict.fromkeys(reasons)),
        capabilities=tuple(capabilities),
    )


def publish_report(report: MigrationReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return output_path
