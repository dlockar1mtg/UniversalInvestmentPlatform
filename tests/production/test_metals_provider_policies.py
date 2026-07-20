from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import yaml

from foundation.production.metals_providers import (
    CommodityObservationAdapter,
    ProviderCollectionPolicy,
    collect_with_policy,
    ingest_commodity_observations,
)
from foundation.production.providers import CommodityObservation, ProviderError


AS_OF = datetime(2026, 7, 20, tzinfo=timezone.utc)


def observation(
    *,
    asset: str = "gold",
    observed: date = date(2026, 6, 1),
    provider: str = "world_bank",
    value: str = "3400",
) -> CommodityObservation:
    return CommodityObservation(
        asset,
        Decimal(value),
        observed,
        "usd_per_troy_ounce",
        provider,
        f"{provider.upper()}::{asset.upper()}",
    )


def test_collection_retries_with_deterministic_backoff() -> None:
    attempts = 0
    pauses: list[float] = []

    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ProviderError("temporary")
        return observation()

    policy = ProviderCollectionPolicy(
        maximum_attempts=3,
        initial_backoff=timedelta(seconds=2),
        backoff_multiplier=3,
        maximum_age=timedelta(days=60),
    )
    result = collect_with_policy(operation, policy, as_of=AS_OF, pause=pauses.append)
    assert result.attempts == 3
    assert pauses == [2.0, 6.0]


def test_collection_exhaustion_hides_provider_details() -> None:
    policy = ProviderCollectionPolicy(maximum_attempts=2)
    with pytest.raises(ProviderError) as caught:
        collect_with_policy(
            lambda: (_ for _ in ()).throw(ProviderError("sensitive detail")),
            policy,
            as_of=AS_OF,
            pause=lambda _: None,
        )
    assert "2 attempt" in str(caught.value)
    assert "sensitive detail" not in str(caught.value)


def test_collection_rejects_stale_and_future_observations() -> None:
    policy = ProviderCollectionPolicy(maximum_attempts=1, maximum_age=timedelta(days=45))
    with pytest.raises(ProviderError):
        collect_with_policy(
            lambda: observation(observed=date(2026, 5, 1)),
            policy,
            as_of=AS_OF,
            pause=lambda _: None,
        )
    with pytest.raises(ProviderError):
        collect_with_policy(
            lambda: observation(observed=date(2026, 7, 21)),
            policy,
            as_of=AS_OF,
            pause=lambda _: None,
        )


def test_collection_policy_validates_bounds() -> None:
    with pytest.raises(ValueError):
        ProviderCollectionPolicy(maximum_attempts=0)
    with pytest.raises(ValueError):
        ProviderCollectionPolicy(maximum_age=timedelta(0))


def test_normalized_ingestion_preserves_lineage_and_is_deterministic() -> None:
    policy = ProviderCollectionPolicy(maximum_age=timedelta(days=60))
    result = collect_with_policy(
        lambda: [observation(asset="silver", value="38"), observation()],
        policy,
        as_of=AS_OF,
        pause=lambda _: None,
    )
    first = ingest_commodity_observations(result, policy)
    reverse_result = type(result)(result.attempts, tuple(reversed(result.observations)), result.collected_at)
    second = ingest_commodity_observations(reverse_result, policy)
    assert first.provider == "world_bank"
    assert first.batch_fingerprint == second.batch_fingerprint
    assert [record.asset_id for record in first.records] == ["metals:gold", "metals:silver"]
    assert str(first.records[0].values["price"]) == "3400"


def test_adapter_rejects_mixed_or_empty_provider_lineage() -> None:
    with pytest.raises(ValueError):
        CommodityObservationAdapter([])
    with pytest.raises(ValueError):
        CommodityObservationAdapter([
            observation(provider="world_bank"),
            observation(asset="uranium", provider="eia"),
        ])


def test_fred_catalog_has_unique_series_and_explicit_freshness() -> None:
    config = yaml.safe_load(open("config/metals/fred_series.yaml", encoding="utf-8"))
    series = config["series"]
    identifiers = [item["series_id"] for item in series]
    assert len(series) == 12
    assert len(identifiers) == len(set(identifiers))
    assert {"DFII10", "DGS10", "T10YIE", "CPIAUCSL", "DTWEXBGS", "VIXCLS"} <= set(identifiers)
    assert all(item["maximum_age_days"] > 0 for item in series)
    assert all(item["frequency"] in {"daily", "weekly", "monthly"} for item in series)
