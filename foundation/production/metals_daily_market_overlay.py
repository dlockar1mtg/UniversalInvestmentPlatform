"""Daily Metals market overlay, divergence analytics, and execution-quality scoring."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class DailyMarketObservation:
    ticker: str
    trading_date: str
    close_price: float
    previous_close_price: float
    benchmark_symbol: str
    benchmark_close_price: float
    benchmark_previous_close_price: float
    expense_ratio_pct: float
    average_daily_volume_shares: float
    median_bid_ask_spread_pct: float
    metadata_as_of_date: str


@dataclass(frozen=True)
class DailyMarketOverlayRow:
    ticker: str
    trading_date: str
    close_price: float
    daily_return_pct: float
    benchmark_symbol: str
    benchmark_daily_return_pct: float
    divergence_pct: float
    annual_expense_drag_pct: float
    daily_expense_drag_pct: float
    expense_adjusted_divergence_pct: float
    median_bid_ask_spread_pct: float
    average_daily_volume_shares: float
    execution_quality_score: float
    freshness_status: str
    divergence_status: str
    alert_severity: str


def _pct_change(current: float, previous: float) -> float:
    if current <= 0 or previous <= 0:
        raise ValueError("prices must be positive")
    return (current / previous - 1.0) * 100.0


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _execution_quality(volume: float, spread_pct: float) -> float:
    volume_score = min(max(volume / 5_000_000.0, 0.0), 1.0) * 60.0
    spread_score = max(0.0, 1.0 - min(spread_pct / 1.0, 1.0)) * 40.0
    return round(volume_score + spread_score, 2)


def _freshness_status(trading_date: str, metadata_as_of_date: str, *, as_of: date) -> str:
    market_age = (as_of - _parse_date(trading_date)).days
    metadata_age = (as_of - _parse_date(metadata_as_of_date)).days
    if market_age < 0 or metadata_age < 0:
        return "FUTURE_DATED"
    if market_age <= 3 and metadata_age <= 30:
        return "CURRENT"
    if market_age <= 7 and metadata_age <= 60:
        return "AGING"
    return "STALE"


def _divergence_status(value: float) -> tuple[str, str]:
    magnitude = abs(value)
    if magnitude >= 3.0:
        return "EXTREME", "CRITICAL"
    if magnitude >= 1.5:
        return "ELEVATED", "WARNING"
    return "NORMAL", "INFO"


def build_daily_market_overlay(
    observations: Iterable[DailyMarketObservation],
    *,
    as_of: date,
) -> tuple[DailyMarketOverlayRow, ...]:
    rows: list[DailyMarketOverlayRow] = []
    for item in observations:
        vehicle_return = _pct_change(item.close_price, item.previous_close_price)
        benchmark_return = _pct_change(item.benchmark_close_price, item.benchmark_previous_close_price)
        divergence = vehicle_return - benchmark_return
        daily_expense_drag = item.expense_ratio_pct / 365.0
        adjusted = divergence + daily_expense_drag
        divergence_status, severity = _divergence_status(adjusted)
        freshness = _freshness_status(item.trading_date, item.metadata_as_of_date, as_of=as_of)
        if freshness in {"STALE", "FUTURE_DATED"}:
            severity = "CRITICAL"
        elif freshness == "AGING" and severity == "INFO":
            severity = "WARNING"
        rows.append(
            DailyMarketOverlayRow(
                ticker=item.ticker,
                trading_date=item.trading_date,
                close_price=round(item.close_price, 6),
                daily_return_pct=round(vehicle_return, 6),
                benchmark_symbol=item.benchmark_symbol,
                benchmark_daily_return_pct=round(benchmark_return, 6),
                divergence_pct=round(divergence, 6),
                annual_expense_drag_pct=round(item.expense_ratio_pct, 6),
                daily_expense_drag_pct=round(daily_expense_drag, 8),
                expense_adjusted_divergence_pct=round(adjusted, 6),
                median_bid_ask_spread_pct=round(item.median_bid_ask_spread_pct, 6),
                average_daily_volume_shares=round(item.average_daily_volume_shares, 2),
                execution_quality_score=_execution_quality(
                    item.average_daily_volume_shares,
                    item.median_bid_ask_spread_pct,
                ),
                freshness_status=freshness,
                divergence_status=divergence_status,
                alert_severity=severity,
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.benchmark_symbol, -row.execution_quality_score, row.ticker)))


def summarize_daily_market_overlay(rows: Iterable[DailyMarketOverlayRow]) -> dict[str, object]:
    materialized = tuple(rows)
    severity_rank = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}
    highest = max((row.alert_severity for row in materialized), key=lambda value: severity_rank[value], default="INFO")
    return {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "vehicle_count": len(materialized),
        "current_vehicle_count": sum(row.freshness_status == "CURRENT" for row in materialized),
        "alert_count": sum(row.alert_severity != "INFO" for row in materialized),
        "critical_alert_count": sum(row.alert_severity == "CRITICAL" for row in materialized),
        "highest_alert_severity": highest,
        "status": "PASS" if highest == "INFO" else ("WARNING" if highest == "WARNING" else "FAIL"),
    }


def write_daily_market_overlay_outputs(
    rows: Iterable[DailyMarketOverlayRow],
    summary: Mapping[str, object],
    output_root: Path,
) -> None:
    materialized = tuple(rows)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "current_overlay.json").write_text(
        json.dumps([asdict(row) for row in materialized], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_root / "overlay_summary.json").write_text(
        json.dumps(dict(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with (output_root / "current_overlay.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(asdict(materialized[0]).keys()) if materialized else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            for row in materialized:
                writer.writerow(asdict(row))
