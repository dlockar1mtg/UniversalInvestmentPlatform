# Phase 8.9.8 — Legacy Retirement Verification

## Objective

Provide structured, auditable evidence that the standalone Metals runtime has
been retired and is no longer operating beside the Universal Investment
Platform.

## Required evidence

A retirement record must include:

- retirement identifier and legacy-system name;
- schedule-disabled flag and timestamp;
- observation-window duration and completion status;
- legacy runtime execution count;
- legacy database access count;
- archive path;
- SHA-256 archive checksum and verification status;
- recovery-procedure path;
- accountable owner;
- evidence-as-of timestamp.

## Status rules

### PASS

All required evidence is present, the observation window is complete, no legacy
runtime execution or database access was detected, and the archive checksum is
valid and verified.

### INCOMPLETE

Required evidence is missing, invalid, or not yet complete. Examples include an
unfinished observation window, missing archive location, or unverified
checksum.

### FAILED

Evidence shows the retired runtime executed or accessed its legacy database
after disablement.

## Components

- `config/metals/legacy_retirement_evidence_template.json`
- `config/metals/legacy_retirement_validation_sample.json`
- `foundation/production/metals_legacy_retirement.py`
- `scripts/publish_metals_legacy_retirement_verification.py`
- `tests/production/test_metals_legacy_retirement.py`

## Output

The publisher writes:

- `metals_legacy_retirement_verification.json`

under `data/operations/metals/legacy_retirement_verification`.

## Validation versus live evidence

The committed validation sample is synthetic and exists only to certify the
verifier. It is not proof that the real standalone Metals platform has been
retired.

Live verification must use:

`data/operations/metals/legacy_retirement_evidence.json`

or an explicitly supplied `--input` file containing real retirement evidence.
Strict mode returns a nonzero exit code unless the status is `PASS`.

## Commands

Validation sample:

```powershell
python scripts\publish_metals_legacy_retirement_verification.py `
  --input config\metals\legacy_retirement_validation_sample.json `
  --strict
```

Live evidence:

```powershell
python scripts\publish_metals_legacy_retirement_verification.py --strict
```
