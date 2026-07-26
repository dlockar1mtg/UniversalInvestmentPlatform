"""Static, non-live capability audit for the MTG source repository."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

TEXT_SUFFIXES = {".py", ".ps1", ".yml", ".yaml", ".json", ".md", ".toml", ".txt"}
CAPABILITY_TERMS = {
    "EBAY": ("ebay",),
    "TCGPLAYER": ("tcgplayer", "tcgcsv"),
    "EXPORT": ("universal export", "export_manifest", "package_summary"),
    "CERTIFICATION": ("certif", "production_closed", "validation"),
    "FORECAST": ("forecast",),
    "RECOMMENDATION": ("recommendation", "buy signal"),
    "PORTFOLIO": ("portfolio", "holding"),
    "SCHEDULING": ("schedule", "cron", "task scheduler"),
}
SKIP_PARTS = {".git", ".venv", "venv", "__pycache__", "node_modules", "data"}


@dataclass(frozen=True)
class CapabilityCandidate:
    path: str
    capabilities: tuple[str, ...]
    executable: bool
    score: int


@dataclass(frozen=True)
class SourceAuditReport:
    status: str
    source_root: str
    files_scanned: int
    candidates: tuple[CapabilityCandidate, ...]
    capability_counts: dict[str, int]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "source_root": self.source_root,
            "files_scanned": self.files_scanned,
            "candidates": [asdict(item) for item in self.candidates],
            "capability_counts": self.capability_counts,
            "reason_codes": list(self.reason_codes),
        }


def _eligible(relative_path: Path) -> bool:
    return (
        relative_path.suffix.lower() in TEXT_SUFFIXES
        and not any(part in SKIP_PARTS for part in relative_path.parts)
    )


def _classify(path: Path, text: str) -> CapabilityCandidate | None:
    haystack = f"{path.as_posix()}\n{text[:200000]}".lower()
    capabilities = tuple(
        name for name, terms in CAPABILITY_TERMS.items() if any(term in haystack for term in terms)
    )
    if not capabilities:
        return None
    executable = path.suffix.lower() in {".py", ".ps1"}
    score = len(capabilities) * 10 + (5 if executable else 0)
    if path.name.lower().startswith(("run_", "export_", "certify_", "check_", "collect_", "build_")):
        score += 4
    return CapabilityCandidate(path.as_posix(), capabilities, executable, score)


def audit_source(source_root: Path) -> SourceAuditReport:
    root = source_root.resolve()
    if not root.is_dir():
        return SourceAuditReport("FAILED", str(root), 0, (), {}, ("MTG_SOURCE_ROOT_NOT_AVAILABLE",))

    scanned = 0
    candidates: list[CapabilityCandidate] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if not _eligible(relative):
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        candidate = _classify(relative, text)
        if candidate is not None:
            candidates.append(candidate)

    candidates.sort(key=lambda item: (-item.score, item.path))
    counts = {name: sum(name in item.capabilities for item in candidates) for name in CAPABILITY_TERMS}
    reasons: list[str] = []
    for required in ("EBAY", "TCGPLAYER", "EXPORT", "CERTIFICATION"):
        if counts.get(required, 0) == 0:
            reasons.append(f"MISSING_{required}_CAPABILITY")
    status = "PASS" if not reasons else "INCOMPLETE"
    if not reasons:
        reasons.append("MTG_SOURCE_CAPABILITIES_DISCOVERED")
    return SourceAuditReport(status, str(root), scanned, tuple(candidates), counts, tuple(reasons))


def publish_source_audit(report: SourceAuditReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return output_path
