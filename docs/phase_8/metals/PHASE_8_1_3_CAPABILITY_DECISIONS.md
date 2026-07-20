# Phase 8.1.3 — Metals Capability Decision Matrix

## Outcome

The Metals v8 application will not be merged wholesale. Its 289-file live source tree contains valuable domain knowledge, but the universal platform already owns the cross-asset infrastructure.

The file-level inventory initially identified 110 archive candidates, 72 replacement candidates, 97 files requiring review, and 10 adaptation candidates. Human review narrowed reusable code to official-source parsers, Metals configuration, vehicle constraints, and canonical v8 export mappings.

The authoritative component decisions are recorded in `METALS_CAPABILITY_DECISION_MATRIX.csv`.

## Capabilities to implement

1. EIA uranium official benchmark provider.
2. World Bank monthly commodity benchmark provider.
3. Metals FRED series configuration using the existing universal FRED provider.
4. Metals vehicle catalog and underlying benchmark mapping.
5. Deterministic vehicle selection constraints:
   - minimum direct exposure;
   - maximum miner exposure;
   - maximum single-vehicle share.
6. Canonical v8 export gap analysis against the Phase 1 Metals adapter.
7. Domain regression fixtures for provider parsing and vehicle constraints.

## Capabilities explicitly superseded

The universal platform remains the owner of portfolio accounting, valuation, allocation, rebalancing, forecasting, confidence, decision intelligence, risk, backtesting, attribution, optimization, persistence, API delivery, dashboards, and reporting.

Legacy implementations of those capabilities are evidence for parity testing only. They are not production integration candidates.

## Provider findings

The universal platform already includes secret-safe FRED and Alpha Vantage providers. The legacy FRED collector therefore contributes series configuration rather than another HTTP implementation. The Yahoo Finance market-proxy collector is replaced by the universal quote provider path.

EIA uranium and World Bank commodity ingestion remain genuine gaps because they normalize official Metals-specific benchmarks not currently represented by the live provider layer.

## Vehicle findings

Generic metrics such as beta, Sharpe ratio, Sortino ratio, downside deviation, tracking error, and information ratio remain universal analytics. The legacy `spread_stability_score` is a constant placeholder and must not be migrated as intelligence.

The reusable vehicle capability is the constraint layer: direct exposure minimums, miner concentration limits, and single-vehicle caps. These rules must be extracted as pure deterministic logic without DuckDB, YAML root-path assumptions, or yfinance calls.

## Integration guardrails

- Do not copy the legacy database schema or migration chain.
- Do not restore retired module-level database APIs.
- Do not import backup, repair, patch, or historical runner files.
- Do not introduce a second FRED client.
- Do not treat yfinance as the universal production provider.
- Do not migrate generic analytics under a Metals namespace.
- Preserve source hashes and decision evidence for traceability.
- Require focused tests and full platform regression testing for each adapted capability.

## Planned sequence

1. Phase 8.1.4 — Canonical v8 export gap analysis.
2. Phase 8.2 — Metals official provider adapters.
3. Phase 8.3 — Metals vehicle constraint integration.
4. Phase 8.4 — Metals end-to-end parity and certification.
