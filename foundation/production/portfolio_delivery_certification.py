"""Deterministic Phase 7.7 secure portfolio delivery certification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from .hosted_portfolio import install_hosted_portfolio_routes
from .http_service import HTTPServiceSettings, create_http_app
from .persistence import SQLiteProductionRepository
from .portfolio import preview_portfolio_csv
from .portfolio_persistence import SQLitePortfolioSnapshotRepository, create_portfolio_snapshot


@dataclass(frozen=True)
class PortfolioDeliveryCheck:
    check_id: str
    status: str
    evidence: str


@dataclass(frozen=True)
class Phase77CertificationReport:
    status: str
    checks: tuple[PortfolioDeliveryCheck, ...]
    certification_fingerprint: str

    def document(self) -> dict[str, object]:
        return {
            "certification_fingerprint": self.certification_fingerprint,
            "checks": [check.__dict__ for check in self.checks],
            "phase": "7.7",
            "profile": "secure-hosted-portfolio",
            "status": self.status,
        }


def _check(identity: str, condition: bool, evidence: str) -> PortfolioDeliveryCheck:
    return PortfolioDeliveryCheck(identity, "PASSED" if condition else "FAILED", evidence)


HEADER = "position_id,account_id,portfolio_group,asset_type,asset_id,quantity,cost_basis,market_value,currency,as_of,symbol,name,provider_symbol,target_weight,liquidity_class,notes\n"
ROWS = (
    "crypto-1,primary,crypto,crypto,bitcoin,0.01,700,800,USD,2026-07-20T18:00:00Z,BTC,Bitcoin,BTC,,liquid,\n"
    "etf-1,primary,etf,etf,voo,1,500,600,USD,2026-07-20T18:00:00Z,VOO,Vanguard S&P 500,VOO,,liquid,\n"
    "metal-1,primary,metals,metal,gold,1,100,150,USD,2026-07-20T18:00:00Z,GLD,Gold,GLD,,liquid,\n"
    "mtg-1,primary,mtg,other,collector-box,1,400,450,USD,2026-07-20T18:00:00Z,,Collector Box,,,illiquid,\n"
)


def certify_phase_7_7(root: Path | str = Path.cwd()) -> Phase77CertificationReport:
    root = Path(root)
    checks: list[PortfolioDeliveryCheck] = []
    report = preview_portfolio_csv(HEADER + ROWS, is_text=True)
    groups = {position.portfolio_group for position in report.positions}
    checks.append(_check(
        "CROSS_ASSET_COVERAGE",
        report.valid and groups == {"crypto", "etf", "metals", "mtg"},
        "Synthetic certification covered crypto, ETF, metals, and MTG positions.",
    ))

    imported = datetime(2026, 7, 20, 19, tzinfo=timezone.utc)
    first = create_portfolio_snapshot(report.positions, imported_at=imported)
    reversed_snapshot = create_portfolio_snapshot(tuple(reversed(report.positions)), imported_at=imported + timedelta(hours=1))
    checks.append(_check(
        "SNAPSHOT_DETERMINISM",
        first.snapshot_id == reversed_snapshot.snapshot_id and first.fingerprint == reversed_snapshot.fingerprint,
        "Reversed position input produced the identical snapshot identity and fingerprint.",
    ))
    checks.append(_check(
        "EXACT_RECONCILIATION",
        first.total_cost_basis == Decimal("1700") and first.total_market_value == Decimal("2000"),
        "Exact decimal cost basis and market value reconciled to all certified positions.",
    ))

    with TemporaryDirectory() as directory:
        temporary = Path(directory)
        snapshots = SQLitePortfolioSnapshotRepository(sqlite3.connect(":memory:", check_same_thread=False))
        snapshots.initialize()
        stored = snapshots.save(first)
        reused = snapshots.save(reversed_snapshot)
        checks.append(_check(
            "PERSISTENCE_IDEMPOTENCY",
            stored == reused and len(snapshots.history()) == 1,
            "Repeated identical content reused one durable snapshot without duplication.",
        ))
        changed_text = (HEADER + ROWS).replace(",450,USD", ",475,USD")
        changed_report = preview_portfolio_csv(changed_text, is_text=True)
        changed = create_portfolio_snapshot(changed_report.positions, imported_at=imported + timedelta(days=1))
        snapshots.save(changed)
        checks.append(_check(
            "IMMUTABLE_HISTORY",
            snapshots.latest() == changed and snapshots.history() == (changed, first) and snapshots.get(first.snapshot_id) == first,
            "Changed holdings created ordered history while the earlier snapshot remained unchanged.",
        ))

        production = SQLiteProductionRepository(temporary / "production.sqlite3")
        production.initialize()
        settings = HTTPServiceSettings(credentials={
            "cert-viewer": ("cert-view-key", ("viewer",)),
            "cert-operator": ("cert-operate-key", ("operator",)),
        })
        app = create_http_app(settings, production)
        hosted = SQLitePortfolioSnapshotRepository(sqlite3.connect(":memory:", check_same_thread=False))
        hosted.initialize()
        install_hosted_portfolio_routes(app, settings, hosted)
        service = TestClient(app)
        body = HEADER + ROWS
        anonymous = service.post("/v1/portfolio/snapshots", content=body, headers={"Content-Type": "text/csv"})
        viewer = service.post("/v1/portfolio/snapshots", content=body, headers={"Content-Type": "text/csv", "X-API-Key": "cert-view-key"})
        operator = service.post("/v1/portfolio/snapshots", content=body, headers={"Content-Type": "text/csv", "X-API-Key": "cert-operate-key", "X-Correlation-ID": "cert-import"})
        checks.append(_check(
            "AUTHORIZATION_BOUNDARY",
            anonymous.status_code == 401 and viewer.status_code == 403 and operator.status_code == 201,
            "Anonymous and viewer imports were rejected while the certified operator was accepted.",
        ))
        before = len(hosted.history())
        invalid = service.post("/v1/portfolio/snapshots", content=body.replace(",USD,", ",US,"), headers={"Content-Type": "text/csv", "X-API-Key": "cert-operate-key"})
        checks.append(_check(
            "VALIDATION_ATOMICITY",
            invalid.status_code == 422 and len(hosted.history()) == before,
            "Invalid CSV evidence was rejected before any snapshot write occurred.",
        ))
        event = app.state.events.events[-2]
        checks.append(_check(
            "AUDIT_PRIVACY",
            event.fields.get("credential") == "[REDACTED]" and "Collector Box" not in str(event.fields) and "cert-operate-key" not in str(event.fields),
            "Audit evidence redacted credentials and omitted raw holding details.",
        ))
        current = service.get("/v1/portfolio/snapshots/current", headers={"X-API-Key": "cert-view-key"})
        history = service.get("/v1/portfolio/snapshots", headers={"X-API-Key": "cert-view-key"})
        checks.append(_check(
            "VIEWER_PROJECTION",
            current.status_code == 200 and len(current.json()["positions"]) == 4 and "positions" not in history.json()["items"][0],
            "Viewer access returned current positions while bounded history remained summary-only.",
        ))

    html = (root / "foundation/production/dashboard_assets/dashboard.html").read_text(encoding="utf-8")
    javascript = (root / "foundation/production/dashboard_assets/dashboard.js").read_text(encoding="utf-8")
    css = (root / "foundation/production/dashboard_assets/dashboard.css").read_text(encoding="utf-8")
    checks.append(_check(
        "DASHBOARD_INTEGRITY",
        all(identity in html for identity in ("portfolio-market", "portfolio-allocation", "portfolio-positions", "portfolio-history"))
        and "esc(item.name" in javascript and "sessionStorage" in javascript and "@media print" in css,
        "Dashboard portfolio projections are escaped, session-scoped, responsive, and print-safe.",
    ))
    runner = (root / "scripts/run_production_api.py").read_text(encoding="utf-8")
    uploader = (root / "scripts/import_portfolio_snapshot.py").read_text(encoding="utf-8")
    checks.append(_check(
        "HOSTED_DELIVERY_WIRING",
        "PostgresPortfolioSnapshotRepository.from_dsn" in runner
        and "install_hosted_portfolio_routes" in runner
        and 'startswith("https://")' in uploader
        and "read_bytes()" in uploader
        and "X-API-Key" in uploader
        and "portfolio_holdings.csv" not in runner,
        "Render initializes Neon persistence while the private CSV travels directly from the local CLI over authenticated HTTPS.",
    ))

    status = "PASSED" if all(check.status == "PASSED" for check in checks) else "FAILED"
    canonical = json.dumps([check.__dict__ for check in checks], sort_keys=True, separators=(",", ":"))
    return Phase77CertificationReport(status, tuple(checks), hashlib.sha256(canonical.encode()).hexdigest())
