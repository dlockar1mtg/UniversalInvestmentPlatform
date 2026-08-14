"""Validate the governed R1 refresh/orchestration contract set."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.orchestration.refresh_contracts import load_refresh_contracts


def main() -> int:
    contracts = load_refresh_contracts(ROOT)
    payload = {
        "status": "UIP_R1_REFRESH_CONTRACT_VALIDATION_PASS",
        "contract_version": contracts.contract_version,
        "milestone": contracts.milestone,
        "domains": [contract.domain_id for contract in contracts.domains],
        "required_cycle_evidence_fields": len(contracts.required_cycle_evidence),
        "r2_milestone": contracts.r2_milestone,
        "r3_milestone": contracts.r3_milestone,
        "r3_findings": list(contracts.r3_findings),
        "cross_asset_ranking_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
