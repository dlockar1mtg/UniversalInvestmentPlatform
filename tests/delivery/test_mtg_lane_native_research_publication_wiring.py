from __future__ import annotations

import os
from collections import Counter

import pytest

from foundation.presentation import publication_model


ENV_NAMES = (
    "UIP_MTG_COLLECTOR_RESEARCH_PATH",
    "UIP_MTG_COLLECTOR_HORIZON_RESEARCH_PATH",
    "UIP_MTG_PRECOLLECTOR_RESEARCH_PATH",
    "UIP_MTG_PRECOLLECTOR_SCENARIO_RESEARCH_PATH",
)


def source_environment() -> dict[str, str]:
    result = {}

    for name in ENV_NAMES:
        value = os.environ.get(name, "").strip()
        assert value, f"Missing test environment variable: {name}"
        result[name] = value

    return result


def clear_all(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(
            name,
            raising=False,
        )


def test_all_absent_preserves_existing_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_all(monkeypatch)

    assert (
        publication_model
        ._mtg_lane_native_research_records_from_environment()
        == []
    )


def test_partial_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = source_environment()

    clear_all(monkeypatch)

    monkeypatch.setenv(
        ENV_NAMES[0],
        values[ENV_NAMES[0]],
    )

    with pytest.raises(
        RuntimeError,
        match="Partial",
    ):
        publication_model._mtg_lane_native_research_records_from_environment()


def test_all_four_exact_paths_project_665_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = source_environment()

    for name, value in values.items():
        monkeypatch.setenv(
            name,
            value,
        )

    records = (
        publication_model
        ._mtg_lane_native_research_records_from_environment()
    )

    assert len(records) == 665

    counts = Counter(
        record.record_type
        for record in records
    )

    assert counts == {
        "mtg_collector_research": 50,
        "mtg_collector_forecast_horizon": 294,
        "mtg_precollector_research": 131,
        "mtg_precollector_scenario_horizon": 190,
    }


def test_missing_explicit_file_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    values = source_environment()

    for name, value in values.items():
        monkeypatch.setenv(
            name,
            value,
        )

    monkeypatch.setenv(
        ENV_NAMES[3],
        str(
            tmp_path
            / "missing-precollector-scenarios.csv"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="missing",
    ):
        publication_model._mtg_lane_native_research_records_from_environment()


def test_existing_premium_helper_remains_present() -> None:
    source = (
        publication_model.__file__
    )

    text = open(
        source,
        "r",
        encoding="utf-8",
    ).read()

    assert (
        "def _mtg_premium_records_from_environment()"
        in text
    )

    assert (
        "records.extend(_mtg_premium_records_from_environment())"
        in text
    )

    assert (
        "records.extend(_mtg_lane_native_research_records_from_environment())"
        in text
    )


def test_lane_native_wiring_occurs_after_native_and_premium_mtg() -> None:
    text = open(
        publication_model.__file__,
        "r",
        encoding="utf-8",
    ).read()

    native = text.index(
        "records.extend(_mtg_records(connection))"
    )

    premium = text.index(
        "records.extend(_mtg_premium_records_from_environment())"
    )

    lane_native = text.index(
        "records.extend(_mtg_lane_native_research_records_from_environment())"
    )

    assert native < premium < lane_native