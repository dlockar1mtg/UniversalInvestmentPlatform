# Universal Import Engine

The Universal Import Engine validates and loads Universal Integration Packages
into the Universal Investment Intelligence Platform database.

## Current Development Status

Phase 1.3.1 — Specification

## Initial Certified Package

Metals Universal Export Adapter 1.2.2

## Planned Commands

The commands below are planned interfaces. They will not work until their
corresponding scripts are created in later Phase 1.3 subphases.

Initialize the database:

    python scripts\initialize_universal_database.py

Validate a package without importing it:

    python scripts\import_universal_package.py --package data\integration\metals\latest --validate-only

Import a package:

    python scripts\import_universal_package.py --package data\integration\metals\latest

Inspect the Universal database:

    python scripts\inspect_universal_database.py