"""Read-only typed interface to the governed D1 domain registry."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb


@dataclass(frozen=True)
class DomainRegistryEntry:
    domain_id: str
    domain_name: str
    platform_id: str
    ownership_type: str
    source_repository: str | None
    publication_boundary: str
    certification_state: str
    dynamic_asset_universe: bool
    native_semantics_authoritative: bool
    cross_asset_ranking_authorized: bool
    automatic_execution_authorized: bool
    registry_version: str
    notes: str | None


def list_certified_domains(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[DomainRegistryEntry, ...]:
    """Return the governed domain registry in deterministic order."""

    rows = connection.execute(
        """
        SELECT
            domain_id,
            domain_name,
            platform_id,
            ownership_type,
            source_repository,
            publication_boundary,
            certification_state,
            dynamic_asset_universe,
            native_semantics_authoritative,
            cross_asset_ranking_authorized,
            automatic_execution_authorized,
            registry_version,
            notes
        FROM universal_domain_registry
        ORDER BY domain_id
        """
    ).fetchall()

    return tuple(
        DomainRegistryEntry(
            domain_id=str(row[0]),
            domain_name=str(row[1]),
            platform_id=str(row[2]),
            ownership_type=str(row[3]),
            source_repository=(
                str(row[4]) if row[4] is not None else None
            ),
            publication_boundary=str(row[5]),
            certification_state=str(row[6]),
            dynamic_asset_universe=bool(row[7]),
            native_semantics_authoritative=bool(row[8]),
            cross_asset_ranking_authorized=bool(row[9]),
            automatic_execution_authorized=bool(row[10]),
            registry_version=str(row[11]),
            notes=(
                str(row[12]) if row[12] is not None else None
            ),
        )
        for row in rows
    )


def get_certified_domain(
    connection: duckdb.DuckDBPyConnection,
    domain_id: str,
) -> DomainRegistryEntry:
    """Return one governed domain or fail closed if it is unknown."""

    normalized = domain_id.strip().lower()

    matches = tuple(
        entry
        for entry in list_certified_domains(connection)
        if entry.domain_id == normalized
    )

    if len(matches) != 1:
        raise KeyError(f"Unknown certified UIP domain: {domain_id}")

    return matches[0]
