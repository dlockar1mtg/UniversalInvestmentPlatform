# Architecture Decision Log

## ADR-001 — Multi-Repository Architecture

Status: Accepted

Decision:

Maintain separate repositories for each investment intelligence platform.

Reason:

The platforms have different data sources, dependencies, databases, update
schedules, and development histories.

Consequences:

- Platforms remain independently maintainable.
- Universal integration requires standardized exports.
- Cross-repository coordination is required.
- Individual failures do not disable the full ecosystem.

---

## ADR-002 — Exchange-Layer Integration

Status: Accepted

Decision:

Platforms publish standardized files to a Universal Exchange Layer rather
than writing directly to the central integration database.

Reason:

This reduces coupling and permits platforms to run on different computers.

Consequences:

- Export schemas must be standardized.
- Freshness metadata must be included.
- Validation occurs before database import.

---

## ADR-003 — Platform-Owned Databases

Status: Accepted

Decision:

Each investment platform retains ownership of its own database.

Reason:

Existing platforms have different schemas and data volumes. Immediate database
consolidation would create unnecessary migration risk.

Consequences:

- Raw platform databases remain separate.
- The Universal Platform stores normalized integration records only.
- Platform-specific history remains within each platform.

---

## ADR-004 — Git Excludes Generated Data

Status: Accepted

Decision:

Raw data, generated exports, databases, archives, and secrets are excluded
from Git.

Reason:

Git is used for source code, documentation, schemas, and reproducibility—not
large generated datasets.

Consequences:

- Data requires separate backup and synchronization methods.
- Test fixtures must be deliberately small and sanitized.

---

## ADR-005 — Python Archive Extraction

Status: Accepted

Decision:

Use `py7zr` for TCGCSV `.7z` extraction where practical.

Reason:

The managed computer does not permit administrator installation of 7-Zip,
while `py7zr` successfully extracted the archive.

Consequences:

- MTG becomes more portable.
- `py7zr` and `pyppmd` become documented MTG dependencies.