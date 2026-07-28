# Phase 8.2 — MTG Manual Production Integration

UIP now owns the complete manual MTG refresh transaction.

## Governed sequence

1. Run the MTG Phase 11E.17 production command.
2. Read `latest_mtg_uip_handoff.json`.
3. Validate the handoff contract, package location, interface version, safety flags, required files, and SHA-256 checksums.
4. Adapt the governed MTG delivery into Universal contract datasets.
5. Validate the Universal package through the existing import engine.
6. Import transactionally and synchronize the audit registry.
7. Only after a successful import, publish UIP-controlled MTG intelligence and dashboard datasets.

No UIP intelligence or dashboard output is changed when source execution, handoff validation, package validation, or import fails.

## Manual command

```powershell
cd C:\Users\DevonLockard\InvestmentPlatform
python scripts\run_mtg_manual_production_cycle.py --mtg-root C:\Users\DevonLockard\mtg-investment-terminal
```

To reconcile an already-produced Phase 11E.17 handoff without rerunning MTG collection:

```powershell
python scripts\run_mtg_manual_production_cycle.py --mtg-root C:\Users\DevonLockard\mtg-investment-terminal --skip-source-run
```

## UIP outputs

- `data\integration\mtg\latest\` — Universal import package
- `data\operations\uip_mtg\latest\mtg_intelligence.csv`
- `data\operations\uip_mtg\latest\mtg_dashboard.csv`
- `data\operations\uip_mtg\latest\publication_status.json`
- `data\operations\uip_mtg\last_successful_cycle.json`
