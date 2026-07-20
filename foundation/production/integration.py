"""Deterministic external-data ingestion and normalization boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Iterable, Mapping, Protocol


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values, key=str)})


@dataclass(frozen=True)
class ExternalDataRecord:
    record_id: str
    provider: str
    observed_at: datetime
    asset_id: str
    values: Mapping[str, object]
    source_reference: str

    def __post_init__(self) -> None:
        if not all((self.record_id.strip(), self.provider.strip(), self.asset_id.strip(), self.source_reference.strip())):
            raise ValueError("record, provider, asset, and source identities are required")
        if self.observed_at.tzinfo is None or not self.values:
            raise ValueError("observed_at must be timezone-aware and values must not be empty")
        normalized = {}
        for key, value in self.values.items():
            number = Decimal(str(value))
            if not number.is_finite():
                raise ValueError(f"values.{key} must be finite")
            normalized[str(key)] = number
        object.__setattr__(self, "values", _freeze(normalized))


class ExternalDataProvider(Protocol):
    provider_id: str

    def fetch(self) -> Iterable[ExternalDataRecord]: ...


@dataclass(frozen=True)
class IngestionPolicy:
    as_of: datetime
    maximum_age: timedelta = timedelta(days=1)
    required_metrics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.maximum_age <= timedelta(0):
            raise ValueError("as_of must be aware and maximum_age must be positive")


@dataclass(frozen=True)
class NormalizedDataBatch:
    provider: str
    records: tuple[ExternalDataRecord, ...]
    batch_fingerprint: str


def ingest_provider(provider: ExternalDataProvider, policy: IngestionPolicy) -> NormalizedDataBatch:
    records = tuple(provider.fetch())
    identifiers = [item.record_id for item in records]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("provider returned duplicate record_id values")
    if any(item.provider != provider.provider_id for item in records):
        raise ValueError("record provider lineage does not match adapter")
    for item in records:
        if item.observed_at > policy.as_of:
            raise ValueError("record observation cannot be in the future")
        if policy.as_of - item.observed_at > policy.maximum_age:
            raise ValueError("record exceeds maximum data age")
        missing = set(policy.required_metrics) - set(item.values)
        if missing:
            raise ValueError(f"record missing required metrics: {', '.join(sorted(missing))}")
    ordered = tuple(sorted(records, key=lambda item: (item.asset_id, item.observed_at, item.record_id)))
    payload = [{
        "asset_id": item.asset_id, "observed_at": item.observed_at.isoformat(),
        "provider": item.provider, "record_id": item.record_id,
        "source_reference": item.source_reference,
        "values": {key: str(value) for key, value in item.values.items()},
    } for item in ordered]
    fingerprint = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return NormalizedDataBatch(provider.provider_id, ordered, fingerprint)
