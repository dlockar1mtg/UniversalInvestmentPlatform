"""Resolve authoritative MTG source entry points from static audit evidence.

This module never imports or executes the MTG source repository. It ranks only
executable source files and explicitly excludes tests, documentation, installers,
and apply-style bundle scripts from authoritative selection.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

EXCLUDED_PARTS = {"tests", "test", "docs", ".github"}
EXCLUDED_PREFIXES = ("apply_", "install_", "repair_", "patch_", "test_")
ROLE_RULES: dict[str, tuple[str, ...]] = {
    "UNIVERSAL_EXPORT": ("universal_export", "export"),
    "PRODUCTION_CLOSEOUT": ("production_closeout", "unified_mtg_closeout", "closeout"),
    "EBAY_COLLECTION": ("ebay", "collect"),
    "EBAY_CERTIFICATION": ("ebay", "certif"),
    "TCGPLAYER_COLLECTION": ("tcgplayer", "tcgcsv", "collect", "download", "ingest"),
    "FORECAST": ("forecast",),
    "RECOMMENDATION": ("recommendation",),
    "PORTFOLIO": ("portfolio",),
}


@dataclass(frozen=True)
class EntrypointCandidate:
    role: str
    path: str
    score: int
    authoritative: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class EntrypointReport:
    status: str
    selections: dict[str, EntrypointCandidate]
    alternatives: dict[str, tuple[EntrypointCandidate, ...]]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "selections": {key: asdict(value) for key, value in self.selections.items()},
            "alternatives": {
                key: [asdict(item) for item in values] for key, values in self.alternatives.items()
            },
            "reason_codes": list(self.reason_codes),
        }


def _excluded(path: str) -> bool:
    normalized = Path(path)
    lower_parts = {part.lower() for part in normalized.parts}
    return bool(lower_parts & EXCLUDED_PARTS) or normalized.name.lower().startswith(EXCLUDED_PREFIXES)


def _rank(role: str, row: Mapping[str, object]) -> EntrypointCandidate | None:
    path = str(row.get("path", ""))
    if not path or not bool(row.get("executable")) or _excluded(path):
        return None
    lower = path.lower()
    terms = ROLE_RULES[role]
    hits = sum(term in lower for term in terms)
    if hits == 0:
        return None
    score = int(row.get("score", 0)) + hits * 20
    reasons: list[str] = ["EXECUTABLE_SOURCE_FILE", f"ROLE_TERM_HITS:{hits}"]
    name = Path(path).name.lower()
    if name.startswith(("run_", "build_", "certify_", "collect_", "export_", "validate_")):
        score += 10
        reasons.append("PRODUCTION_STYLE_NAME")
    if "phase_10_10" in lower and role == "UNIVERSAL_EXPORT":
        score += 25
        reasons.append("CERTIFIED_PHASE_10_10_EXPORT")
    if "phase_10_9" in lower and role == "PRODUCTION_CLOSEOUT":
        score += 25
        reasons.append("CERTIFIED_PHASE_10_9_CLOSEOUT")
    return EntrypointCandidate(role, path, score, False, tuple(reasons))


def resolve_entrypoints(audit_payload: Mapping[str, object]) -> EntrypointReport:
    rows = audit_payload.get("candidates", [])
    if not isinstance(rows, list):
        return EntrypointReport("FAILED", {}, {}, ("INVALID_AUDIT_PAYLOAD",))

    selections: dict[str, EntrypointCandidate] = {}
    alternatives: dict[str, tuple[EntrypointCandidate, ...]] = {}
    reasons: list[str] = []
    for role in ROLE_RULES:
        ranked = [candidate for row in rows if isinstance(row, dict) if (candidate := _rank(role, row))]
        ranked.sort(key=lambda item: (-item.score, item.path))
        alternatives[role] = tuple(ranked[:10])
        if ranked:
            winner = ranked[0]
            selections[role] = EntrypointCandidate(
                role=winner.role,
                path=winner.path,
                score=winner.score,
                authoritative=True,
                reason_codes=winner.reason_codes + ("HIGHEST_RANKED_CANDIDATE",),
            )
        else:
            reasons.append(f"MISSING_{role}_ENTRYPOINT")

    required = {"UNIVERSAL_EXPORT", "PRODUCTION_CLOSEOUT", "EBAY_COLLECTION", "TCGPLAYER_COLLECTION"}
    missing_required = sorted(required - selections.keys())
    if missing_required:
        reasons.extend(f"REQUIRED_ENTRYPOINT_UNRESOLVED:{role}" for role in missing_required)
        status = "INCOMPLETE"
    else:
        status = "PASS"
        reasons.append("MTG_ENTRYPOINT_MAP_RESOLVED")
    return EntrypointReport(status, selections, alternatives, tuple(dict.fromkeys(reasons)))


def load_audit(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def publish_entrypoints(report: EntrypointReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return output_path
