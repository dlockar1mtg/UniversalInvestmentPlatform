"""Strict, deterministic CSV portfolio ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import csv
import hashlib
import io
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

REQUIRED_COLUMNS = (
    "position_id", "account_id", "portfolio_group", "asset_type", "asset_id",
    "quantity", "cost_basis", "market_value", "currency", "as_of",
)
OPTIONAL_COLUMNS = (
    "symbol", "name", "provider_symbol", "target_weight", "liquidity_class", "notes",
)
PORTFOLIO_GROUPS = frozenset({"crypto", "etf", "metals", "mtg"})
ASSET_TYPES = frozenset({"crypto", "equity", "etf", "metal", "mortgage", "cash", "other"})


@dataclass(frozen=True)
class PortfolioPosition:
    position_id: str
    account_id: str
    portfolio_group: str
    asset_type: str
    asset_id: str
    quantity: Decimal
    cost_basis: Decimal
    market_value: Decimal
    currency: str
    as_of: datetime
    symbol: str = ""
    name: str = ""
    provider_symbol: str = ""
    target_weight: Decimal | None = None
    liquidity_class: str = ""
    notes: str = ""

    def canonical(self) -> Mapping[str, str | None]:
        return MappingProxyType({
            "position_id": self.position_id,
            "account_id": self.account_id,
            "portfolio_group": self.portfolio_group,
            "asset_type": self.asset_type,
            "asset_id": self.asset_id,
            "quantity": str(self.quantity),
            "cost_basis": str(self.cost_basis),
            "market_value": str(self.market_value),
            "currency": self.currency,
            "as_of": self.as_of.isoformat(),
            "symbol": self.symbol,
            "name": self.name,
            "provider_symbol": self.provider_symbol,
            "target_weight": None if self.target_weight is None else str(self.target_weight),
            "liquidity_class": self.liquidity_class,
            "notes": self.notes,
        })


@dataclass(frozen=True)
class PortfolioCSVError:
    row_number: int
    field: str
    message: str


@dataclass(frozen=True)
class PortfolioImportReport:
    positions: tuple[PortfolioPosition, ...]
    errors: tuple[PortfolioCSVError, ...]
    fingerprint: str

    @property
    def valid(self) -> bool:
        return not self.errors


class PortfolioCSVValidationError(ValueError):
    def __init__(self, report: PortfolioImportReport):
        self.report = report
        super().__init__(f"portfolio CSV contains {len(report.errors)} validation error(s)")


def _decimal(value: str, field: str, row: int, errors: list[PortfolioCSVError], *, optional: bool = False) -> Decimal | None:
    value = value.strip()
    if optional and not value:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        errors.append(PortfolioCSVError(row, field, "must be a decimal number"))
        return None
    if not parsed.is_finite() or parsed < 0:
        errors.append(PortfolioCSVError(row, field, "must be a finite non-negative number"))
        return None
    return parsed


def preview_portfolio_csv(source: str | Path, *, is_text: bool = False) -> PortfolioImportReport:
    text = str(source) if is_text else Path(source).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    errors: list[PortfolioCSVError] = []
    positions: list[PortfolioPosition] = []
    headers = tuple(reader.fieldnames or ())
    missing = [name for name in REQUIRED_COLUMNS if name not in headers]
    unknown = [name for name in headers if name not in REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
    for name in missing:
        errors.append(PortfolioCSVError(1, name, "required column is missing"))
    for name in unknown:
        errors.append(PortfolioCSVError(1, name, "unknown column"))
    if len(headers) != len(set(headers)):
        errors.append(PortfolioCSVError(1, "header", "duplicate column name"))
    if errors:
        return _report(positions, errors)

    seen: set[str] = set()
    for row_number, raw in enumerate(reader, start=2):
        row_errors: list[PortfolioCSVError] = []
        values = {key: (raw.get(key) or "").strip() for key in REQUIRED_COLUMNS + OPTIONAL_COLUMNS}
        for name in ("position_id", "account_id", "portfolio_group", "asset_type", "asset_id", "currency", "as_of"):
            if not values[name]:
                row_errors.append(PortfolioCSVError(row_number, name, "is required"))
        position_id = values["position_id"]
        if position_id in seen:
            row_errors.append(PortfolioCSVError(row_number, "position_id", "must be unique"))
        seen.add(position_id)
        group = values["portfolio_group"].lower()
        asset_type = values["asset_type"].lower()
        if group and group not in PORTFOLIO_GROUPS:
            row_errors.append(PortfolioCSVError(row_number, "portfolio_group", "must be crypto, etf, metals, or mtg"))
        if asset_type and asset_type not in ASSET_TYPES:
            row_errors.append(PortfolioCSVError(row_number, "asset_type", "is not supported"))
        currency = values["currency"].upper()
        if currency and (len(currency) != 3 or not currency.isalpha()):
            row_errors.append(PortfolioCSVError(row_number, "currency", "must be a three-letter ISO code"))
        quantity = _decimal(values["quantity"], "quantity", row_number, row_errors)
        cost_basis = _decimal(values["cost_basis"], "cost_basis", row_number, row_errors)
        market_value = _decimal(values["market_value"], "market_value", row_number, row_errors)
        target = _decimal(values["target_weight"], "target_weight", row_number, row_errors, optional=True)
        if target is not None and target > 1:
            row_errors.append(PortfolioCSVError(row_number, "target_weight", "must be between 0 and 1"))
        try:
            as_of = datetime.fromisoformat(values["as_of"].replace("Z", "+00:00"))
            if as_of.tzinfo is None:
                raise ValueError
        except ValueError:
            as_of = datetime.min
            row_errors.append(PortfolioCSVError(row_number, "as_of", "must be an ISO-8601 timestamp with timezone"))
        errors.extend(row_errors)
        if not row_errors:
            positions.append(PortfolioPosition(
                position_id, values["account_id"], group, asset_type, values["asset_id"],
                quantity or Decimal(0), cost_basis or Decimal(0), market_value or Decimal(0),
                currency, as_of, values["symbol"].upper(), values["name"],
                values["provider_symbol"].upper(), target, values["liquidity_class"], values["notes"],
            ))
    return _report(positions, errors)


def _report(positions: list[PortfolioPosition], errors: list[PortfolioCSVError]) -> PortfolioImportReport:
    ordered = tuple(sorted(positions, key=lambda item: item.position_id))
    payload = [dict(item.canonical()) for item in ordered]
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return PortfolioImportReport(ordered, tuple(errors), fingerprint)


def import_portfolio_csv(source: str | Path, *, is_text: bool = False) -> tuple[PortfolioPosition, ...]:
    report = preview_portfolio_csv(source, is_text=is_text)
    if not report.valid:
        raise PortfolioCSVValidationError(report)
    return report.positions
