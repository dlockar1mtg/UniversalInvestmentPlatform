"""Build calculated positions from append-only ledger entries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from foundation.portfolio_engine.ledger import LedgerEntry
from foundation.portfolio_engine.models import AssetCategory, LiquidityTier, TransactionType

from .cost_basis import CostBasisState, apply_buy, apply_sell


@dataclass(slots=True)
class DerivedPosition:
    portfolio_id: UUID
    account_id: UUID
    asset_id: str
    asset_name: str
    asset_category: AssetCategory
    quantity: Decimal
    cost_basis: Decimal
    average_unit_cost: Decimal
    realized_gain_loss: Decimal
    currency: str
    liquidity_tier: LiquidityTier
    as_of: datetime


def _default_liquidity(category: AssetCategory) -> LiquidityTier:
    if category in {
        AssetCategory.CRYPTO,
        AssetCategory.METALS,
        AssetCategory.STOCKS_ETFS,
        AssetCategory.ACORNS,
        AssetCategory.CASH,
    }:
        return LiquidityTier.DAILY
    if category == AssetCategory.MTG:
        return LiquidityTier.ILLIQUID
    if category == AssetCategory.HOUSING:
        return LiquidityTier.ILLIQUID
    return LiquidityTier.UNKNOWN


def build_positions(
    entries: Iterable[LedgerEntry],
    *,
    as_of: datetime | None = None,
) -> list[DerivedPosition]:
    cutoff = as_of or datetime.now(timezone.utc)
    states: dict[tuple[UUID, UUID, str, str], CostBasisState] = defaultdict(CostBasisState)
    metadata: dict[tuple[UUID, UUID, str, str], tuple[str, AssetCategory]] = {}

    rows = sorted(
        (
            entry
            for entry in entries
            if entry.entry_status.value == "posted"
            and entry.asset_id
            and entry.effective_at <= cutoff
        ),
        key=lambda entry: (entry.effective_at, entry.recorded_at, str(entry.ledger_entry_id)),
    )

    for entry in rows:
        key = (
            entry.portfolio_id,
            entry.account_id,
            entry.asset_id,
            entry.currency,
        )
        category = entry.asset_category or AssetCategory.OTHER
        metadata[key] = (entry.asset_name or entry.asset_id, category)
        state = states[key]

        if entry.transaction_type == TransactionType.BUY:
            states[key] = apply_buy(
                state,
                quantity=entry.quantity or Decimal("0"),
                gross_amount=entry.gross_amount,
                fees=entry.fees,
            )
        elif entry.transaction_type == TransactionType.SELL:
            states[key] = apply_sell(
                state,
                quantity=entry.quantity or Decimal("0"),
                gross_amount=entry.gross_amount,
                fees=entry.fees,
            )
        elif entry.transaction_type == TransactionType.TRANSFER_IN:
            quantity = entry.quantity or Decimal("0")
            if quantity > 0:
                transfer_basis = Decimal(str(entry.metadata.get("transferred_cost_basis", "0")))
                states[key] = CostBasisState(
                    quantity=state.quantity + quantity,
                    cost_basis=state.cost_basis + transfer_basis,
                    realized_gain_loss=state.realized_gain_loss,
                )
        elif entry.transaction_type == TransactionType.TRANSFER_OUT:
            quantity = entry.quantity or Decimal("0")
            if quantity > state.quantity:
                raise ValueError(
                    f"Transfer-out quantity exceeds holdings for {entry.asset_id}."
                )
            removed_basis = state.average_unit_cost * quantity
            remaining_quantity = state.quantity - quantity
            states[key] = CostBasisState(
                quantity=remaining_quantity,
                cost_basis=Decimal("0") if remaining_quantity == 0 else state.cost_basis - removed_basis,
                realized_gain_loss=state.realized_gain_loss,
            )

    positions: list[DerivedPosition] = []
    for key, state in states.items():
        if state.quantity <= 0:
            continue
        portfolio_id, account_id, asset_id, currency = key
        asset_name, category = metadata[key]
        positions.append(
            DerivedPosition(
                portfolio_id=portfolio_id,
                account_id=account_id,
                asset_id=asset_id,
                asset_name=asset_name,
                asset_category=category,
                quantity=state.quantity,
                cost_basis=state.cost_basis,
                average_unit_cost=state.average_unit_cost,
                realized_gain_loss=state.realized_gain_loss,
                currency=currency,
                liquidity_tier=_default_liquidity(category),
                as_of=cutoff,
            )
        )

    return sorted(
        positions,
        key=lambda position: (
            str(position.portfolio_id),
            str(position.account_id),
            position.asset_id,
        ),
    )
