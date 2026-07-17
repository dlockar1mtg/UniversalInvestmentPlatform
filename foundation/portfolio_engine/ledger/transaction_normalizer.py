"""Normalize imported rows into universal ledger entries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from foundation.portfolio_engine.models import AssetCategory, TransactionType

from .ledger_entry import LedgerEntry


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_decimal(value: Any, default: str = "0") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    return Decimal(str(value).replace(",", "").replace("$", "").strip())


def normalize_row(
    row: dict[str, Any],
    *,
    portfolio_id: UUID,
    account_id: UUID,
    import_run_id: UUID | None = None,
    source_file: str | None = None,
) -> LedgerEntry:
    transaction_type = TransactionType(str(row["transaction_type"]).strip().lower())
    gross_amount = parse_decimal(row.get("gross_amount", row.get("amount", 0)))
    fees = parse_decimal(row.get("fees", 0))

    if row.get("net_amount") not in (None, ""):
        net_amount = parse_decimal(row["net_amount"])
    elif transaction_type in {
        TransactionType.BUY,
        TransactionType.WITHDRAWAL,
        TransactionType.FEE,
        TransactionType.TRANSFER_OUT,
    }:
        net_amount = -(gross_amount + fees)
    elif transaction_type in {
        TransactionType.SELL,
        TransactionType.DEPOSIT,
        TransactionType.DIVIDEND,
        TransactionType.DISTRIBUTION,
        TransactionType.INTEREST,
        TransactionType.TRANSFER_IN,
    }:
        net_amount = gross_amount - fees
    else:
        net_amount = parse_decimal(row.get("net_amount", 0))

    metadata_value = row.get("metadata", row.get("metadata_json", {}))
    if isinstance(metadata_value, str):
        metadata = json.loads(metadata_value) if metadata_value.strip() else {}
    else:
        metadata = dict(metadata_value or {})

    category_value = str(row.get("asset_category", "")).strip().lower()
    category = AssetCategory(category_value) if category_value else None

    return LedgerEntry(
        portfolio_id=portfolio_id,
        account_id=account_id,
        transaction_type=transaction_type,
        effective_at=parse_datetime(row["effective_at"]),
        gross_amount=gross_amount,
        net_amount=net_amount,
        currency=str(row.get("currency", "USD")),
        asset_id=str(row.get("asset_id", "")).strip() or None,
        asset_name=str(row.get("asset_name", "")).strip() or None,
        asset_category=category,
        quantity=(
            None
            if row.get("quantity") in (None, "")
            else parse_decimal(row.get("quantity"))
        ),
        unit_price=(
            None
            if row.get("unit_price") in (None, "")
            else parse_decimal(row.get("unit_price"))
        ),
        fees=fees,
        source_platform=str(row.get("source_platform", "")).strip() or None,
        source_file=source_file or str(row.get("source_file", "")).strip() or None,
        source_record_id=str(row.get("source_record_id", "")).strip() or None,
        import_run_id=import_run_id,
        metadata=metadata,
    )
