# Phase 8.9.8 Certification — Metals Legacy Retirement Verification

## Certification status

**VERIFIER CERTIFIED / LIVE RETIREMENT EVIDENCE INCOMPLETE**

Phase 8.9.8 adds a deterministic, fail-closed verifier for retiring the standalone Metals runtime. The verifier itself is certified. The actual legacy system must not be declared retired until real operational evidence is populated and passes strict verification.

## Certified implementation

- Structured legacy-retirement evidence contract.
- Explicit `PASS`, `INCOMPLETE`, and `FAILED` states.
- Schedule-disablement verification.
- Observation-window verification.
- Legacy runtime-execution monitoring evidence.
- Legacy database-access monitoring evidence.
- Archive path and SHA-256 verification.
- Recovery-procedure and ownership requirements.
- Machine-readable JSON publication.
- Strict nonzero exit behavior when evidence is incomplete or failed.

## Test evidence

Executed on July 25, 2026:

- Focused Phase 8.9.8 tests: **7 passed**.
- Production test suite: **133 passed**.
- Full platform regression suite: **1,148 passed**.
- Existing FastAPI/Starlette test-client warning remained nonblocking.

## Deterministic verifier validation

Command:

```powershell
python scripts\publish_metals_legacy_retirement_verification.py `
  --input config\metals\legacy_retirement_validation_sample.json `
  --strict
```

Result:

- Status: `PASS`.
- Legacy system: `Standalone Metals Platform`.
- Schedule disabled: `true`.
- Observation window completed: `true`.
- Legacy runtime executions: `0`.
- Legacy database accesses: `0`.
- Archive checksum verified: `true`.
- Reason: `RETIREMENT_EVIDENCE_COMPLETE`.
- Strict exit code: `0`.

The committed validation sample is synthetic and certifies verifier behavior only. It is not evidence of actual operational retirement.

## Live fail-closed validation

Command:

```powershell
python scripts\publish_metals_legacy_retirement_verification.py --strict
```

With no populated live evidence file, the verifier returned:

- Status: `INCOMPLETE`.
- Legacy system: `UNKNOWN`.
- Runtime and database counts unresolved.
- Missing schedule, observation, archive, recovery, owner, and evidence-date fields reported through explicit reason codes.
- Strict exit code: `1`.

This confirms the system cannot mistake missing evidence for completed retirement.

## Live completion requirements

Actual legacy retirement remains incomplete until the live evidence record contains verified values for:

1. schedule disablement and disablement timestamp;
2. completed observation window;
3. zero legacy runtime executions during the observation window;
4. zero legacy database accesses during the observation window;
5. durable archive location;
6. actual SHA-256 archive checksum and successful checksum verification;
7. recovery procedure path;
8. accountable owner;
9. evidence-as-of timestamp.

## Certification conclusion

The Phase 8.9.8 verifier and its fail-closed behavior are certified. Live retirement of the standalone Metals platform is explicitly **not yet certified** and must remain `INCOMPLETE` until real operational evidence passes strict verification.
