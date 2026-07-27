# Phase 11 — Cross-Domain Automation Readiness

## Purpose

Phase 11 certifies that Metals, Crypto, and MTG can collect current data, run
their production intelligence pipelines, publish durable outputs, and hand
validated packages to the Universal Investment Platform.

## Large-block implementation

### 11A — Domain scheduling

- Metals daily hosted production
- Crypto daily incremental production
- Crypto weekly full refresh
- MTG daily marketplace production
- MTG weekly full-universe refresh

### 11B — Automation readiness audit

Run:

```powershell
python .\scripts\audit_cross_domain_automation.py
```

Strict mode:

```powershell
python .\scripts\audit_cross_domain_automation.py --strict
```

Outputs:

```text
data/operations/phase_11/automation_inventory.csv
data/operations/phase_11/automation_gap_register.csv
data/operations/phase_11/automation_readiness.json
```

## Known MTG delivery gap

MTG has a certified universal export package, but scheduled marketplace
production does not yet produce and publish that package. The existing export
also depends on Phase 10.9 certified artifacts and currently publishes
`portfolio_summary.csv` rather than the standard `portfolio_positions.csv`.

This gap must be closed before the UIP can automatically ingest MTG alongside
Metals and Crypto.

## MTG Hosted Delivery Alignment

Phase 11C established a checksum-governed MTG hosted baseline and a clean-runner
UIP delivery builder. The scheduled marketplace production workflow now builds
and uploads the standard MTG UIP contract, including:

- `asset_master.csv`
- `forecasts.csv`
- `recommendations.csv`
- `risk_metrics.csv`
- `portfolio_positions.csv`
- `platform_status.csv`
- `diagnostics.csv`
- `package_summary.json`

The hosted foundation contains 1,141 governed products across Secret Lair,
Collector Booster Box, and Pre-Collector Booster Box lanes. Position-level
holdings remain privacy-protected; the standard positions file is currently
published with its governed schema and zero private rows.

The readiness contract now treats MTG delivery as required and recognizes
`data/operations/mtg_uip_delivery/` as the production delivery location.
