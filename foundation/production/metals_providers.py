"""Policy-controlled Metals provider collection and universal ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from time import sleep as _sleep
from typing import Callable, Iterable, Sequence, TypeVar

from .integration import ExternalDataRecord, IngestionPolicy, NormalizedDataBatch, ingest_provider
from .metals_registry import canonical_metals_asset_id
from .providers import CommodityObservation, ProviderError

T = TypeVar("T")


@dataclass(frozen=True)
class ProviderCollectionPolicy:
    maximum_attempts: int = 3
    initial_backoff: timedelta = timedelta(seconds=2)
    backoff_multiplier: int = 2
    maximum_age: timedelta = timedelta(days=45)

    def __post_init__(self) -> None:
        if (
            self.maximum_attempts < 1
            or self.initial_backoff < timedelta(0)
            or self.backoff_multiplier < 1
            or self.maximum_age <= timedelta(0)
        ):
            raise ValueError("provider collection policy values are outside permitted bounds")

    def delay_after(self, attempt: int) -> timedelta:
        return self.initial_backoff * (self.backoff_multiplier ** max(0, attempt - 1))


@dataclass(frozen=True)
class ProviderCollectionResult:
    attempts: int
    observations: tuple[CommodityObservation, ...]
    collected_at: datetime


def collect_with_policy(
    operation: Callable[[], T | Sequence[T]],
    policy: ProviderCollectionPolicy,
    *,
    as_of: datetime,
    pause: Callable[[float], None] = _sleep,
) -> ProviderCollectionResult:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    last_error: ProviderError | None = None
    for attempt in range(1, policy.maximum_attempts + 1):
        try:
            value = operation()
            values = tuple(value) if isinstance(value, (tuple, list)) else (value,)
            if not values or not all(isinstance(item, CommodityObservation) for item in values):
                raise ProviderError("provider returned invalid commodity observations")
            _validate_freshness(values, as_of, policy.maximum_age)
            return ProviderCollectionResult(attempt, values, as_of)
        except ProviderError as exc:
            last_error = exc
            if attempt < policy.maximum_attempts:
                pause(policy.delay_after(attempt).total_seconds())
    raise ProviderError(
        f"provider collection failed after {policy.maximum_attempts} attempt(s): "
        f"{type(last_error).__name__}"
    ) from last_error


def _validate_freshness(
    observations: Iterable[CommodityObservation],
    as_of: datetime,
    maximum_age: timedelta,
) -> None:
    for observation in observations:
        observed = datetime.combine(observation.observation_date, time.min, timezone.utc)
        reference = as_of.astimezone(timezone.utc)
        if observed > reference:
            raise ProviderError(f"{observation.series_id} observation is in the future")
        if reference - observed > maximum_age:
            raise ProviderError(f"{observation.series_id} observation exceeds maximum age")


class CommodityObservationAdapter:
    def __init__(self, observations: Sequence[CommodityObservation]):
        self._observations = tuple(observations)
        providers = {item.provider for item in self._observations}
        if not self._observations or len(providers) != 1:
            raise ValueError("commodity batch must contain one non-empty provider lineage")
        self.provider_id = next(iter(providers))

    def fetch(self) -> Iterable[ExternalDataRecord]:
        for item in self._observations:
            observed = datetime.combine(item.observation_date, time.min, timezone.utc)
            yield ExternalDataRecord(
                record_id=f"{item.provider}:{item.series_id}:{item.observation_date.isoformat()}",
                provider=item.provider,
                observed_at=observed,
                asset_id=canonical_metals_asset_id(item.asset),
                values={"price": Decimal(item.value)},
                source_reference=item.series_id,
            )


def ingest_commodity_observations(
    result: ProviderCollectionResult,
    policy: ProviderCollectionPolicy,
) -> NormalizedDataBatch:
    adapter = CommodityObservationAdapter(result.observations)
    return ingest_provider(
        adapter,
        IngestionPolicy(
            as_of=result.collected_at,
            maximum_age=policy.maximum_age,
            required_metrics=("price",),
        ),
    )
