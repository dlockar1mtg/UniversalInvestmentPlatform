from foundation.presentation.publication_model import PresentationPublication, PresentationRecord
from foundation.presentation.publication_service import (
    PresentationPublicationError,
    publish_presentation_bundle,
    validate_publication_bundle,
)


def record(record_type, domain_id, key, payload, asset_id=None):
    return PresentationRecord(record_type, domain_id, asset_id, key, payload)


def valid_publication(publication_id="pub-new"):
    health = []
    for domain_id in ("crypto", "metals", "mtg"):
        health.append(record("domain_health", domain_id, domain_id, {
            "certification_state": "CERTIFIED",
            "import_registry_status": "ACTIVE",
            "last_import_status": "IMPORTED",
            "warning_count": 0,
            "error_count": 0,
            "native_semantics_authoritative": True,
            "cross_asset_ranking_authorized": False,
            "automatic_execution_authorized": False,
        }))
    records = health + [
        record("asset", "crypto", "crypto:btc", {
            "current_price_usd": None,
            "current_price_authority_available": False,
        }, "crypto:btc"),
        record("recommendation", "crypto", "crypto:btc", {
            "native_recommendation": "WATCH",
            "cross_domain_rank": None,
        }, "crypto:btc"),
        record("asset", "metals", "metals:gold", {
            "current_price_usd": None,
            "current_price_authority_available": False,
        }, "metals:gold"),
        record("recommendation", "metals", "metals:gold", {
            "native_recommendation": "HOLD",
            "cross_domain_rank": None,
        }, "metals:gold"),
        record("asset", "mtg", "mtg:1", {
            "current_price_usd": 42.0,
            "current_price_authority_available": True,
        }, "mtg:1"),
        record("recommendation", "mtg", "mtg:1", {
            "native_purchase_status": "BUY_CANDIDATE_NOW",
            "automatic_purchase_execution": False,
        }, "mtg:1"),
        record("native_authority", "mtg", "mtg:1", {
            "native_rank": 1,
            "automatic_purchase_execution": False,
        }, "mtg:1"),
    ]
    return PresentationPublication(
        publication_id=publication_id,
        publication_version="1.0.0",
        source_database_sha256="a" * 64,
        source_database_classification="AUTHORITATIVE_MULTI_DOMAIN_PRODUCTION_STATE_R3_CERTIFIED",
        published_at_utc="2026-08-23T03:30:00+00:00",
        publication_status="STAGED",
        records=tuple(records),
    )


class FakeStore:
    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.active = {
            "publication_id": "pub-old",
            "publication_status": "ACTIVE",
        }
        self.staged = None
        self.rejected = []

    def active_metadata(self):
        return dict(self.active) if self.active else None

    def stage(self, publication):
        if self.fail_at == "stage":
            raise RuntimeError("stage failed")
        self.staged = publication

    def validate_staged(self, publication_id):
        if self.fail_at == "validate":
            raise RuntimeError("validation failed")
        return {"record_count": len(self.staged.records), "mtg_asset_count": 1}

    def activate(self, publication_id):
        if self.fail_at == "activate":
            raise RuntimeError("activation failed")
        self.active = {
            "publication_id": publication_id,
            "publication_status": "ACTIVE",
        }

    def reject(self, publication_id, reason):
        self.rejected.append((publication_id, reason))


def test_valid_publication_preserves_governed_semantics():
    validate_publication_bundle(valid_publication())


def test_crypto_price_cannot_be_synthesized_before_binding():
    publication = valid_publication()
    records = list(publication.records)
    target = next(i for i, item in enumerate(records) if item.record_type == "asset" and item.domain_id == "crypto")
    records[target] = record("asset", "crypto", "crypto:btc", {
        "current_price_usd": 100000.0,
        "current_price_authority_available": True,
    }, "crypto:btc")
    bad = PresentationPublication(
        publication.publication_id, publication.publication_version,
        publication.source_database_sha256, publication.source_database_classification,
        publication.published_at_utc, publication.publication_status, tuple(records),
    )
    try:
        validate_publication_bundle(bad)
    except PresentationPublicationError as exc:
        assert "current price was synthesized" in str(exc)
    else:
        raise AssertionError("Synthesized Crypto price was accepted")


def test_cross_domain_rank_is_rejected():
    publication = valid_publication()
    records = list(publication.records)
    target = next(i for i, item in enumerate(records) if item.record_type == "recommendation" and item.domain_id == "metals")
    records[target] = record("recommendation", "metals", "metals:gold", {
        "native_recommendation": "HOLD",
        "cross_domain_rank": 1,
    }, "metals:gold")
    bad = PresentationPublication(
        publication.publication_id, publication.publication_version,
        publication.source_database_sha256, publication.source_database_classification,
        publication.published_at_utc, publication.publication_status, tuple(records),
    )
    try:
        validate_publication_bundle(bad)
    except PresentationPublicationError as exc:
        assert "cross-domain rank" in str(exc)
    else:
        raise AssertionError("Cross-domain rank was accepted")


def test_mtg_automatic_execution_is_rejected():
    publication = valid_publication()
    records = list(publication.records)
    target = next(i for i, item in enumerate(records) if item.record_type == "recommendation" and item.domain_id == "mtg")
    records[target] = record("recommendation", "mtg", "mtg:1", {
        "native_purchase_status": "BUY_CANDIDATE_NOW",
        "automatic_purchase_execution": True,
    }, "mtg:1")
    bad = PresentationPublication(
        publication.publication_id, publication.publication_version,
        publication.source_database_sha256, publication.source_database_classification,
        publication.published_at_utc, publication.publication_status, tuple(records),
    )
    try:
        validate_publication_bundle(bad)
    except PresentationPublicationError as exc:
        assert "automatic purchase execution" in str(exc)
    else:
        raise AssertionError("Automatic MTG execution was accepted")


def test_successful_publication_switches_active_pointer():
    store = FakeStore()
    result = publish_presentation_bundle(store, valid_publication())
    assert result.status == "ACTIVE"
    assert result.previous_active_publication_id == "pub-old"
    assert store.active["publication_id"] == "pub-new"
    assert not store.rejected


def test_failed_validation_preserves_previous_active_version():
    store = FakeStore(fail_at="validate")
    try:
        publish_presentation_bundle(store, valid_publication())
    except PresentationPublicationError as exc:
        assert "previous active version must remain unchanged" in str(exc)
    else:
        raise AssertionError("Failed publication unexpectedly succeeded")
    assert store.active["publication_id"] == "pub-old"
    assert store.rejected and store.rejected[0][0] == "pub-new"


def test_failed_activation_preserves_previous_active_version():
    store = FakeStore(fail_at="activate")
    try:
        publish_presentation_bundle(store, valid_publication())
    except PresentationPublicationError:
        pass
    else:
        raise AssertionError("Failed activation unexpectedly succeeded")
    assert store.active["publication_id"] == "pub-old"
    assert store.rejected and store.rejected[0][0] == "pub-new"
