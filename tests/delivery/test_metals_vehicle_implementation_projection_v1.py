from pathlib import Path

from foundation.presentation.metals_vehicle_implementation_projection import (
    ONLY_LABEL,
    PREFERRED_LABEL,
    build_metals_vehicle_implementation_records,
)

ROOT = Path(__file__).resolve().parents[2]


def _records():
    return build_metals_vehicle_implementation_records(ROOT)


def test_projection_preserves_non_authorizations_and_paused_cron():
    for record in _records():
        payload = record.payload
        assert payload["ranking_may_not_override_commodity_recommendation"] is True
        assert payload["automatic_execution_authorized"] is False
        assert payload["portfolio_allocation_authorized"] is False
        assert payload["position_sizing_authorized"] is False
        assert payload["central_publication_cron_restoration_authorized"] is False
