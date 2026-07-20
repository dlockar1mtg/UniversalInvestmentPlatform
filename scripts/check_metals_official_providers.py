"""Opt-in live health check for official Metals data providers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_providers import (
    ProviderCollectionPolicy,
    collect_with_policy,
    ingest_commodity_observations,
)
from foundation.production.providers import (
    EIAUraniumProvider,
    ProviderError,
    WorldBankCommodityProvider,
)


def _summary(name, result, batch):
    return {
        "provider": name,
        "status": "PASS",
        "attempts": result.attempts,
        "records": len(batch.records),
        "fingerprint": batch.batch_fingerprint,
        "observations": [
            {
                "asset_id": record.asset_id,
                "observed_at": record.observed_at.isoformat(),
                "price": str(record.values["price"]),
                "source_reference": record.source_reference,
            }
            for record in batch.records
        ],
    }


def main() -> int:
    as_of = datetime.now(timezone.utc)
    checks = []
    try:
        eia_policy = ProviderCollectionPolicy(
            maximum_attempts=3,
            initial_backoff=timedelta(seconds=2),
            maximum_age=timedelta(days=730),
        )
        eia_result = collect_with_policy(
            EIAUraniumProvider().latest,
            eia_policy,
            as_of=as_of,
        )
        checks.append(_summary("eia", eia_result, ingest_commodity_observations(eia_result, eia_policy)))

        world_bank_policy = ProviderCollectionPolicy(
            maximum_attempts=3,
            initial_backoff=timedelta(seconds=2),
            maximum_age=timedelta(days=75),
        )
        world_bank_result = collect_with_policy(
            WorldBankCommodityProvider().latest,
            world_bank_policy,
            as_of=as_of,
        )
        checks.append(
            _summary(
                "world_bank",
                world_bank_result,
                ingest_commodity_observations(world_bank_result, world_bank_policy),
            )
        )
    except (ProviderError, ValueError) as exc:
        print(json.dumps({
            "status": "FAILED",
            "completed_checks": checks,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({"status": "PASS", "checks": checks}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
