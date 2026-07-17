# Universal Import Policy

## Default Mode

The default import mode is STANDARD.

STANDARD mode validates and imports a new package.

It rejects duplicate packages.

## Validation-Only Mode

VALIDATE_ONLY performs all package and contract validation without modifying
the Universal database.

## Forced Mode

FORCE permits a controlled reimport.

FORCE must:

- preserve the prior import record
- record the user-requested override
- create a new import attempt
- never silently overwrite audit history

## Transaction Policy

Production dataset loads must occur inside one database transaction.

The engine must:

1. begin a transaction
2. register the import attempt
3. load all approved datasets
4. verify row counts
5. update package status
6. update platform status
7. commit

If any step fails, the engine must roll back the production data changes.

The failed attempt must still be captured in an audit record when possible.

## Warning Policy

Warnings do not automatically fail an import unless the warning concerns:

- missing required data
- invalid checksum
- invalid contract
- conflicting package identity
- unsupported contract version
- unsupported platform
- row-count mismatch

## Historical Data Policy

Imported datasets are append-only history tables.

Current-state data is exposed through views.

Historical rows must not be deleted during normal imports.

## Security Policy

The import engine must not:

- execute code from an integration package
- import Python modules from a native platform
- modify a native platform database
- expose credentials in logs
- trust filenames without validation