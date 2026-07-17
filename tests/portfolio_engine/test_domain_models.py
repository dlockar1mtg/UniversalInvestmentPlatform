"""Tests for the Phase 2.1 universal portfolio domain."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from foundation.portfolio_engine.models import (
    Account,
    AccountType,
    AllocationTarget,
    AssetCategory,
    Portfolio,
    Transaction,
    TransactionType,
)
from foundation.portfolio_engine.validation import validate_portfolio_configuration


ROOT = Path(__file__).resolve().parents[2]


def test_portfolio_accepts_monthly_contribution() -> None:
    portfolio = Portfolio(
        name="Universal Portfolio",
        monthly_contribution=Decimal("3000.00"),
    )
    assert portfolio.monthly_contribution == Decimal("3000.00")
    assert portfolio.base_currency == "USD"


def test_account_requires_institution() -> None:
    with pytest.raises(ValueError, match="Institution"):
        Account(
            portfolio_id=uuid4(),
            name="Brokerage",
            institution=" ",
            account_type=AccountType.BROKERAGE,
        )


def test_buy_transaction_requires_asset_and_quantity() -> None:
    with pytest.raises(ValueError, match="asset_id"):
        Transaction(
            portfolio_id=uuid4(),
            account_id=uuid4(),
            transaction_type=TransactionType.BUY,
            transaction_at=datetime.now(timezone.utc),
            amount=Decimal("100"),
            quantity=Decimal("1"),
        )


def test_allocation_target_requires_valid_band() -> None:
    with pytest.raises(ValueError, match="inside"):
        AllocationTarget(
            portfolio_id=uuid4(),
            category=AssetCategory.CRYPTO,
            target_weight=Decimal("0.33"),
            minimum_weight=Decimal("0.40"),
            maximum_weight=Decimal("0.50"),
        )


def test_default_configuration_is_valid() -> None:
    result = validate_portfolio_configuration(ROOT / "config" / "portfolios")
    assert result.errors == []
    assert result.is_valid
