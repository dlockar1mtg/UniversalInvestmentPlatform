from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path

import pytest

from foundation.presentation.mtg_lane_native_research_projection import (
    COLLECTOR_HORIZON_RECORD_TYPE,
    COLLECTOR_PRODUCT_RECORD_TYPE,
    EXPECTED_MTG_HEAD,
    LOTR_CURRENT_PRICE_ONLY_ID,
    PRECOLLECTOR_PRODUCT_RECORD_TYPE,
    PRECOLLECTOR_SCENARIO_RECORD_TYPE,
    build_mtg_lane_native_research_records,
)


ENV_NAMES = (
    "UIP_MTG_COLLECTOR_RESEARCH_PATH",
    "UIP_MTG_COLLECTOR_HORIZON_RESEARCH_PATH",
    "UIP_MTG_PRECOLLECTOR_RESEARCH_PATH",
    "UIP_MTG_PRECOLLECTOR_SCENARIO_RESEARCH_PATH",
)


def paths() -> tuple[Path, Path, Path, Path]:
    raw_values = [
        os.environ.get(name, "").strip()
        for name in ENV_NAMES
    ]

    if not any(raw_values):
        pytest.skip(
            "Certified MTG lane-native external authorities "
            "are not configured."
        )

    values = []

    for name, raw in zip(
        ENV_NAMES,
        raw_values,
        strict=True,
    ):
        assert raw, f"Missing test environment variable: {name}"

        values.append(Path(raw))

    return tuple(values)


def build():
    return build_mtg_lane_native_research_records(
        *paths(),
        mtg_head=EXPECTED_MTG_HEAD,
    )


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def test_exact_record_populations() -> None:
    records = build()

    assert len(records) == 665

    counts = Counter(
        record.record_type
        for record in records
    )

    assert counts == {
        COLLECTOR_PRODUCT_RECORD_TYPE: 50,
        COLLECTOR_HORIZON_RECORD_TYPE: 294,
        PRECOLLECTOR_PRODUCT_RECORD_TYPE: 131,
        PRECOLLECTOR_SCENARIO_RECORD_TYPE: 190,
    }


def test_collector_asset_identity_is_exact() -> None:
    records = build()

    edge_id = (
        "COLLECTOR_V1|"
        "MTG-CANON-TCGPLAYER-619672"
    )

    edge_product = [
        record
        for record in records
        if (
            record.record_type
            == COLLECTOR_PRODUCT_RECORD_TYPE
            and record.asset_id == edge_id
        )
    ]

    assert len(edge_product) == 1

    payload = dict(edge_product[0].payload)

    assert payload["current_price"] == "717.61"
    assert payload["final_rank"] == "1"
    assert payload["median_price_365"] == "1205.893871"
    assert payload["probability_of_loss_365"] == "0.0023"


def test_collector_horizon_projection_is_six_rows_for_edge() -> None:
    records = build()

    edge_id = (
        "COLLECTOR_V1|"
        "MTG-CANON-TCGPLAYER-619672"
    )

    rows = [
        record
        for record in records
        if (
            record.record_type
            == COLLECTOR_HORIZON_RECORD_TYPE
            and record.asset_id == edge_id
        )
    ]

    assert len(rows) == 6

    assert {
        record.payload["horizon_days"]
        for record in rows
    } == {
        "90",
        "180",
        "365",
        "730",
        "1095",
        "1825",
    }


def test_lotr_current_price_only_boundary_is_preserved() -> None:
    records = build()

    asset_id = (
        "COLLECTOR_V1|"
        + LOTR_CURRENT_PRICE_ONLY_ID
    )

    products = [
        record
        for record in records
        if (
            record.record_type
            == COLLECTOR_PRODUCT_RECORD_TYPE
            and record.asset_id == asset_id
        )
    ]

    horizons = [
        record
        for record in records
        if (
            record.record_type
            == COLLECTOR_HORIZON_RECORD_TYPE
            and record.asset_id == asset_id
        )
    ]

    assert len(products) == 1
    assert len(horizons) == 0

    payload = dict(products[0].payload)

    assert payload["current_price"] == "5828.6"
    assert payload["final_rank"] == ""
    assert payload["median_price_365"] == ""
    assert payload["purchase_status"] == ""


def test_dominaria_product_and_scenarios_are_projected() -> None:
    records = build()

    asset_id = (
        "PRE_COLLECTOR_V1|"
        "tcgplayer:158423"
    )

    products = [
        record
        for record in records
        if (
            record.record_type
            == PRECOLLECTOR_PRODUCT_RECORD_TYPE
            and record.asset_id == asset_id
        )
    ]

    scenarios = [
        record
        for record in records
        if (
            record.record_type
            == PRECOLLECTOR_SCENARIO_RECORD_TYPE
            and record.asset_id == asset_id
        )
    ]

    assert len(products) == 1
    assert len(scenarios) == 2

    product = dict(products[0].payload)

    assert product["current_price"] == "207.54"
    assert product["purchase_rank"] == "1"
    assert product["final_analysis_status"] == "RANKED_FORECASTABLE"

    classes = {
        row.payload["scenario_classification"]
        for row in scenarios
    }

    assert classes == {
        "THREE_YEAR_SCENARIO_NOT_DIRECTLY_BACKTESTED",
        "FIVE_YEAR_SCENARIO_NOT_DIRECTLY_BACKTESTED",
    }

    assert all(
        row.payload[
            "directly_backtested_at_this_horizon"
        ]
        == "false"
        for row in scenarios
    )


def test_unranked_precollector_has_no_scenario_records() -> None:
    product_rows = csv_rows(
        paths()[2]
    )

    unranked = next(
        row
        for row in product_rows
        if (
            row["final_analysis_status"]
            != "RANKED_FORECASTABLE"
        )
    )

    asset_id = (
        "PRE_COLLECTOR_V1|"
        + unranked["canonical_product_id"]
    )

    records = build()

    product_records = [
        record
        for record in records
        if (
            record.record_type
            == PRECOLLECTOR_PRODUCT_RECORD_TYPE
            and record.asset_id == asset_id
        )
    ]

    scenario_records = [
        record
        for record in records
        if (
            record.record_type
            == PRECOLLECTOR_SCENARIO_RECORD_TYPE
            and record.asset_id == asset_id
        )
    ]

    assert len(product_records) == 1
    assert len(scenario_records) == 0


def test_projection_payloads_are_lossless() -> None:
    source_paths = paths()

    source_sets = {
        COLLECTOR_PRODUCT_RECORD_TYPE: csv_rows(source_paths[0]),
        COLLECTOR_HORIZON_RECORD_TYPE: csv_rows(source_paths[1]),
        PRECOLLECTOR_PRODUCT_RECORD_TYPE: csv_rows(source_paths[2]),
        PRECOLLECTOR_SCENARIO_RECORD_TYPE: csv_rows(source_paths[3]),
    }

    projected = build()

    for record_type, source_rows in source_sets.items():
        projected_rows = [
            dict(record.payload)
            for record in projected
            if record.record_type == record_type
        ]

        assert projected_rows == source_rows


def test_wrong_mtg_head_fails_closed() -> None:
    with pytest.raises(
        RuntimeError,
        match="source HEAD",
    ):
        build_mtg_lane_native_research_records(
            *paths(),
            mtg_head="wrong-head",
        )


def test_invalid_sidecar_fails_closed_before_projection(
    tmp_path: Path,
) -> None:
    real = paths()

    bad = tmp_path / "collector.csv"
    bad.write_bytes(real[0].read_bytes() + b"\n")

    with pytest.raises(
        RuntimeError,
        match="SHA-256",
    ):
        build_mtg_lane_native_research_records(
            bad,
            real[1],
            real[2],
            real[3],
            mtg_head=EXPECTED_MTG_HEAD,
        )


def test_no_execution_or_cross_domain_fields_are_created() -> None:
    records = build()

    forbidden = {
        "automatic_purchase_execution",
        "execution_ready_purchase_certified",
        "universal_mtg_rank",
        "cross_domain_rank",
        "cross_lane_score",
    }

    for record in records:
        assert not (
            forbidden
            & set(record.payload)
        )