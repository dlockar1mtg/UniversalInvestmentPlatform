"""Validate and project certified MTG Collector / Pre-Collector research."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .publication_model import PresentationRecord


ROOT = Path(__file__).resolve().parents[2]

AUTHORIZATION_PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_lane_native_research_hydration_implementation_authorization_v1.json"
)

DOMAIN_ID = "mtg"

EXPECTED_MTG_HEAD = (
    "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
)

COLLECTOR_PRODUCT_RECORD_TYPE = "mtg_collector_research"
COLLECTOR_HORIZON_RECORD_TYPE = "mtg_collector_forecast_horizon"
PRECOLLECTOR_PRODUCT_RECORD_TYPE = "mtg_precollector_research"
PRECOLLECTOR_SCENARIO_RECORD_TYPE = "mtg_precollector_scenario_horizon"

COLLECTOR_PREFIX = "COLLECTOR_V1|"
PRECOLLECTOR_PREFIX = "PRE_COLLECTOR_V1|"

LOTR_CURRENT_PRICE_ONLY_ID = "MTG-CANON-TCGPLAYER-515906"

FORBIDDEN_PRESENTATION_FIELDS = {
    "automatic_purchase_execution",
    "execution_ready_purchase_certified",
    "universal_mtg_rank",
    "cross_domain_rank",
    "cross_lane_score",
}


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    record_type: str
    expected_sha256: str
    expected_rows: int
    required_fields: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _authorization() -> dict:
    document = json.loads(
        AUTHORIZATION_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        document.get("status")
        != "AUTHORIZED_FOR_BOUNDED_PRESENTATION_PROJECTION_AND_WIRING_IMPLEMENTATION"
    ):
        raise RuntimeError(
            "Lane-native MTG projection authorization is not active."
        )

    if (
        int(
            document["governing_checkpoints"]
            ["frozen_common_mtg_field_count"]
        )
        != 23
    ):
        raise RuntimeError(
            "Frozen common MTG authority field count changed."
        )

    return document


def _specs() -> dict[str, DatasetSpec]:
    auth = _authorization()
    data = auth["certified_datasets"]

    return {
        "collector_product": DatasetSpec(
            key="collector_product",
            record_type=COLLECTOR_PRODUCT_RECORD_TYPE,
            expected_sha256=str(
                data["collector_product"]["sha256"]
            ),
            expected_rows=int(
                data["collector_product"]["row_count"]
            ),
            required_fields=(
                "canonical_product_id",
                "product_name",
                "current_price",
            ),
        ),
        "collector_horizon": DatasetSpec(
            key="collector_horizon",
            record_type=COLLECTOR_HORIZON_RECORD_TYPE,
            expected_sha256=str(
                data["collector_horizon"]["sha256"]
            ),
            expected_rows=int(
                data["collector_horizon"]["row_count"]
            ),
            required_fields=(
                "canonical_product_id",
                "horizon_days",
                "current_price",
            ),
        ),
        "precollector_product": DatasetSpec(
            key="precollector_product",
            record_type=PRECOLLECTOR_PRODUCT_RECORD_TYPE,
            expected_sha256=str(
                data["precollector_product"]["sha256"]
            ),
            expected_rows=int(
                data["precollector_product"]["row_count"]
            ),
            required_fields=(
                "canonical_product_id",
                "product_name",
                "final_analysis_status",
            ),
        ),
        "precollector_scenario": DatasetSpec(
            key="precollector_scenario",
            record_type=PRECOLLECTOR_SCENARIO_RECORD_TYPE,
            expected_sha256=str(
                data["precollector_scenario"]["sha256"]
            ),
            expected_rows=int(
                data["precollector_scenario"]["row_count"]
            ),
            required_fields=(
                "canonical_product_id",
                "monte_carlo_horizon_years",
                "scenario_classification",
                "directly_backtested_at_this_horizon",
            ),
        ),
    }


def _read_exact_csv(
    path: Path,
    spec: DatasetSpec,
) -> tuple[dict[str, str], ...]:
    if not path.is_file():
        raise RuntimeError(
            f"Explicit MTG research sidecar is missing: {path}"
        )

    actual_sha = sha256_file(path)

    if actual_sha != spec.expected_sha256:
        raise RuntimeError(
            f"{spec.key} SHA-256 does not match certified authority."
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        raw_rows = list(reader)

    if len(raw_rows) != spec.expected_rows:
        raise RuntimeError(
            f"{spec.key} row count changed: "
            f"expected={spec.expected_rows} actual={len(raw_rows)}"
        )

    for field in spec.required_fields:
        if field not in fields:
            raise RuntimeError(
                f"{spec.key} required field missing: {field}"
            )

    unexpected = (
        set(fields)
        & FORBIDDEN_PRESENTATION_FIELDS
    )

    if unexpected:
        raise RuntimeError(
            f"{spec.key} contains forbidden presentation fields: "
            f"{sorted(unexpected)}"
        )

    rows: list[dict[str, str]] = []

    for source in raw_rows:
        row = {
            str(field): (
                ""
                if source.get(field) is None
                else str(source.get(field))
            )
            for field in fields
        }

        rows.append(row)

    return tuple(rows)


def _asset_id(
    canonical_product_id: str,
    *,
    prefix: str,
) -> str:
    value = canonical_product_id.strip()

    if not value:
        raise RuntimeError(
            "Blank canonical_product_id in MTG research sidecar."
        )

    return f"{prefix}{value}"


def _unique_product_rows(
    rows: tuple[dict[str, str], ...],
    *,
    label: str,
) -> None:
    seen: set[str] = set()

    for row in rows:
        key = row["canonical_product_id"].strip()

        if not key:
            raise RuntimeError(
                f"{label} contains blank canonical_product_id."
            )

        if key in seen:
            raise RuntimeError(
                f"{label} contains duplicate canonical_product_id: {key}"
            )

        seen.add(key)


def _unique_horizon_rows(
    rows: tuple[dict[str, str], ...],
    *,
    horizon_field: str,
    label: str,
) -> None:
    seen: set[tuple[str, str]] = set()

    for row in rows:
        product = row["canonical_product_id"].strip()
        horizon = row[horizon_field].strip()

        if not product or not horizon:
            raise RuntimeError(
                f"{label} contains blank product/horizon identity."
            )

        key = (product, horizon)

        if key in seen:
            raise RuntimeError(
                f"{label} contains duplicate horizon key: {key}"
            )

        seen.add(key)


def _project_product_rows(
    rows: tuple[Mapping[str, str], ...],
    *,
    record_type: str,
    prefix: str,
) -> list[PresentationRecord]:
    records: list[PresentationRecord] = []

    for source in rows:
        payload = dict(source)

        canonical_id = str(
            payload["canonical_product_id"]
        )

        asset_id = _asset_id(
            canonical_id,
            prefix=prefix,
        )

        records.append(
            PresentationRecord(
                record_type=record_type,
                domain_id=DOMAIN_ID,
                asset_id=asset_id,
                record_key=canonical_id,
                payload=payload,
            )
        )

    return records


def _project_horizon_rows(
    rows: tuple[Mapping[str, str], ...],
    *,
    record_type: str,
    prefix: str,
    horizon_field: str,
) -> list[PresentationRecord]:
    records: list[PresentationRecord] = []

    for source in rows:
        payload = dict(source)

        canonical_id = str(
            payload["canonical_product_id"]
        )

        horizon = str(
            payload[horizon_field]
        )

        asset_id = _asset_id(
            canonical_id,
            prefix=prefix,
        )

        record_key = (
            f"{canonical_id}|{horizon}"
        )

        records.append(
            PresentationRecord(
                record_type=record_type,
                domain_id=DOMAIN_ID,
                asset_id=asset_id,
                record_key=record_key,
                payload=payload,
            )
        )

    return records


def build_mtg_lane_native_research_records(
    collector_product_path: Path,
    collector_horizon_path: Path,
    precollector_product_path: Path,
    precollector_scenario_path: Path,
    *,
    mtg_head: str,
) -> list[PresentationRecord]:
    """
    Validate and project already-certified lane-native MTG research.

    No forecast, risk, score, rank, recommendation, scenario, or
    execution value is calculated here.
    """
    if mtg_head != EXPECTED_MTG_HEAD:
        raise RuntimeError(
            "MTG source HEAD does not match governed checkpoint."
        )

    specs = _specs()

    collector_products = _read_exact_csv(
        collector_product_path,
        specs["collector_product"],
    )

    collector_horizons = _read_exact_csv(
        collector_horizon_path,
        specs["collector_horizon"],
    )

    precollector_products = _read_exact_csv(
        precollector_product_path,
        specs["precollector_product"],
    )

    precollector_scenarios = _read_exact_csv(
        precollector_scenario_path,
        specs["precollector_scenario"],
    )

    _unique_product_rows(
        collector_products,
        label="Collector product research",
    )

    _unique_horizon_rows(
        collector_horizons,
        horizon_field="horizon_days",
        label="Collector horizon research",
    )

    _unique_product_rows(
        precollector_products,
        label="Pre-Collector product research",
    )

    _unique_horizon_rows(
        precollector_scenarios,
        horizon_field="monte_carlo_horizon_years",
        label="Pre-Collector scenario research",
    )

    collector_product_ids = {
        row["canonical_product_id"]
        for row in collector_products
    }

    collector_horizon_ids = {
        row["canonical_product_id"]
        for row in collector_horizons
    }

    if len(collector_product_ids) != 50:
        raise RuntimeError(
            "Collector product population must remain 50."
        )

    if len(collector_horizon_ids) != 49:
        raise RuntimeError(
            "Collector analytical population must remain 49."
        )

    if (
        collector_product_ids - collector_horizon_ids
        != {LOTR_CURRENT_PRICE_ONLY_ID}
    ):
        raise RuntimeError(
            "Collector current-price-only boundary changed."
        )

    pre_product_ids = {
        row["canonical_product_id"]
        for row in precollector_products
    }

    pre_ranked_ids = {
        row["canonical_product_id"]
        for row in precollector_products
        if row.get("final_analysis_status") == "RANKED_FORECASTABLE"
    }

    pre_scenario_ids = {
        row["canonical_product_id"]
        for row in precollector_scenarios
    }

    if len(pre_product_ids) != 131:
        raise RuntimeError(
            "Pre-Collector product population must remain 131."
        )

    if len(pre_ranked_ids) != 95:
        raise RuntimeError(
            "Pre-Collector ranked population must remain 95."
        )

    if pre_scenario_ids != pre_ranked_ids:
        raise RuntimeError(
            "Pre-Collector scenario population must exactly equal "
            "the ranked/forecastable population."
        )

    collector_horizon_counts: dict[str, int] = {}

    for row in collector_horizons:
        product = row["canonical_product_id"]

        collector_horizon_counts[product] = (
            collector_horizon_counts.get(product, 0)
            + 1
        )

    if any(
        count != 6
        for count in collector_horizon_counts.values()
    ):
        raise RuntimeError(
            "Every analytical Collector product must retain six horizons."
        )

    scenario_counts: dict[str, int] = {}

    for row in precollector_scenarios:
        product = row["canonical_product_id"]
        horizon = row["monte_carlo_horizon_years"]

        expected_classification = {
            "3": "THREE_YEAR_SCENARIO_NOT_DIRECTLY_BACKTESTED",
            "5": "FIVE_YEAR_SCENARIO_NOT_DIRECTLY_BACKTESTED",
        }.get(horizon)

        if expected_classification is None:
            raise RuntimeError(
                f"Unexpected Pre-Collector scenario horizon: {horizon}"
            )

        if (
            row["scenario_classification"]
            != expected_classification
        ):
            raise RuntimeError(
                "Pre-Collector scenario classification changed."
            )

        if (
            row["directly_backtested_at_this_horizon"]
            != "false"
        ):
            raise RuntimeError(
                "Pre-Collector 3Y/5Y scenario was relabeled as "
                "directly backtested."
            )

        scenario_counts[product] = (
            scenario_counts.get(product, 0)
            + 1
        )

    if any(
        count != 2
        for count in scenario_counts.values()
    ):
        raise RuntimeError(
            "Every ranked Pre-Collector product must retain "
            "exactly 3Y and 5Y scenario records."
        )

    records: list[PresentationRecord] = []

    records.extend(
        _project_product_rows(
            collector_products,
            record_type=COLLECTOR_PRODUCT_RECORD_TYPE,
            prefix=COLLECTOR_PREFIX,
        )
    )

    records.extend(
        _project_horizon_rows(
            collector_horizons,
            record_type=COLLECTOR_HORIZON_RECORD_TYPE,
            prefix=COLLECTOR_PREFIX,
            horizon_field="horizon_days",
        )
    )

    records.extend(
        _project_product_rows(
            precollector_products,
            record_type=PRECOLLECTOR_PRODUCT_RECORD_TYPE,
            prefix=PRECOLLECTOR_PREFIX,
        )
    )

    records.extend(
        _project_horizon_rows(
            precollector_scenarios,
            record_type=PRECOLLECTOR_SCENARIO_RECORD_TYPE,
            prefix=PRECOLLECTOR_PREFIX,
            horizon_field="monte_carlo_horizon_years",
        )
    )

    expected_total = 50 + 294 + 131 + 190

    if len(records) != expected_total:
        raise RuntimeError(
            f"Lane-native presentation record count changed: "
            f"{len(records)}"
        )

    return records