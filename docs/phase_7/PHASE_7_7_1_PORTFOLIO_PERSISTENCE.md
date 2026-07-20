# Phase 7.7.1 - Secure Portfolio Snapshot Persistence

This increment adds immutable, content-addressed portfolio snapshots for local SQLite evaluation and hosted Neon/PostgreSQL operation.

## Guarantees

- Raw CSV bytes and filenames are not persisted.
- Positions are normalized by the certified Phase 7.2 parser before storage.
- Exact decimal values, timestamps, identity, and lineage are retained.
- Identical holdings reuse the existing SHA-256-addressed snapshot.
- Changed holdings create ordered history without mutating earlier snapshots.
- PostgreSQL writes are transactional and foreign-key protected.
- Snapshot totals reconcile exactly to stored positions.

Hosted ingestion and API authorization are intentionally deferred to Phase 7.7.2.
