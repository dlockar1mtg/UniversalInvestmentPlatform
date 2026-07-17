"""Deterministic audit hashing for portfolio ledger entries."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID


AUDIT_FIELDS = (
    "portfolio_id",
    "account_id",
    "asset_id",
    "asset_name",
    "asset_category",
    "transaction_type",
    "effective_at",
    "quantity",
    "unit_price",
    "gross_amount",
    "fees",
    "net_amount",
    "currency",
    "source_platform",
    "source_file",
    "source_record_id",
    "reversal_of_entry_id",
)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def canonical_audit_payload(entry: Any) -> dict[str, Any]:
    return {
        field: _canonical_value(getattr(entry, field, None))
        for field in AUDIT_FIELDS
    }


def calculate_audit_hash(entry: Any) -> str:
    payload = json.dumps(
        canonical_audit_payload(entry),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_audit_hash(entry: Any) -> bool:
    return bool(getattr(entry, "audit_hash", None)) and (
        entry.audit_hash == calculate_audit_hash(entry)
    )
