# Phase 8.9.2 — Metals Operations Visibility

## Objective

Turn the durable Phase 8.9.1 cycle evidence into current and historical operational datasets suitable for dashboards, health panels, alerting, and audit review.

## Outputs

A successful Metals production cycle now publishes:

- `data/operations/metals/visibility/current_snapshot.json`
- `data/operations/metals/visibility/current_snapshot.csv`
- `data/operations/metals/visibility/alerts.json`
- `data/operations/metals/visibility/alerts.csv`
- `data/operations/metals/visibility/cycle_history.csv`
- `data/operations/metals/visibility/stage_history.csv`

These remain runtime outputs and are ignored by Git.

## Current snapshot

The current snapshot contains:

- cycle ID and status;
- start, completion, and runtime;
- package ID and import ID;
- data-as-of date;
- owner and notification destination;
- readiness status and component count;
- package age and package warning/error counts;
- provider, bridge, model-parity, registry, and vehicle-constraint status;
- EIA, World Bank, provider, bridge, and parity record counts;
- alert count and highest severity.

## Historical datasets

`cycle_history.csv` contains one row per durable production cycle.

`stage_history.csv` contains one row per stage per cycle, allowing dashboard analysis of:

- stage duration;
- failures by stage;
- runtime trends;
- return codes;
- cycle-to-cycle operational performance.

## Alert model

Severity levels are:

- `INFO`: healthy; no actionable alert;
- `WARNING`: degradation requiring review but not immediate shutdown;
- `CRITICAL`: failed or invalid evidence that should block a production-ready status.

Critical conditions include:

- failed cycle;
- failed required stage;
- missing package ID;
- missing import ID;
- failed readiness gate;
- failed readiness component;
- package beyond the critical freshness threshold;
- future-dated cycle evidence;
- recorded cycle errors.

Warning conditions include:

- package beyond the warning freshness threshold;
- recorded cycle warnings.

## Execution

The normal Windows runner performs the production cycle and visibility publication together:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\run_metals_production_cycle.ps1
```

Visibility may also be republished without another provider or import cycle:

```powershell
python scripts\publish_metals_operations_visibility.py
```

## Failure behavior

The visibility publisher returns a nonzero exit code when:

- latest cycle evidence is missing;
- latest readiness evidence is missing;
- the resulting snapshot contains a critical alert.

The PowerShell production runner propagates that nonzero exit code.

## Test scope

Focused regression tests cover:

- healthy snapshots;
- stale-package critical alerts;
- missing import evidence;
- failed readiness components;
- cycle and stage history projection;
- JSON and CSV publication helpers.

## Definition of done

Phase 8.9.2 is complete when:

1. focused tests pass;
2. production tests pass;
3. full-platform tests pass;
4. a live cycle publishes all visibility files;
5. the healthy live snapshot reports `INFO`, zero alerts, and all readiness components passing;
6. cycle and stage history contain the live run;
7. the repository remains clean because runtime outputs are ignored.
