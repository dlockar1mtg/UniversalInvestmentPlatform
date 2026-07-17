# Phase 1.3 — Universal Import Engine Architecture

## Input

A validated Universal Integration Package.

Initial certified source:

- Platform: Metals
- Native platform version: v8.1
- Adapter version: 1.2.2
- Contract version: v1

## Processing Flow

1. Discover package
2. Read manifest
3. Establish package identity
4. Validate required files
5. Verify checksums
6. Verify row counts
7. Validate datasets against Universal contracts
8. Check duplicate policy
9. Begin database transaction
10. Register import
11. Load dataset history tables
12. Verify imported row counts
13. Update package registry
14. Update platform registry
15. Commit transaction
16. Publish import result

## Failure Flow

1. Capture failure context
2. Roll back production data
3. Record failed attempt
4. Preserve validation evidence
5. Return non-zero exit status

## Separation of Responsibilities

### Native Platform

- produces native analytics
- publishes Universal package through an adapter

### Export Adapter

- maps native output to Universal contracts
- creates manifest
- validates export package

### Import Engine

- verifies package integrity
- loads Universal database
- records lineage and audit history

### Universal Analytics Layer

- reads current-state and historical Universal data
- does not read native platform databases directly