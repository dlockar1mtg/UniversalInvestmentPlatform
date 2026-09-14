"""Project the ten certified UIP-native Metals rich sidecars into presentation records.

This module performs no discovery and no persistence. The caller supplies an explicit
Metals production-artifact root. Each family must independently pass the same certified
source contract used by the rich-publication recovery gate before any rows are projected.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from foundation.presentation.metals_identity_bridge import canonical_presentation_asset_id
from foundation.presentation.publication_model import PresentationRecord
from scripts.audit_rich_publication_source_contract import (
    NATIVE_METALS_CERTIFIED_CONTRACTS,
    audit_certified_metals_family,
)

DOMAIN_ID = "metals"

FAMILY_PROJECTION = {
    "current_price": {
        "record_type": "metals_current_price",
        "asset_field": "asset_id",
        "key_fields": ("asset_id",),
    },
    "price_history": {
        "record_type": "metals_price_history",
        "asset_field": "asset_id",
        "key_fields": ("asset_id", "observation_date", "source_run_id"),
    },
    "data_freshness": {
        "record_type": "metals_data_freshness",
        "asset_field": "series_key",
        "key_fields": ("series_key",),
    },
    "platform_health": {
        "record_type": "metals_platform_health",
        "asset_field": None,
        "key_fields": ("decision_run_id",),
    },
    "model_component": {
        "record_type": "metals_model_component",
        "asset_field": "metal",
        "key_fields": ("forecast_run_id", "metal", "horizon_months", "model_name"),
    },
    "risk": {
        "record_type": "risk",
        "asset_field": "universal_asset_id",
        "key_fields": ("universal_asset_id",),
    },
    "recommendation_change": {
        "record_type": "metals_recommendation_change",
        "asset_field": "universal_asset_id",
        "key_fields": ("universal_asset_id", "evaluation_date"),
    },
    "regime_probability": {
        "record_type": "metals_regime_probability",
        "asset_field": "universal_asset_id",
        "key_fields": ("universal_asset_id", "as_of_date", "regime"),
    },
    "uncertainty_adjusted": {
        "record_type": "metals_uncertainty_adjusted",
        "asset_field": "universal_asset_id",
        "key_fields": ("universal_asset_id", "as_of_date", "horizon_months"),
    },
    "tactical_state": {
        "record_type": "tactical_state",
        "asset_field": "universal_asset_id",
        "key_fields": ("universal_asset_id",),
    },
}

EXPECTED_FAMILIES = frozenset(FAMILY_PROJECTION)


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"Certified Metals rich CSV is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _record_key(row: dict[str, str], fields: tuple[str, ...], family: str) -> str:
    values: list[str] = []
    for field in fields:
        value = str(row.get(field, "")).strip()
        if not value:
            raise RuntimeError(f"Blank key field {field!r} in certified Metals family {family!r}")
        values.append(value)
    return "|".join(values)


def build_metals_rich_records(artifact_root: Path) -> list[PresentationRecord]:
    """Validate and project exactly the ten certified Metals rich families."""
    root = artifact_root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"Metals artifact root is missing: {root}")

    if set(NATIVE_METALS_CERTIFIED_CONTRACTS) != EXPECTED_FAMILIES:
        raise RuntimeError(
            "Metals rich projection family set no longer matches the certified source contract"
        )

    records: list[PresentationRecord] = []
    seen: set[tuple[str, str]] = set()

    for family in sorted(EXPECTED_FAMILIES):
        spec = NATIVE_METALS_CERTIFIED_CONTRACTS[family]
        audit = audit_certified_metals_family(root, family, spec)
        if not audit.get("pass"):
            raise RuntimeError(f"Certified Metals family failed projection preflight: {family}: {audit}")

        projection = FAMILY_PROJECTION[family]
        csv_path = root / str(spec["csv"])
        rows = _read_rows(csv_path)
        if len(rows) != int(audit["rows"]):
            raise RuntimeError(f"Metals family row count changed after validation: {family}")

        for row in rows:
            record_type = str(projection["record_type"])
            key = _record_key(row, tuple(projection["key_fields"]), family)
            identity = (record_type, key)
            if identity in seen:
                raise RuntimeError(f"Duplicate projected Metals rich record: {identity}")
            seen.add(identity)

            asset_field = projection["asset_field"]
            source_asset_id = None if asset_field is None else str(row.get(str(asset_field), "")).strip()
            if asset_field is not None and not source_asset_id:
                raise RuntimeError(f"Blank asset identity in certified Metals family {family!r}")
            asset_id = (
                None
                if source_asset_id is None
                else canonical_presentation_asset_id(family, source_asset_id)
            )

            payload: dict[str, Any] = dict(row)
            payload.update(
                {
                    "_rich_source_family": family,
                    "_rich_source_csv_sha256": audit["sha256"],
                    "_rich_source_manifest_status": audit["manifest_status"],
                    "_rich_source_manifest_authority": audit["manifest_authority"],
                }
            )
            if source_asset_id is not None and asset_id != source_asset_id:
                payload["_rich_source_asset_id"] = source_asset_id
                payload["_presentation_asset_id"] = asset_id
            if family == "tactical_state" and row.get("dominant_regime"):
                payload["candidate_regime"] = row["dominant_regime"]
                payload["_presentation_schema_alias"] = "candidate_regime<-dominant_regime"
            records.append(
                PresentationRecord(
                    record_type=record_type,
                    domain_id=DOMAIN_ID,
                    asset_id=asset_id,
                    record_key=key,
                    payload=payload,
                )
            )

    return records
