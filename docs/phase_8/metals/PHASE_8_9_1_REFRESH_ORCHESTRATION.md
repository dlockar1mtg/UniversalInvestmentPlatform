# Phase 8.9.1 — Metals Refresh Orchestration

## Objective

Provide one fail-closed production-cycle command that executes the supported Metals export, transactional import, and production-readiness gate while preserving durable machine-readable evidence.

## Canonical Windows command

```powershell
cd C:\Users\DevonLockard\InvestmentPlatform

powershell -ExecutionPolicy Bypass -File .\scripts\run_metals_production_cycle.ps1
```

The PowerShell runner defaults to:

```text
Metals source: C:\Users\DevonLockard\metals
Owner: Devon Lockard
Notification destination: local-console
```

## Diagnostic commands

Run without rebuilding the package:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_metals_production_cycle.ps1 -SkipExport
```

Run without live external-provider calls for offline diagnostics only:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_metals_production_cycle.ps1 -SkipExport -SkipLiveProviders
```

Skipping live providers is not valid for production certification.

## Required stage order

1. Universal Metals export, unless explicitly skipped.
2. Transactional universal import using the new package.
3. Production-readiness evaluation, including live official providers by default.
4. Operations-status JSON and CSV publication.

Any nonzero exit code from a required stage stops the cycle and causes the overall command to return a nonzero exit code.

## Durable evidence

Each cycle writes records under:

```text
data/operations/metals/cycle_history/
```

Files include:

- `<cycle_id>.json` — immutable per-cycle evidence;
- `latest.json` — latest attempted cycle;
- `latest_success.json` — latest successful cycle only.

Each record includes:

- cycle ID and status;
- owner and notification destination;
- repository, Metals source, and package roots;
- start, completion, and runtime;
- package ID and data-as-of evidence;
- failed stage;
- warnings and errors;
- command, return code, runtime, stdout tail, and stderr tail for every stage.

## Dashboard-ready outputs

The runner publishes:

```text
data/operations/metals/metals_operations_status.json
data/operations/metals/metals_operations_status.csv
```

The status projection includes cycle health, readiness health, package identity, provider status, registry status, bridge status, model parity, and vehicle-constraint status.

## Test command

```powershell
python -m pytest tests\production\test_metals_cycle.py tests\production\test_metals_operations_status.py -q
```

Then run the related Metals production tests:

```powershell
python -m pytest tests\production -q
```

Finally run the full regression suite:

```powershell
python -m pytest -q
```

## Scheduling guidance

The supported scheduler command should invoke the PowerShell runner from the repository root. The scheduled task must capture the process exit code and treat any nonzero value as a failure.

Recommended initial cadence:

- full production cycle monthly after the World Bank benchmark update;
- a separate daily market-overlay cycle will be introduced in Phase 8.9.3;
- manual rerun after provider remediation or package correction.

The scheduler record should identify the task owner, cadence, executable command, last success, last failure, runtime, package ID, data-as-of date, and notification destination.

## Definition of done

Phase 8.9.1 is complete when:

- focused tests pass;
- production tests pass;
- full regression tests pass;
- one live cycle returns PASS;
- `latest.json`, `latest_success.json`, readiness JSON, operations JSON, and operations CSV exist;
- the latest successful record contains a package ID and data-as-of value;
- the scheduled execution method and notification destination are documented.
