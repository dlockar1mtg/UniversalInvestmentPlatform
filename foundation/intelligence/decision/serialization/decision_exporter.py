"""Filesystem exports for serialized decision records."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from ..orchestration.orchestration_result import (
    DecisionOrchestrationResult,
)
from .decision_serializer import UniversalDecisionSerializer
from .serialization_errors import DecisionExportError
from .serialization_profile import DecisionSerializationProfile


class UniversalDecisionExporter:
    """Write decision detail, audit, and summary records to disk."""

    def __init__(
        self,
        serializer: UniversalDecisionSerializer | None = None,
    ) -> None:
        self._serializer = (
            serializer or UniversalDecisionSerializer()
        )

    def export_json(
        self,
        result: DecisionOrchestrationResult,
        path: str | Path,
        *,
        profile: DecisionSerializationProfile | None = None,
    ) -> Path:
        """Write a complete serialized decision to JSON."""

        destination = Path(path)
        self._prepare_parent(destination)

        try:
            destination.write_text(
                self._serializer.to_json(
                    result,
                    profile=profile,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            raise DecisionExportError(
                f"Unable to write decision JSON to {destination}."
            ) from exc

        return destination

    def export_audit_json(
        self,
        result: DecisionOrchestrationResult,
        path: str | Path,
        *,
        profile: DecisionSerializationProfile | None = None,
    ) -> Path:
        """Write a full reconstruction audit record to JSON."""

        destination = Path(path)
        self._prepare_parent(destination)

        active_profile = (
            profile or DecisionSerializationProfile()
        )
        payload = self._serializer.audit_record(
            result,
            profile=active_profile,
        )

        try:
            destination.write_text(
                json.dumps(
                    payload,
                    indent=active_profile.json_indent,
                    sort_keys=active_profile.sort_keys,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            raise DecisionExportError(
                f"Unable to write audit JSON to {destination}."
            ) from exc

        return destination

    def export_summary_csv(
        self,
        results: Iterable[DecisionOrchestrationResult],
        path: str | Path,
    ) -> Path:
        """Write one flat CSV row per decision."""

        destination = Path(path)
        self._prepare_parent(destination)

        rows = [
            dict(self._serializer.summary_record(result))
            for result in results
        ]

        if not rows:
            raise DecisionExportError(
                "At least one decision is required for CSV export."
            )

        try:
            with destination.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(rows[0]),
                    extrasaction="raise",
                )
                writer.writeheader()
                writer.writerows(rows)
        except (OSError, csv.Error, ValueError) as exc:
            raise DecisionExportError(
                f"Unable to write decision CSV to {destination}."
            ) from exc

        return destination

    @staticmethod
    def _prepare_parent(destination: Path) -> None:
        try:
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise DecisionExportError(
                f"Unable to create export directory for {destination}."
            ) from exc
