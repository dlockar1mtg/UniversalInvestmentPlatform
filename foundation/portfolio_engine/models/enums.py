"""Enumerations used by the Universal Portfolio Engine."""

from __future__ import annotations

from enum import StrEnum


class PortfolioStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class AccountType(StrEnum):
    BROKERAGE = "brokerage"
    RETIREMENT = "retirement"
    CRYPTO_EXCHANGE = "crypto_exchange"
    CRYPTO_WALLET = "crypto_wallet"
    COLLECTIBLES = "collectibles"
    ROBO_ADVISOR = "robo_advisor"
    BANK = "bank"
    TREASURY = "treasury"
    OTHER = "other"


class AssetCategory(StrEnum):
    CRYPTO = "crypto"
    MTG = "mtg"
    METALS = "metals"
    ACORNS = "acorns"
    STOCKS_ETFS = "stocks_etfs"
    CASH = "cash"
    HOUSING = "housing"
    OTHER = "other"


class TransactionType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    DIVIDEND = "dividend"
    DISTRIBUTION = "distribution"
    INTEREST = "interest"
    FEE = "fee"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    VALUATION_ADJUSTMENT = "valuation_adjustment"


class ValuationSource(StrEnum):
    MARKET = "market"
    PLATFORM = "platform"
    MANUAL = "manual"
    MODEL = "model"
    APPRAISAL = "appraisal"


class ValuationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class LiquidityTier(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ILLIQUID = "illiquid"
    UNKNOWN = "unknown"


class RebalanceMethod(StrEnum):
    CONTRIBUTION_ONLY = "contribution_only"
    THRESHOLD = "threshold"
    SCHEDULED = "scheduled"
    RISK_TRIGGERED = "risk_triggered"
    LIQUIDITY_AWARE = "liquidity_aware"
