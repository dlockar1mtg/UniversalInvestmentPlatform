"""Single composition path for rehearsal and manual production publication."""
from __future__ import annotations

from pathlib import Path

from foundation.presentation.crypto_current_price_projection import ASSETS, build_crypto_current_price_records
from foundation.presentation.crypto_forecast_tracking import apply_crypto_forecast_tracking
from foundation.presentation.metals_rich_projection import build_metals_rich_records
from foundation.presentation.metals_vehicle_implementation_projection import build_metals_vehicle_implementation_records
from foundation.presentation.publication_model import PresentationPublication


def compose_rich_candidate(
    base: PresentationPublication, crypto_artifact: Path, metals_artifact: Path,
    repository_root: Path,
) -> PresentationPublication:
    generic_crypto_ids = {
        record.asset_id for record in base.records
        if record.domain_id == "crypto" and record.record_type == "asset"
    }
    if generic_crypto_ids != ASSETS:
        raise RuntimeError("Crypto current-price identity set does not reconcile with generic asset catalog")
    # Labeled 7-day context and the forecast-log scorecard from the crypto run evidence (optional).
    apply_crypto_forecast_tracking(base.records, crypto_artifact)
    combined = (
        list(base.records)
        + build_metals_rich_records(metals_artifact)
        + build_metals_vehicle_implementation_records(repository_root)
        + build_crypto_current_price_records(crypto_artifact)
    )
    combined.sort(key=lambda item: (item.record_type, item.domain_id, item.asset_id or "", item.record_key))
    return PresentationPublication(
        publication_id=base.publication_id,
        publication_version=base.publication_version,
        source_database_sha256=base.source_database_sha256,
        source_database_classification=base.source_database_classification,
        published_at_utc=base.published_at_utc,
        publication_status="STAGED",
        records=tuple(combined),
    )
