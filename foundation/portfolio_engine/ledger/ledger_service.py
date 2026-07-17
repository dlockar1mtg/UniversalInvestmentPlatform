"""Application service for idempotent ledger posting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID, uuid4

from .duplicate_detector import split_duplicates
from .ledger_entry import LedgerEntry
from .ledger_repository import LedgerRepository


@dataclass(slots=True)
class PostingResult:
    import_run_id: UUID
    received_count: int
    posted_count: int
    duplicate_count: int


class LedgerService:
    def __init__(self, repository: LedgerRepository) -> None:
        self.repository = repository

    def post_entries(
        self,
        entries: Iterable[LedgerEntry],
        import_run_id: UUID | None = None,
    ) -> PostingResult:
        run_id = import_run_id or uuid4()
        rows = list(entries)

        for entry in rows:
            if entry.import_run_id is None:
                entry.import_run_id = run_id

        result = split_duplicates(
            rows,
            existing_hashes=self.repository.existing_hashes(),
            existing_source_keys=self.repository.existing_source_keys(),
        )
        posted = self.repository.append_many(result.accepted)

        return PostingResult(
            import_run_id=run_id,
            received_count=len(rows),
            posted_count=posted,
            duplicate_count=len(result.duplicates),
        )
