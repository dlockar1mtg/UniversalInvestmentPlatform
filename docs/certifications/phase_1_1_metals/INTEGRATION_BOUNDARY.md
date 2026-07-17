# Frozen Integration Boundary

## Approved boundary

```text
Metals internal code + DuckDB
        ↓ native read-only export
Metals native export folder
        ↓ deterministic adapter
Universal contract package
        ↓ validation + manifest
Universal integration staging
```

## Universal may

- Read approved native CSV outputs.
- Execute narrowly defined read-only queries through a Metals-owned export script when no CSV exists yet.
- Map identifiers and enums.
- Add provenance, timestamps, checksums, contract versions, and validation fields.
- Reject incomplete, stale, malformed, or internally inconsistent packages.

## Universal may not

- Write to the Metals DuckDB.
- Import Metals engine classes to recompute analytics.
- Depend on internal table names as the permanent API.
- Change Metals recommendations, scores, weights, forecasts, or confidence values.
- Copy `.env`, credentials, raw private data, logs, database backups, or compiled caches into integration packages.

## Versioning

The initial adapter should declare `metals-native-v8` as its source interface and Universal contract version `v1`. Any breaking native-output change requires a new adapter/interface version or an explicit compatibility test.
