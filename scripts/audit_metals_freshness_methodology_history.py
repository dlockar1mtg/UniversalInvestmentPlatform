"""Read-only Git-history audit for retired Metals freshness methodology."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMS = [
    "latest_data_freshness_details",
    "export_v8.py",
    "freshness_status",
    "health_score",
    "age_days",
    "frequency",
]


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, errors="replace")


def main() -> int:
    commits = run("git", "rev-list", "--all").splitlines()
    hits: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for commit in commits:
        try:
            names = run("git", "ls-tree", "-r", "--name-only", commit).splitlines()
        except subprocess.CalledProcessError:
            continue
        candidate_paths = [
            p for p in names
            if any(token in p.lower() for token in ("metal", "fresh", "export_v8", "schema", "view"))
            and p.lower().endswith((".py", ".sql", ".md", ".csv", ".json", ".yml", ".yaml"))
        ]
        for path in candidate_paths:
            key = (commit, path)
            if key in seen:
                continue
            try:
                text = run("git", "show", f"{commit}:{path}")
            except subprocess.CalledProcessError:
                continue
            matched = [term for term in TERMS if term.lower() in text.lower()]
            if not matched:
                continue
            seen.add(key)
            snippets: list[str] = []
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if any(term.lower() in line.lower() for term in TERMS):
                    lo, hi = max(0, i - 2), min(len(lines), i + 3)
                    snippet = "\n".join(lines[lo:hi])
                    if snippet not in snippets:
                        snippets.append(snippet)
                if len(snippets) >= 8:
                    break
            hits.append({
                "commit": commit,
                "path": path,
                "matched_terms": matched,
                "snippets": snippets,
            })

    exact_candidates = [
        h for h in hits
        if "latest_data_freshness_details" in h["matched_terms"] or "export_v8.py" in h["matched_terms"]
    ]
    result = {
        "status": "METALS_FRESHNESS_METHODOLOGY_HISTORY_AUDIT_PASS",
        "query_policy": "LOCAL_GIT_HISTORY_READ_ONLY",
        "commit_count_scanned": len(commits),
        "hit_count": len(hits),
        "exact_candidate_count": len(exact_candidates),
        "exact_candidates": exact_candidates[:50],
        "all_hits": hits[:100],
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "source_collection_performed": False,
    }
    out = ROOT / "data" / "operations" / "publication" / "metals_freshness_methodology_history_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("METALS_FRESHNESS_METHODOLOGY_HISTORY_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
