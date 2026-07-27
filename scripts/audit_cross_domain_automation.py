from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "config" / "phase_11" / "cross_domain_automation_contract.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "operations" / "phase_11"

@dataclass(frozen=True)
class Finding:
    domain: str
    category: str
    item: str
    status: str
    severity: str
    details: str

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def git_branch(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""

def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def audit_domain(domain: str, config: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    repo = Path(config["repository_path"])

    if not repo.is_dir():
        return [Finding(domain, "repository", str(repo), "FAIL", "critical", "Repository path does not exist.")]

    branch = git_branch(repo)
    findings.append(Finding(
        domain, "repository", "git_branch",
        "PASS" if branch else "FAIL",
        "info" if branch else "critical",
        branch or "Unable to determine current branch.",
    ))

    workflow_payloads: dict[Path, str] = {}
    for relative in config.get("workflow_paths", []):
        path = repo / relative
        if not path.is_file():
            findings.append(Finding(domain, "workflow", relative, "FAIL", "critical", "Workflow file is missing."))
            continue
        payload = path.read_text(encoding="utf-8")
        workflow_payloads[path] = payload
        findings.append(Finding(domain, "workflow", relative, "PASS", "info", "Workflow exists."))

    combined = "\n".join(workflow_payloads.values())

    for schedule in config.get("required_schedules", []):
        present = bool(re.search(rf'cron:\s*["\']{re.escape(schedule)}["\']', combined))
        findings.append(Finding(
            domain, "schedule", schedule,
            "PASS" if present else "FAIL",
            "info" if present else "critical",
            "Required cron schedule found." if present else "Required cron schedule missing.",
        ))

    for marker in config.get("required_markers", []):
        present = marker in combined
        findings.append(Finding(
            domain, "workflow_marker", marker,
            "PASS" if present else "FAIL",
            "info" if present else "critical",
            "Required workflow marker found." if present else "Required workflow marker missing.",
        ))

    for secret in config.get("required_secrets", []):
        present = secret in combined
        findings.append(Finding(
            domain, "required_secret_reference", secret,
            "PASS" if present else "FAIL",
            "info" if present else "critical",
            "Secret is referenced by a workflow." if present else "Required secret is not referenced.",
        ))

    for secret in config.get("optional_secrets", []):
        present = secret in combined
        findings.append(Finding(
            domain, "optional_secret_reference", secret,
            "PASS" if present else "WARN",
            "info" if present else "warning",
            "Optional secret is referenced." if present else "Optional secret is not referenced.",
        ))

    delivery_required = bool(config.get("delivery_required", True))
    for marker in config.get("delivery_markers", []):
        present = marker in combined
        missing_status = "FAIL" if delivery_required else "OPEN"
        missing_severity = "critical" if delivery_required else "warning"
        findings.append(Finding(
            domain, "delivery", marker,
            "PASS" if present else missing_status,
            "info" if present else missing_severity,
            "Delivery path or command is present in production workflow." if present
            else "Delivery path or command is not present in production workflow.",
        ))

    for gap in config.get("known_gaps", []):
        findings.append(Finding(domain, "known_gap", gap, "OPEN", "warning", gap))

    return findings

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Metals, Crypto, and MTG production automation.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    for domain, config in contract["domains"].items():
        findings.extend(audit_domain(domain, config))

    inventory = [asdict(item) for item in findings]
    gaps = [row for row in inventory if row["status"] in {"FAIL", "WARN", "OPEN"}]

    summary: dict[str, dict[str, Any]] = {}
    for domain in contract["domains"]:
        rows = [row for row in inventory if row["domain"] == domain]
        failures = sum(row["status"] == "FAIL" for row in rows)
        warnings = sum(row["status"] in {"WARN", "OPEN"} for row in rows)
        summary[domain] = {
            "status": "FAIL" if failures else ("WARN" if warnings else "PASS"),
            "finding_count": len(rows),
            "failures": failures,
            "warnings": warnings,
        }

    overall = "FAIL" if any(v["status"] == "FAIL" for v in summary.values()) else (
        "WARN" if any(v["status"] == "WARN" for v in summary.values()) else "PASS"
    )

    args.output_root.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_root / "automation_inventory.csv", inventory,
              ["domain", "category", "item", "status", "severity", "details"])
    write_csv(args.output_root / "automation_gap_register.csv", gaps,
              ["domain", "category", "item", "status", "severity", "details"])

    report = {
        "status": overall,
        "contract_version": contract["contract_version"],
        "generated_at_utc": utc_now(),
        "domain_summary": summary,
        "findings": inventory,
    }
    (args.output_root / "automation_readiness.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))
    print(f"\nPHASE 11 AUTOMATION READINESS: {overall}")
    print(f"Inventory: {args.output_root / 'automation_inventory.csv'}")
    print(f"Gap register: {args.output_root / 'automation_gap_register.csv'}")
    print(f"Readiness report: {args.output_root / 'automation_readiness.json'}")

    return 1 if args.strict and overall == "FAIL" else 0

if __name__ == "__main__":
    raise SystemExit(main())
