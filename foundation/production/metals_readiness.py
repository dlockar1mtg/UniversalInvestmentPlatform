"""Fail-closed operational readiness projection for the Metals integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

import pandas as pd

from exchange.metals.adapter.native_surfaces import BRIDGE_SURFACES, load_bridge_surface
from exchange.metals.adapter.parity import certify_metals_parity

from .metals_providers import (
    ProviderCollectionPolicy,
    collect_with_policy,
    ingest_commodity_observations,
)
from .metals_registry import load_metals_registry, validate_adapter_crosswalk
from .metals_vehicles import VehicleCandidate, select_metals_vehicles
from .providers import EIAUraniumProvider, WorldBankCommodityProvider


def _component(name: str, operation: Callable[[], Mapping[str, object]]) -> dict:
    try:
        detail = dict(operation())
        return {"name": name, "status": "PASS", "detail": detail}
    except Exception as exc:
        return {
            "name": name,
            "status": "FAILED",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def summarize_metals_readiness(
    components: list[dict],
    *,
    generated_at: datetime,
) -> dict:
    if generated_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    failed = [item["name"] for item in components if item.get("status") != "PASS"]
    return {
        "status": "PASS" if not failed and components else "FAILED",
        "ready": bool(components) and not failed,
        "generated_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "component_count": len(components),
        "failed_components": failed,
        "components": components,
    }


def evaluate_metals_readiness(
    metals_root: str | Path,
    package_root: str | Path,
    *,
    universal_root: str | Path = Path.cwd(),
    as_of: datetime | None = None,
    maximum_package_age: timedelta = timedelta(days=45),
    include_live_providers: bool = True,
) -> dict:
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    metals = Path(metals_root)
    package = Path(package_root)
    universal = Path(universal_root)
    exports = metals / "data" / "exports"
    adapter_config = universal / "exchange" / "metals" / "config" / "adapter_config.json"

    def registry_check() -> Mapping[str, object]:
        registry = load_metals_registry(universal / "config" / "metals")
        validate_adapter_crosswalk(registry, adapter_config)
        return {"assets": len(registry.assets), "vehicles": len(registry.vehicles)}

    def bridge_check() -> Mapping[str, object]:
        counts = {
            name: len(load_bridge_surface(exports, name))
            for name in BRIDGE_SURFACES
        }
        return {"surfaces": len(counts), "records": sum(counts.values()), "counts": counts}

    def package_check() -> Mapping[str, object]:
        import json

        summary = json.loads((package / "package_summary.json").read_text(encoding="utf-8"))
        if summary.get("validation_status") != "PASS":
            raise RuntimeError("package validation status is not PASS")
        generated = datetime.fromisoformat(str(summary["generated_at_utc"]).replace("Z", "+00:00"))
        age = now.astimezone(timezone.utc) - generated.astimezone(timezone.utc)
        if age < timedelta(0) or age > maximum_package_age:
            raise RuntimeError("package is outside the permitted freshness window")
        status = pd.read_csv(package / "platform_status.csv")
        if status.empty or "status" not in status or not status["status"].astype(str).str.upper().eq("READY").all():
            raise RuntimeError("Metals platform status is not READY")
        return {
            "package_id": summary.get("package_id"),
            "age_seconds": int(age.total_seconds()),
            "platform_status": "READY",
        }

    def parity_check() -> Mapping[str, object]:
        report = certify_metals_parity(metals, package)
        return {"package_id": report["package_id"], "checks": len(report["checks"])}

    def vehicle_check() -> Mapping[str, object]:
        cases = {
            "gold": (("GLD", 95), ("IAU", 70), ("SGOL", 65)),
            "silver": (("SLV", 85), ("SIVR", 65)),
            "copper": (("COPX", 95), ("CPER", 30)),
            "uranium": (("URA", 90), ("URNM", 50)),
            "platinum": (("PPLT", 75),),
            "tactical_reserve": (("BIL", 80),),
        }
        for asset, values in cases.items():
            result = select_metals_vehicles(
                asset,
                [VehicleCandidate(ticker, score) for ticker, score in values],
            )
            if result.total_share_pct != 100:
                raise RuntimeError(f"vehicle allocation does not total 100 for {asset}")
        return {"scenarios": len(cases)}

    components = [
        _component("registry", registry_check),
        _component("bridge_handoff", bridge_check),
        _component("package", package_check),
        _component("model_parity", parity_check),
        _component("vehicle_constraints", vehicle_check),
    ]

    if include_live_providers:
        def provider_check() -> Mapping[str, object]:
            providers = (
                (
                    "eia",
                    EIAUraniumProvider().latest,
                    ProviderCollectionPolicy(
                        maximum_attempts=3,
                        initial_backoff=timedelta(seconds=2),
                        maximum_age=timedelta(days=730),
                    ),
                ),
                (
                    "world_bank",
                    WorldBankCommodityProvider().latest,
                    ProviderCollectionPolicy(
                        maximum_attempts=3,
                        initial_backoff=timedelta(seconds=2),
                        maximum_age=timedelta(days=75),
                    ),
                ),
            )
            counts = {}
            for name, operation, policy in providers:
                result = collect_with_policy(operation, policy, as_of=now)
                counts[name] = len(ingest_commodity_observations(result, policy).records)
            return {"providers": len(counts), "records": sum(counts.values()), "counts": counts}

        components.append(_component("official_providers", provider_check))

    return summarize_metals_readiness(components, generated_at=now)
