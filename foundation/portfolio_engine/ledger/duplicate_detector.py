"""Duplicate detection for portfolio ledger imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .ledger_entry import LedgerEntry


@dataclass(slots=True)
class DuplicateResult:
    accepted: list[LedgerEntry]
    duplicates: list[LedgerEntry]


def split_duplicates(
    entries: Iterable[LedgerEntry],
    existing_hashes: set[str] | None = None,
    existing_source_keys: set[tuple[str, str]] | None = None,
) -> DuplicateResult:
    hashes = set(existing_hashes or set())
    source_keys = set(existing_source_keys or set())
    accepted: list[LedgerEntry] = []
    duplicates: list[LedgerEntry] = []

    for entry in entries:
        source_key = None
        if entry.source_platform and entry.source_record_id:
            source_key = (entry.source_platform, entry.source_record_id)

        is_duplicate = entry.audit_hash in hashes or (
            source_key is not None and source_key in source_keys
        )
        if is_duplicate:
            duplicates.append(entry)
            continue

        accepted.append(entry)
        hashes.add(entry.audit_hash)
        if source_key is not None:
            source_keys.add(source_key)

    return DuplicateResult(accepted=accepted, duplicates=duplicates)
