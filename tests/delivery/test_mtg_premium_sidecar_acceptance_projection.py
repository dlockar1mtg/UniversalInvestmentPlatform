from __future__ import annotations

import os
from pathlib import Path

import pytest

from foundation.presentation.mtg_premium_projection import (
    DOMAIN_ID,
    EXPECTED_FIELD_COUNT,
    EXPECTED_FIELDS,
    EXPECTED_MTG_HEAD,
    EXPECTED_ROW_COUNT,
    EXPECTED_SIDECAR_SHA256,
    LANE,
    RECORD_TYPE,
    build_mtg_premium_records,
    project_premium_rows,
    sha256_file,
    validate_certified_sidecar,
)


def external_sidecar() -> Path:
    raw = os.environ.get(
        "UIP_MTG_PREMIUM_SIDECAR_PATH",
        "",
    ).strip()

    if not raw:
        pytest.skip(
            "Certified external MTG sidecar path not configured."
        )

    return Path(raw)


def test_contract_constants_are_frozen() -> None:
    assert DOMAIN_ID == "mtg"
    assert LANE == "SECRET_LAIR_V1_1"
    assert RECORD_TYPE == "mtg_premium_research"

    assert EXPECTED_ROW_COUNT == 787
    assert EXPECTED_FIELD_COUNT == 36
    assert len(EXPECTED_FIELDS) == 36

    assert (
        EXPECTED_MTG_HEAD
        == "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
    )

    assert (
        EXPECTED_SIDECAR_SHA256
        == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    )


def test_real_certified_sidecar_is_accepted() -> None:
    path = external_sidecar()

    assert sha256_file(path) == EXPECTED_SIDECAR_SHA256

    rows = validate_certified_sidecar(
        path,
        mtg_head=EXPECTED_MTG_HEAD,
    )

    assert len(rows) == 787
    assert len(rows[0]) == 36

    assert len(
        {
            row["mtg_asset_id"]
            for row in rows
        }
    ) == 787

    assert len(
        {
            row["secret_lair_id"]
            for row in rows
        }
    ) == 787


def test_wrong_mtg_head_fails_closed() -> None:
    path = external_sidecar()

    with pytest.raises(
        RuntimeError,
        match="source HEAD",
    ):
        validate_certified_sidecar(
            path,
            mtg_head="not-the-governed-head",
        )


def test_projection_preserves_full_payload_losslessly() -> None:
    path = external_sidecar()

    rows = validate_certified_sidecar(
        path,
        mtg_head=EXPECTED_MTG_HEAD,
    )

    records = project_premium_rows(rows)

    assert len(records) == 787

    for source, record in zip(
        rows,
        records,
        strict=True,
    ):
        assert record.record_type == RECORD_TYPE
        assert record.domain_id == "mtg"

        assert (
            record.asset_id
            == source["mtg_asset_id"]
        )

        assert (
            record.record_key
            == source["mtg_asset_id"]
        )

        assert dict(record.payload) == dict(source)


def test_end_to_end_real_sidecar_projection() -> None:
    path = external_sidecar()

    records = build_mtg_premium_records(
        path,
        mtg_head=EXPECTED_MTG_HEAD,
    )

    assert len(records) == 787

    asset_ids = [
        record.asset_id
        for record in records
    ]

    assert len(set(asset_ids)) == 787

    assert all(
        record.record_type
        == "mtg_premium_research"
        for record in records
    )


def test_projector_does_not_relabel_long_horizon_scenarios() -> None:
    path = external_sidecar()

    rows = validate_certified_sidecar(
        path,
        mtg_head=EXPECTED_MTG_HEAD,
    )

    records = project_premium_rows(rows)

    for source, record in zip(
        rows,
        records,
        strict=True,
    ):
        payload = dict(record.payload)

        assert (
            payload["y3_median_total_return_scenario"]
            == source["y3_median_total_return_scenario"]
        )

        assert (
            payload["y5_median_total_return_scenario"]
            == source["y5_median_total_return_scenario"]
        )

        assert "forecast_3y" not in payload
        assert "forecast_5y" not in payload


def test_projector_preserves_q10_without_q25_q50_substitution() -> None:
    path = external_sidecar()

    rows = validate_certified_sidecar(
        path,
        mtg_head=EXPECTED_MTG_HEAD,
    )

    records = project_premium_rows(rows)

    for source, record in zip(
        rows,
        records,
        strict=True,
    ):
        payload = dict(record.payload)

        assert (
            payload["y1_q10_break_even_entry_price_usd"]
            == source["y1_q10_break_even_entry_price_usd"]
        )


def test_projector_has_no_automatic_execution_surface() -> None:
    path = external_sidecar()

    records = build_mtg_premium_records(
        path,
        mtg_head=EXPECTED_MTG_HEAD,
    )

    for record in records:
        payload = dict(record.payload)

        assert (
            "automatic_purchase_execution"
            not in payload
        )

        assert (
            "execution_ready_purchase_certified"
            not in payload
        )
