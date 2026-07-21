# Metals Legacy Retirement Runbook

## Purpose

Retire the standalone `C:\Users\DevonLockard\metals` runtime only after Phase 8.8 passes and
the production-hardening pull request is merged.

Retirement means making the universal platform authoritative. It does not mean immediately
deleting historical evidence.

## Preconditions

All conditions are mandatory:

1. Phase 8.8 final certification reports PASS.
2. The full universal regression suite passes.
3. The branch is clean and pushed.
4. The pull request is approved and merged.
5. Adapter release 2.0.0 produces a PASS package.
6. The exports-only independence proof passes.
7. The combined production-readiness report is PASS with zero warnings and errors.
8. A recoverable archive of the legacy source, configuration, database, and final exports exists.

## Authoritative capabilities after merge

The universal platform owns:

- Metals official providers and provider policies;
- canonical asset and vehicle registries;
- vehicle-selection constraints;
- universal portfolio, risk, forecast, and recommendation contracts;
- verified handoff ingestion;
- model-evidence parity;
- production readiness and operational reporting.

The legacy application is not an ongoing production dependency.

## Archive contents

Retain one read-only archive containing:

- the legacy source tree;
- the final DuckDB database;
- the nine v8 native exports;
- the five bridge surfaces;
- `metals_bridge_export_manifest.json`;
- the last certified universal package identifier;
- the source audit and capability decision matrix;
- the final readiness and Phase 8.8 certification reports.

Record a SHA-256 checksum for the archive and store it separately from the archive itself.

## Retirement sequence

1. Stop scheduled legacy Metals jobs.
2. Confirm no process is writing to the legacy DuckDB.
3. Run `export_v8.py`.
4. Run `export_metals_bridge_surfaces.py`.
5. Build adapter release 2.0.0 package.
6. Run model parity and combined production readiness.
7. Create and checksum the archive.
8. Mark the standalone directory read-only.
9. Run the universal Metals workflow through one complete scheduled cycle.
10. After the observation window succeeds, move the standalone directory to archival storage.

Do not delete the standalone directory as part of the merge.

## Rollback

Rollback is allowed only when the universal Metals workflow cannot produce a valid package or a
material semantic regression is discovered.

1. Disable the universal Metals schedule.
2. Restore the archived legacy directory to a separate recovery path.
3. Verify the archive checksum before use.
4. Restore credentials through the approved secret mechanism; do not copy secrets from logs.
5. Run the legacy pipeline read-only first.
6. Document the incident and the exact failed Phase 8 gate.
7. Correct the universal implementation and repeat Phase 8.8.

## Completion evidence

Retirement is complete when:

- the universal workflow completes its observation window;
- no production job reads the legacy DuckDB;
- no production module imports `metals_platform`;
- the archive checksum is recorded;
- operational ownership and recovery instructions are documented.
