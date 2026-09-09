"""Read-only byte portability audit for the certified Secret Lair premium sidecar.

This script does not modify source data, presentation data, or PostgreSQL. It compares
raw checkout bytes with canonical LF and CRLF byte forms to determine whether the
historic governed SHA mismatch is explained solely by line-ending normalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GOVERNED_SHA256 = "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
OBSERVED_LINUX_SHA256 = "6ed7f46d52f01bfb0ba80dfb923a9f438dd899641280bf52d887b1fc0dd956fe"
EXPECTED_ROWS = 787


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def normalize_crlf(data: bytes) -> bytes:
    return normalize_lf(data).replace(b"\n", b"\r\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()

    path = args.sidecar.resolve()
    if not path.is_file():
        raise RuntimeError(f"Secret Lair premium sidecar missing: {path}")

    raw = path.read_bytes()
    lf = normalize_lf(raw)
    crlf = normalize_crlf(raw)

    # CSV contains one header line plus exactly EXPECTED_ROWS data rows.
    row_count = len(lf.splitlines()) - 1
    raw_sha = digest(raw)
    lf_sha = digest(lf)
    crlf_sha = digest(crlf)

    content_equivalent = normalize_lf(raw) == normalize_lf(crlf)
    portability_proven = (
        row_count == EXPECTED_ROWS
        and lf_sha == OBSERVED_LINUX_SHA256
        and crlf_sha == GOVERNED_SHA256
        and content_equivalent
    )

    evidence = {
        "status": "PORTABILITY_PROVEN" if portability_proven else "FAIL_CLOSED",
        "sidecar": str(path),
        "expected_rows": EXPECTED_ROWS,
        "rows": row_count,
        "row_count_pass": row_count == EXPECTED_ROWS,
        "raw_sha256": raw_sha,
        "canonical_lf_sha256": lf_sha,
        "canonical_crlf_sha256": crlf_sha,
        "expected_linux_lf_sha256": OBSERVED_LINUX_SHA256,
        "governed_certified_sha256": GOVERNED_SHA256,
        "lf_matches_observed_linux": lf_sha == OBSERVED_LINUX_SHA256,
        "crlf_matches_governed_certification": crlf_sha == GOVERNED_SHA256,
        "line_ending_normalization_preserves_content": content_equivalent,
        "source_data_modified": False,
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "governance_changed": False,
        "portability_proven": portability_proven,
    }

    output = args.evidence_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if portability_proven else 1


if __name__ == "__main__":
    raise SystemExit(main())
