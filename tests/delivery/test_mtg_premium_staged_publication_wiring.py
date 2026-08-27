from __future__ import annotations

from collections import Counter
from pathlib import Path
import os

import pytest

import foundation.presentation.metals_tactical_projection as metals_projection
import foundation.presentation.publication_model as publication_model


EXPECTED_MTG_HEAD = (
    "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
)

EXPECTED_SIDECAR_SHA256 = (
    "296ccbb9ba96812b99dacd771f1ad311"
    "496b4997fa0ac7103e68a1d4aaa03333"
)


def external_sidecar() -> Path:
    raw = os.environ.get(
        "UIP_MTG_PREMIUM_TEST_SIDECAR_PATH",
        "",
    ).strip()

    if not raw:
        raise AssertionError(
            "UIP_MTG_PREMIUM_TEST_SIDECAR_PATH must be configured."
        )

    return Path(raw)


def marker(
    record_type: str,
    domain_id: str,
    asset_id: str,
) -> publication_model.PresentationRecord:
    return publication_model.PresentationRecord(
        record_type=record_type,
        domain_id=domain_id,
        asset_id=asset_id,
        record_key=asset_id,
        payload={
            "marker": asset_id,
        },
    )


@pytest.fixture
def isolated_publication_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    database_path = tmp_path / "authority.duckdb"

    database_path.write_bytes(
        b"certification-only-test-database"
    )

    monkeypatch.setattr(
        publication_model,
        "validate_authority_schema",
        lambda connection, contract: None,
    )

    monkeypatch.setattr(
        publication_model,
        "_domain_health_records",
        lambda connection: [
            marker(
                "domain_health",
                "mtg",
                "domain-health-marker",
            )
        ],
    )

    monkeypatch.setattr(
        publication_model,
        "_generic_records",
        lambda connection, domain_id: [
            marker(
                "asset",
                domain_id,
                f"{domain_id}-marker",
            )
        ],
    )

    monkeypatch.setattr(
        publication_model,
        "_mtg_records",
        lambda connection: [
            marker(
                "native_authority",
                "mtg",
                "native-mtg-marker",
            ),
            marker(
                "recommendation",
                "mtg",
                "native-rec-marker",
            ),
        ],
    )

    monkeypatch.setattr(
        metals_projection,
        "build_metals_tactical_records",
        lambda repository_root, connection, source_sha256: [
            marker(
                "metals_tactical_marker",
                "metals",
                "metals-tactical-marker",
            )
        ],
    )

    return database_path


def build(
    database_path: Path,
) -> publication_model.PresentationPublication:
    return publication_model.build_presentation_publication(
        repository_root=Path("."),
        database_path=database_path,
        connection=object(),
        publication_id="test-publication",
        published_at_utc="2026-08-27T00:00:00+00:00",
        contract=object(),
    )


def canonical_nonpremium(
    publication: publication_model.PresentationPublication,
) -> list[dict]:
    return [
        record.canonical()
        for record in publication.records
        if record.record_type != "mtg_premium_research"
    ]


def test_environment_absent_preserves_existing_publication(
    isolated_publication_dependencies: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        raising=False,
    )

    publication = build(
        isolated_publication_dependencies
    )

    assert publication.publication_status == "STAGED"

    assert not any(
        record.record_type == "mtg_premium_research"
        for record in publication.records
    )

    counts = Counter(
        record.record_type
        for record in publication.records
    )

    assert counts["native_authority"] == 1
    assert counts["recommendation"] == 1


def test_exact_external_sidecar_adds_787_records_only(
    isolated_publication_dependencies: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sidecar = external_sidecar()

    monkeypatch.delenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        raising=False,
    )

    baseline = build(
        isolated_publication_dependencies
    )

    monkeypatch.setenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        str(sidecar),
    )

    premium = build(
        isolated_publication_dependencies
    )

    assert baseline.publication_status == "STAGED"
    assert premium.publication_status == "STAGED"

    premium_records = [
        record
        for record in premium.records
        if record.record_type == "mtg_premium_research"
    ]

    assert len(premium_records) == 787

    assert (
        len(premium.records)
        == len(baseline.records) + 787
    )

    assert (
        canonical_nonpremium(premium)
        == canonical_nonpremium(baseline)
    )

    assert len(
        {
            record.asset_id
            for record in premium_records
        }
    ) == 787

    assert all(
        record.domain_id == "mtg"
        for record in premium_records
    )


def test_real_premium_payload_is_lossless(
    isolated_publication_dependencies: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from foundation.presentation.mtg_premium_projection import (
        EXPECTED_FIELDS,
        EXPECTED_MTG_HEAD as PROJECTOR_MTG_HEAD,
        EXPECTED_SIDECAR_SHA256 as PROJECTOR_SHA,
        validate_certified_sidecar,
    )

    sidecar = external_sidecar()

    assert PROJECTOR_MTG_HEAD == EXPECTED_MTG_HEAD
    assert PROJECTOR_SHA == EXPECTED_SIDECAR_SHA256

    source_rows = validate_certified_sidecar(
        sidecar,
        mtg_head=EXPECTED_MTG_HEAD,
    )

    monkeypatch.setenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        str(sidecar),
    )

    publication = build(
        isolated_publication_dependencies
    )

    premium_records = [
        record
        for record in publication.records
        if record.record_type == "mtg_premium_research"
    ]

    assert len(premium_records) == 787

    source_by_asset = {
        row["mtg_asset_id"]: row
        for row in source_rows
    }

    for record in premium_records:
        source = source_by_asset[
            str(record.asset_id)
        ]

        assert (
            dict(record.payload)
            == {
                field: source[field]
                for field in EXPECTED_FIELDS
            }
        )


def test_invalid_present_external_path_fails_closed(
    isolated_publication_dependencies: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "invalid-sidecar.csv"

    invalid.write_text(
        "mtg_asset_id,secret_lair_id\nbad,bad\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        str(invalid),
    )

    with pytest.raises(
        RuntimeError,
        match="SHA-256",
    ):
        build(
            isolated_publication_dependencies
        )


def test_missing_present_external_path_fails_closed(
    isolated_publication_dependencies: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "does-not-exist.csv"

    monkeypatch.setenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        str(missing),
    )

    with pytest.raises(
        RuntimeError,
        match="missing",
    ):
        build(
            isolated_publication_dependencies
        )


def test_premium_wiring_does_not_create_execution_surface(
    isolated_publication_dependencies: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        str(external_sidecar()),
    )

    publication = build(
        isolated_publication_dependencies
    )

    premium_records = [
        record
        for record in publication.records
        if record.record_type == "mtg_premium_research"
    ]

    assert premium_records

    for record in premium_records:
        payload = dict(record.payload)

        assert (
            "automatic_purchase_execution"
            not in payload
        )

        assert (
            "execution_ready_purchase_certified"
            not in payload
        )


def test_premium_wiring_preserves_scenario_names_and_q10(
    isolated_publication_dependencies: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        str(external_sidecar()),
    )

    publication = build(
        isolated_publication_dependencies
    )

    premium_records = [
        record
        for record in publication.records
        if record.record_type == "mtg_premium_research"
    ]

    assert len(premium_records) == 787

    for record in premium_records:
        payload = dict(record.payload)

        assert (
            "y1_q10_break_even_entry_price_usd"
            in payload
        )

        assert (
            "y3_median_total_return_scenario"
            in payload
        )

        assert (
            "y5_median_total_return_scenario"
            in payload
        )

        assert "forecast_3y" not in payload
        assert "forecast_5y" not in payload
