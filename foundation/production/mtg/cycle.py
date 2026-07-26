"""Safe-hold MTG production-cycle skeleton.

The cycle cannot execute live marketplace or source-repository work unless the
explicit UIP_MTG_LIVE_EXECUTION gate is enabled. Phase 10.12 begins with this
non-live orchestration contract so Crypto staging remains untouched.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from foundation.production.mtg.readiness import evaluate_mtg_readiness


@dataclass(frozen=True)
class MTGProductionReport:
    status: str
    mode: str
    run_id: str
    started_at_utc: str
    completed_at_utc: str
    stages: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["stages"] = list(self.stages)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


class MTGProductionCycle:
    def __init__(self, source_root: Path, config_path: Path, output_root: Path) -> None:
        self.source_root = source_root
        self.config_path = config_path
        self.output_root = output_root

    def run(self, run_id: str, environment: Mapping[str, str]) -> MTGProductionReport:
        started = datetime.now(timezone.utc).isoformat()
        readiness = evaluate_mtg_readiness(self.source_root, self.config_path, environment)
        stages = ("READINESS", "EVIDENCE_PUBLICATION")

        if readiness.status != "READY":
            report = MTGProductionReport(
                status="SAFE_HOLD",
                mode="NON_LIVE",
                run_id=run_id,
                started_at_utc=started,
                completed_at_utc=datetime.now(timezone.utc).isoformat(),
                stages=stages,
                reason_codes=readiness.reason_codes,
            )
            self.publish(report, readiness.to_dict())
            return report

        report = MTGProductionReport(
            status="NOT_IMPLEMENTED",
            mode="LIVE_GATE_OPEN",
            run_id=run_id,
            started_at_utc=started,
            completed_at_utc=datetime.now(timezone.utc).isoformat(),
            stages=stages,
            reason_codes=("LIVE_EXECUTION_PIPELINE_NOT_YET_IMPLEMENTED",),
        )
        self.publish(report, readiness.to_dict())
        return report

    def publish(self, report: MTGProductionReport, readiness: dict[str, object]) -> Path:
        self.output_root.mkdir(parents=True, exist_ok=True)
        path = self.output_root / "latest.json"
        payload = {"report": report.to_dict(), "readiness": readiness}
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path
