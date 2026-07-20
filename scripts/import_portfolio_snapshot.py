"""Validate a private local CSV and upload it to the hosted portfolio API."""

from __future__ import annotations

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.portfolio import preview_portfolio_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a validated portfolio snapshot over HTTPS")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--base-url", default=os.getenv("UIIP_BASE_URL", ""))
    arguments = parser.parse_args()
    base_url = arguments.base_url.strip().rstrip("/")
    if not base_url.startswith("https://"):
        parser.error("--base-url must be an HTTPS URL")
    raw = arguments.csv_path.read_bytes()
    if len(raw) > 262_144:
        parser.error("portfolio CSV exceeds 262144 bytes")
    report = preview_portfolio_csv(raw.decode("utf-8-sig"), is_text=True)
    if not report.valid:
        print(json.dumps({
            "accepted_rows": len(report.positions),
            "error_count": len(report.errors),
            "valid": False,
        }, indent=2, sort_keys=True))
        return 2
    credential = os.getenv("UIIP_PORTFOLIO_OPERATOR_KEY", "") or getpass("Portfolio operator key: ")
    request = Request(
        base_url + "/v1/portfolio/snapshots", data=raw, method="POST",
        headers={"Content-Type": "text/csv; charset=utf-8", "X-API-Key": credential},
    )
    try:
        with urlopen(request, timeout=90) as response:
            document = json.load(response)
    except HTTPError as exc:
        print(json.dumps({"status": "FAILED", "status_code": exc.code}, sort_keys=True))
        return 1
    snapshot = document["snapshot"]
    print(json.dumps({
        "created": bool(document["created"]),
        "fingerprint": snapshot["fingerprint"],
        "position_count": snapshot["position_count"],
        "snapshot_id": snapshot["snapshot_id"],
        "status": "PASSED",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
