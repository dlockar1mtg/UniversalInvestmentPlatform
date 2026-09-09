"""Validate and project the certified MTG Secret Lair premium sidecar."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any, Mapping

from .publication_model import PresentationRecord


RECORD_TYPE = "mtg_premium_research"
DOMAIN_ID = "mtg"
LANE = "SECRET_LAIR_V1_1"

EXPECTED_MTG_HEAD = (
    "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
)

EXPECTED_SIDECAR_SHA256 = (
    "296ccbb9ba96812b99dacd771f1ad311"
    "496b4997fa0ac7103e68a1d4aaa03333"
)

EXPECTED_ROW_COUNT = 787
EXPECTED_FIELD_COUNT = 36

EXPECTED_SOURCE_AUTHORITY_SHA256 = (
    "eb5efced959116eb7b174d4aff27c06d"
    "321e774eda39b3f8572d958499441cdb"
)

EXPECTED_SOURCE_AUTHORITY_PATH = (
    "docs/phase_8/secret_lair/"
    "secret_lair_v1_purchase_analysis.csv"
)

IDENTITY_FIELDS = (
    "mtg_asset_id",
    "secret_lair_id",
    "product_name",
)

AUTHORIZED_SOURCE_FIELDS = (
    "current_tcg_market_price_usd",
    "certified_1y_point_forecast_usd",
    "certified_1y_point_return",
    "y1_q10_break_even_entry_price_usd",
    "current_price_margin_to_q10_break_even",
    "current_price_vs_q10_break_even_state",
    "y1_probability_of_loss",
    "y1_probability_of_positive_return",
    "y1_downside_tail_mean_total_return",
    "y1_upside_tail_mean_total_return",
    "y1_q10_terminal_value_usd",
    "y1_q50_terminal_value_usd",
    "y1_q90_terminal_value_usd",
    "y3_median_total_return_scenario",
    "y3_probability_of_loss_scenario",
    "y3_q10_terminal_value_scenario_usd",
    "y3_q50_terminal_value_scenario_usd",
    "y3_q90_terminal_value_scenario_usd",
    "y5_median_total_return_scenario",
    "y5_probability_of_loss_scenario",
    "y5_q10_terminal_value_scenario_usd",
    "y5_q50_terminal_value_scenario_usd",
    "y5_q90_terminal_value_scenario_usd",
    "own_history_evidence_class",
    "history_span_days",
    "historical_observation_count",
    "exact_structural_comparable_support",
    "exact_structural_comparable_product_count",
    "global_comparable_product_count",
    "exact_structural_comparable_event_count",
    "global_comparable_event_count",
)

LINEAGE_FIELDS = (
    "source_authority_path",
    "source_authority_sha256",
)

EXPECTED_FIELDS = (
    IDENTITY_FIELDS
    + AUTHORIZED_SOURCE_FIELDS
    + LINEAGE_FIELDS
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def canonical_crlf_sha256(path: Path) -> str:
    """Hash certified text using the original Windows CRLF byte convention.

    The Secret Lair sidecar was certified on Windows. Git checkout on Linux
    normalizes line endings to LF, so raw-byte hashing creates a false mismatch.
    Canonicalizing only line endings preserves the original governed hash while
    continuing to fail closed on any substantive content change.
    """

    raw = path.read_bytes()
    normalized_lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    canonical = normalized_lf.replace(b"\n", b"\r\n")
    return hashlib.sha256(canonical).hexdigest()


def _read_sidecar(
    path: Path,
) -> tuple[list[dict[str, str]], list[str]]:
    if not path.is_file():
        raise RuntimeError(
            f"Certified MTG premium sidecar is missing: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        fields = list(reader.fieldnames or [])
        rows = list(reader)

    return rows, fields


def validate_certified_sidecar(
    path: Path,
    *,
    mtg_head: str,
) -> tuple[dict[str, str], ...]:
    """Accept only the exact governed Secret Lair premium sidecar."""

    if mtg_head != EXPECTED_MTG_HEAD:
        raise RuntimeError(
            "MTG premium source HEAD does not match "
            "the governed checkpoint."
        )

    observed_sha = canonical_crlf_sha256(path)

    if observed_sha != EXPECTED_SIDECAR_SHA256:
        raise RuntimeError(
            "MTG premium sidecar canonical SHA-256 does not match "
            "the governed authority."
        )

    rows, fields = _read_sidecar(path)

    if len(rows) != EXPECTED_ROW_COUNT:
        raise RuntimeError(
            "MTG premium sidecar must contain exactly "
            f"{EXPECTED_ROW_COUNT} rows; found {len(rows)}."
        )

    if len(fields) != EXPECTED_FIELD_COUNT:
        raise RuntimeError(
            "MTG premium sidecar must contain exactly "
            f"{EXPECTED_FIELD_COUNT} fields; found {len(fields)}."
        )

    if tuple(fields) != EXPECTED_FIELDS:
        raise RuntimeError(
            "MTG premium sidecar field order/surface changed."
        )

    seen_asset_ids: set[str] = set()
    seen_secret_ids: set[str] = set()

    validated: list[dict[str, str]] = []

    for row_number, source_row in enumerate(
        rows,
        start=2,
    ):
        row = {
            field: str(
                source_row.get(field, "")
            )
            for field in EXPECTED_FIELDS
        }

        asset_id = row["mtg_asset_id"].strip()
        secret_id = row["secret_lair_id"].strip()

        if not asset_id:
            raise RuntimeError(
                f"Blank mtg_asset_id at row {row_number}."
            )

        if not secret_id:
            raise RuntimeError(
                f"Blank secret_lair_id at row {row_number}."
            )

        expected_asset_id = (
            f"{LANE}|{secret_id}"
        )

        if asset_id != expected_asset_id:
            raise RuntimeError(
                "MTG premium sidecar identity mapping changed at "
                f"row {row_number}: {asset_id!r}."
            )

        if asset_id in seen_asset_ids:
            raise RuntimeError(
                f"Duplicate mtg_asset_id: {asset_id}"
            )

        if secret_id in seen_secret_ids:
            raise RuntimeError(
                f"Duplicate secret_lair_id: {secret_id}"
            )

        seen_asset_ids.add(asset_id)
        seen_secret_ids.add(secret_id)

        if (
            row["source_authority_path"]
            != EXPECTED_SOURCE_AUTHORITY_PATH
        ):
            raise RuntimeError(
                "MTG premium source-authority path changed at "
                f"row {row_number}."
            )

        if (
            row["source_authority_sha256"]
            != EXPECTED_SOURCE_AUTHORITY_SHA256
        ):
            raise RuntimeError(
                "MTG premium source-authority SHA changed at "
                f"row {row_number}."
            )

        validated.append(row)

    if len(seen_asset_ids) != EXPECTED_ROW_COUNT:
        raise RuntimeError(
            "MTG premium asset identity population changed."
        )

    if len(seen_secret_ids) != EXPECTED_ROW_COUNT:
        raise RuntimeError(
            "MTG premium Secret Lair identity population changed."
        )

    return tuple(validated)


def project_premium_rows(
    rows: tuple[Mapping[str, Any], ...],
) -> list[PresentationRecord]:
    """Project already-validated source rows without recalculation."""

    records: list[PresentationRecord] = []

    for source_row in rows:
        payload = {
            field: source_row[field]
            for field in EXPECTED_FIELDS
        }

        asset_id = str(
            payload["mtg_asset_id"]
        )

        records.append(
            PresentationRecord(
                record_type=RECORD_TYPE,
                domain_id=DOMAIN_ID,
                asset_id=asset_id,
                record_key=asset_id,
                payload=payload,
            )
        )

    return records


def build_mtg_premium_records(
    sidecar_path: Path,
    *,
    mtg_head: str,
) -> list[PresentationRecord]:
    """
    Validate the exact external source artifact and project it.

    This function performs no database mutation, no model execution,
    no missing-value synthesis, and no recommendation recalculation.
    """

    rows = validate_certified_sidecar(
        sidecar_path,
        mtg_head=mtg_head,
    )

    records = project_premium_rows(rows)

    if len(records) != EXPECTED_ROW_COUNT:
        raise RuntimeError(
            "MTG premium presentation record count changed."
        )

    return records
