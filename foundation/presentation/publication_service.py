"""Fail-closed staging/validation/activation for DASH-READ-1 publications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .publication_model import PresentationPublication, PresentationRecord


class PresentationPublicationError(RuntimeError):
    """Raised when a presentation publication cannot be safely activated."""


class PresentationStore(Protocol):
    def stage(self, publication: PresentationPublication) -> None: ...
    def validate_staged(self, publication_id: str) -> dict[str, int]: ...
    def activate(self, publication_id: str) -> None: ...
    def reject(self, publication_id: str, reason: str) -> None: ...
    def active_metadata(self) -> dict[str, object] | None: ...


@dataclass(frozen=True)
class PublicationResult:
    publication_id: str
    content_fingerprint: str
    source_database_sha256: str
    status: str
    record_count: int
    previous_active_publication_id: str | None


def _records(publication: PresentationPublication, record_type: str, domain_id: str | None = None) -> tuple[PresentationRecord, ...]:
    return tuple(
        item for item in publication.records
        if item.record_type == record_type and (domain_id is None or item.domain_id == domain_id)
    )


def validate_publication_bundle(publication: PresentationPublication) -> None:
    """Validate semantic invariants before the presentation store is touched."""
    if publication.publication_status != "STAGED":
        raise PresentationPublicationError("Publication must enter the service as STAGED.")
    if not publication.source_database_sha256 or len(publication.source_database_sha256) != 64:
        raise PresentationPublicationError("Publication source database SHA-256 is invalid.")

    health = _records(publication, "domain_health")
    if tuple(sorted(item.domain_id for item in health)) != ("crypto", "metals", "mtg"):
        raise PresentationPublicationError("Publication must contain exactly one health record for each certified domain.")
    for item in health:
        payload = item.payload
        if payload.get("certification_state") != "CERTIFIED":
            raise PresentationPublicationError(f"{item.domain_id} is not CERTIFIED.")
        if payload.get("import_registry_status") != "ACTIVE":
            raise PresentationPublicationError(f"{item.domain_id} registry is not ACTIVE.")
        if payload.get("last_import_status") != "IMPORTED":
            raise PresentationPublicationError(f"{item.domain_id} last import is not IMPORTED.")
        if int(payload.get("warning_count") or 0) != 0 or int(payload.get("error_count") or 0) != 0:
            raise PresentationPublicationError(f"{item.domain_id} health contains warnings/errors.")
        if payload.get("native_semantics_authoritative") is not True:
            raise PresentationPublicationError(f"{item.domain_id} native semantics are not authoritative.")
        if payload.get("cross_asset_ranking_authorized") is not False:
            raise PresentationPublicationError("Cross-domain ranking became authorized.")
        if payload.get("automatic_execution_authorized") is not False:
            raise PresentationPublicationError("Automatic execution became authorized.")

    for domain_id in ("crypto", "metals", "mtg"):
        if not _records(publication, "asset", domain_id):
            raise PresentationPublicationError(f"{domain_id} has no current asset presentation surface.")

    for domain_id in ("crypto", "metals"):
        for item in _records(publication, "asset", domain_id):
            if item.payload.get("current_price_usd") is not None:
                raise PresentationPublicationError(f"{domain_id} current price was synthesized before a governed binding exists.")
            if item.payload.get("current_price_authority_available") is not False:
                raise PresentationPublicationError(f"{domain_id} current-price authority state changed unexpectedly.")
        for item in _records(publication, "recommendation", domain_id):
            if item.payload.get("cross_domain_rank") is not None:
                raise PresentationPublicationError("A cross-domain rank was introduced into the presentation bundle.")

    mtg_assets = _records(publication, "asset", "mtg")
    mtg_native = _records(publication, "native_authority", "mtg")
    if len(mtg_assets) != len(mtg_native):
        raise PresentationPublicationError("MTG asset projection does not reconcile to native current authority.")
    for item in _records(publication, "recommendation", "mtg"):
        if item.payload.get("automatic_purchase_execution") is not False:
            raise PresentationPublicationError("MTG automatic purchase execution is not allowed.")


def publish_presentation_bundle(store: PresentationStore, publication: PresentationPublication) -> PublicationResult:
    """Stage, validate and atomically activate one versioned presentation publication."""
    validate_publication_bundle(publication)
    previous = store.active_metadata()
    previous_id = str(previous["publication_id"]) if previous else None
    staged = False
    try:
        store.stage(publication)
        staged = True
        validation = store.validate_staged(publication.publication_id)
        if int(validation.get("record_count", -1)) != len(publication.records):
            raise PresentationPublicationError("Presentation store validation returned an unexpected record count.")
        store.activate(publication.publication_id)
    except Exception as exc:
        if staged:
            try:
                store.reject(publication.publication_id, str(exc))
            except Exception:
                pass
        raise PresentationPublicationError(
            f"Presentation publication failed; previous active version must remain unchanged: {exc}"
        ) from exc

    active = store.active_metadata()
    if not active or active.get("publication_id") != publication.publication_id or active.get("publication_status") != "ACTIVE":
        raise PresentationPublicationError("Presentation publication did not become the active version.")
    return PublicationResult(
        publication_id=publication.publication_id,
        content_fingerprint=publication.content_fingerprint,
        source_database_sha256=publication.source_database_sha256,
        status="ACTIVE",
        record_count=len(publication.records),
        previous_active_publication_id=previous_id,
    )
