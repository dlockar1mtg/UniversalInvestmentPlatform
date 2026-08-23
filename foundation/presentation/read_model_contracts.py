"""Fail-closed DASH-READ-1 presentation/read-model contract validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

CONTRACT_PATH = Path("config/presentation/dash_read_1_contract.json")
EXPECTED_DOMAINS = ("crypto", "metals", "mtg")
EXPECTED_API_SURFACES = ("global_status", "recommendations", "asset_detail", "domain_health", "lineage")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PresentationContractError(RuntimeError):
    """Raised when DASH-READ-1 authority or configuration fails closed."""


@dataclass(frozen=True)
class SurfaceContract:
    source: str
    required_fields: tuple[str, ...]


@dataclass(frozen=True)
class DomainPresentationContract:
    domain_id: str
    platform_id: str
    authority_mode: str
    surfaces: Mapping[str, SurfaceContract]
    native_rank_available: bool
    current_price_contract: str
    generic_current_authority_must_be_zero: tuple[str, ...]


@dataclass(frozen=True)
class PresentationReadModelContract:
    contract_version: str
    milestone: str
    source_authority_classification: str
    required_publication_metadata: tuple[str, ...]
    common_surfaces: Mapping[str, SurfaceContract]
    domains: tuple[DomainPresentationContract, ...]
    render_read_api_surfaces: tuple[str, ...]
    application_state_not_part_of_dash_read_1: tuple[str, ...]


def _require_bool(mapping: Mapping[str, Any], key: str, expected: bool) -> None:
    if mapping.get(key) is not expected:
        raise PresentationContractError(f"Expected {key}={expected}.")


def _surface(raw: Mapping[str, Any], inherited: SurfaceContract | None = None) -> SurfaceContract:
    source = str(raw.get("source", "")).strip()
    if not _IDENTIFIER.fullmatch(source):
        raise PresentationContractError(f"Invalid source identifier: {source!r}")
    fields = raw.get("required_fields")
    if fields is None and inherited is not None:
        return SurfaceContract(source=source, required_fields=inherited.required_fields)
    if not isinstance(fields, list) or not fields or len(fields) != len(set(fields)):
        raise PresentationContractError(f"Surface {source} requires unique required_fields.")
    normalized = tuple(str(value) for value in fields)
    if any(not _IDENTIFIER.fullmatch(value) for value in normalized):
        raise PresentationContractError(f"Surface {source} contains an invalid field name.")
    return SurfaceContract(source=source, required_fields=normalized)


def load_presentation_contract(repository_root: Path) -> PresentationReadModelContract:
    """Load and fail-closed validate the governed DASH-READ-1 contract."""
    path = repository_root.resolve() / CONTRACT_PATH
    if not path.is_file():
        raise PresentationContractError(f"DASH-READ-1 contract not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract_version") != "1.0.0":
        raise PresentationContractError("Unsupported DASH-READ-1 contract version.")
    if payload.get("milestone") != "DASH_READ_1_CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT":
        raise PresentationContractError("Unexpected DASH-READ-1 milestone.")

    controls = payload.get("global_controls")
    if not isinstance(controls, dict):
        raise PresentationContractError("global_controls is missing or invalid.")
    for key, expected in (
        ("presentation_store_is_analytical_authority", False),
        ("current_authority_only", True),
        ("publication_must_be_atomic", True),
        ("failed_publication_preserves_previous_active_version", True),
        ("source_database_sha256_required", True),
        ("native_semantics_authoritative", True),
        ("missing_authority_may_be_synthesized", False),
        ("unsupported_forecasts_may_be_synthesized", False),
        ("unknown_cost_basis_may_be_zero_filled", False),
        ("cross_domain_rank_authorized", False),
        ("allocation_policy_authorized", False),
        ("automatic_execution_authorized", False),
        ("application_state_is_separate_from_analytical_authority", True),
        ("source_owned_refresh_execution_remains_source_owned", True),
    ):
        _require_bool(controls, key, expected)

    metadata = payload.get("required_publication_metadata")
    mandatory = {
        "publication_id", "publication_version", "source_database_sha256",
        "source_database_classification", "published_at_utc", "publication_status",
    }
    if not isinstance(metadata, list) or len(metadata) != len(set(metadata)) or set(metadata) != mandatory:
        raise PresentationContractError("Unexpected publication metadata contract.")

    raw_common = payload.get("common_surfaces")
    if not isinstance(raw_common, dict) or tuple(sorted(raw_common)) != ("domain_health", "lineage"):
        raise PresentationContractError("DASH-READ-1 common surfaces are incomplete.")
    common_surfaces = {name: _surface(raw_common[name]) for name in sorted(raw_common)}

    raw_domains = payload.get("domains")
    if not isinstance(raw_domains, dict) or tuple(sorted(raw_domains)) != EXPECTED_DOMAINS:
        raise PresentationContractError("DASH-READ-1 must define exactly crypto, metals, and mtg.")
    crypto_raw = raw_domains["crypto"]
    crypto_surfaces = {
        name: _surface(crypto_raw[name])
        for name in ("asset_surface", "recommendation_surface", "forecast_surface", "risk_surface")
    }

    domains: list[DomainPresentationContract] = []
    for domain_id in EXPECTED_DOMAINS:
        raw = raw_domains[domain_id]
        if not isinstance(raw, dict) or str(raw.get("platform_id", "")).lower() != domain_id:
            raise PresentationContractError(f"Invalid domain identity: {domain_id}.")
        authority_mode = str(raw.get("authority_mode", ""))
        if domain_id in {"crypto", "metals"}:
            if authority_mode != "GENERIC_CURRENT_VIEWS":
                raise PresentationContractError(f"Unexpected authority mode for {domain_id}.")
            surfaces: dict[str, SurfaceContract] = {}
            for name in ("asset_surface", "recommendation_surface", "forecast_surface", "risk_surface"):
                surfaces[name] = _surface(raw[name], crypto_surfaces[name] if domain_id == "metals" else None)
            if raw.get("native_rank_available") is not False:
                raise PresentationContractError(f"Native rank must remain unavailable for {domain_id}.")
            zero_surfaces: tuple[str, ...] = ()
        else:
            if authority_mode != "MTG_NATIVE_CURRENT_ONLY":
                raise PresentationContractError("MTG must remain native-current-only.")
            surfaces = {"native_surface": _surface(raw["native_surface"])}
            expected_zero = ("asset_master_current", "forecasts_current", "recommendations_current", "risk_metrics_current")
            zero_raw = raw.get("generic_current_authority_must_be_zero")
            if not isinstance(zero_raw, list) or tuple(zero_raw) != expected_zero:
                raise PresentationContractError("MTG generic-current suppression contract changed.")
            if raw.get("native_rank_available") is not True:
                raise PresentationContractError("MTG native-rank availability changed.")
            zero_surfaces = tuple(str(value) for value in zero_raw)
        domains.append(DomainPresentationContract(
            domain_id=domain_id,
            platform_id=domain_id,
            authority_mode=authority_mode,
            surfaces=surfaces,
            native_rank_available=bool(raw["native_rank_available"]),
            current_price_contract=str(raw["current_price_contract"]),
            generic_current_authority_must_be_zero=zero_surfaces,
        ))

    api = payload.get("render_read_api_surfaces")
    if tuple(api or ()) != EXPECTED_API_SURFACES:
        raise PresentationContractError("Unexpected Render read API surface set.")
    app_state = payload.get("application_state_not_part_of_dash_read_1")
    if not isinstance(app_state, list) or not app_state or len(app_state) != len(set(app_state)):
        raise PresentationContractError("Application-state exclusions are missing or invalid.")

    return PresentationReadModelContract(
        contract_version="1.0.0",
        milestone=str(payload["milestone"]),
        source_authority_classification=str(controls["source_authority_classification"]),
        required_publication_metadata=tuple(str(value) for value in metadata),
        common_surfaces=common_surfaces,
        domains=tuple(domains),
        render_read_api_surfaces=tuple(str(value) for value in api),
        application_state_not_part_of_dash_read_1=tuple(str(value) for value in app_state),
    )


def _columns(connection: Any, source: str) -> set[str]:
    rows = connection.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='main' AND table_name=? ORDER BY ordinal_position",
        [source],
    ).fetchall()
    if not rows:
        raise PresentationContractError(f"Authority surface is missing: {source}")
    return {str(row[0]) for row in rows}


def validate_authority_schema(connection: Any, contract: PresentationReadModelContract) -> None:
    """Schema-only validation; does not authorize publication or mutate analytical state."""
    surfaces: list[SurfaceContract] = list(contract.common_surfaces.values())
    for domain in contract.domains:
        surfaces.extend(domain.surfaces.values())
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for surface in surfaces:
        key = (surface.source, surface.required_fields)
        if key in seen:
            continue
        seen.add(key)
        actual = _columns(connection, surface.source)
        missing = sorted(set(surface.required_fields) - actual)
        if missing:
            raise PresentationContractError(
                f"Authority surface {surface.source} is missing contracted fields: {missing}"
            )
