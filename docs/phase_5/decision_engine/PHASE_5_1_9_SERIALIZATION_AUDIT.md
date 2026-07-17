# Phase 5.1.9 — Universal Decision Serialization and Audit

## Objective

Provide stable, schema-versioned serialization, reconstruction, and
filesystem exports for orchestrated investment decisions.

## Supported outputs

The serialization layer supports:

- complete JSON decision records;
- immutable audit JSON records;
- flat summary records;
- multi-decision CSV exports;
- reconstruction of DecisionResult objects.

## Schema versioning

Serialized records contain independent versions for:

- decision schema;
- serialization implementation;
- Decision Engine;
- policy;
- scoring;
- classification;
- confidence;
- constraints;
- allocation;
- explanation.

The initial decision schema version is `1.0`.

## Stable primitive representation

Serialization converts:

- enums to stable string values;
- Decimal values to strings;
- timezone-aware datetimes to ISO 8601 strings;
- tuples and sequences to JSON arrays;
- nested dataclasses to mappings.

Naive datetimes and unsupported object types are rejected.

## Decision record

The complete decision record contains:

- record type;
- schema version;
- serialization version;
- engine version;
- final DecisionResult;
- intermediate artifacts;
- explanation.

Intermediate artifacts and explanation may be omitted through the
serialization profile.

## Audit record

The audit record always preserves:

- complete final decision;
- all intermediate artifacts;
- complete explanation;
- audit facts;
- source metadata;
- component versions.

It is intended for deterministic reconstruction and certification.

## Summary record

The summary record is flat and suitable for:

- opportunity ranking;
- dashboards;
- CSV exports;
- batch analytics;
- decision registries.

## Reconstruction

The deserializer reconstructs the stable final DecisionResult contract.

It validates:

- record type;
- supported schema version;
- required identifiers;
- enum values;
- Decimal-compatible values;
- timezone-aware timestamps;
- evidence records;
- score structure.

## Export formats

### JSON

Writes the complete schema-versioned decision record.

### Audit JSON

Writes an immutable reconstruction package.

### CSV

Writes one flat summary row per decision.

## DecisionSerializationProfile

The profile controls:

- schema version;
- JSON indentation;
- deterministic key ordering;
- inclusion of intermediate artifacts;
- inclusion of explanation;
- inclusion of audit facts;
- inclusion of source metadata.

## Determinism

Serializing the same orchestration result with the same profile produces
identical JSON text.

This supports:

- historical replay;
- reproducibility checks;
- audit hashing;
- certification;
- regression testing.

## Scope boundary

Phase 5.1.9 serializes and reconstructs decisions.

It does not:

- certify recommendation quality;
- calculate historical decision outcomes;
- evaluate decision drift;
- approve decisions for execution.

Those responsibilities belong to Phase 5.1.10 and later Phase 5
components.
