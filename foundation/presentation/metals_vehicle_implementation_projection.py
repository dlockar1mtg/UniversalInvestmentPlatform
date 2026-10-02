"""Project certified Metals implementation choices into commodity presentation records.

This module is presentation-only. It consumes committed governed authorities and emits
records suitable for inclusion in a rich presentation candidate. It performs no source
collection, database write, allocation, sizing, or execution.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from foundation.presentation.publication_model import PresentationRecord

DOMAIN_ID = "metals"
RECORD_TYPE = "metals_vehicle_implementation"

AUTH_PATH = Path("config/presentation/metals_vehicle_presentation_authorization_v1.json")
RANKING_PATH = Path("config/presentation/metals_vehicle_ranking_evidence_v1.json")
COMPONENT_PATH = Path("config/presentation/metals_vehicle_ranking_component_evidence_v1.json")
COST_PATH = Path("config/presentation/metals_vehicle_cost_evidence_snapshot_v1.json")
VEHICLES_PATH = Path("config/metals/vehicles.json")

EXPECTED_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_PRESENTATION_AUTHORIZATION_V1"
EXPECTED_RANKING_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_RANKING_EVIDENCE_V1"
EXPECTED_COMPONENT_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_RANKING_COMPONENT_EVIDENCE_V1"
EXPECTED_COST_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_COST_EVIDENCE_SNAPSHOT_V1"
PREFERRED_LABEL = "PREFERRED_IMPLEMENTATION_CANDIDATE"
ONLY_LABEL = "ONLY_REGISTERED_IMPLEMENTATION"


def _load(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise RuntimeError(f"Required Metals presentation authority is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object in {path}")
    return payload


def _unique_index(rows: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key, "")).strip()
        if not value:
            raise RuntimeError(f"Blank {key} in {label}")
        if value in result:
            raise RuntimeError(f"Duplicate {key}={value!r} in {label}")
        result[value] = row
    return result


def build_metals_vehicle_implementation_records(repository_root: Path) -> list[PresentationRecord]:
    """Emit exactly one implementation record per registered ranked Metals vehicle."""
    root = repository_root.resolve()
    auth = _load(root, AUTH_PATH)
    ranking = _load(root, RANKING_PATH)
    component = _load(root, COMPONENT_PATH)
    cost = _load(root, COST_PATH)
    registry = _load(root, VEHICLES_PATH)
    # The implementation universe is whatever the registry lists as enabled and not a reserve.
    expected_tickers = {
        str(row.get("ticker", "")).strip()
        for row in registry.get("vehicles", [])
        if bool(row.get("enabled")) and row.get("role") != "reserve"
    }

    if auth.get("authority_id") != EXPECTED_AUTHORITY:
        raise RuntimeError("Unexpected Metals vehicle presentation authorization authority")
    if ranking.get("authority_id") != EXPECTED_RANKING_AUTHORITY:
        raise RuntimeError("Unexpected Metals vehicle ranking evidence authority")
    if component.get("authority_id") != EXPECTED_COMPONENT_AUTHORITY:
        raise RuntimeError("Unexpected Metals vehicle ranking component evidence authority")
    if cost.get("authority_id") != EXPECTED_COST_AUTHORITY:
        raise RuntimeError("Unexpected Metals vehicle cost evidence authority")
    if auth.get("ranking_evidence_authority_id") != ranking.get("authority_id"):
        raise RuntimeError("Presentation authorization is not bound to certified ranking evidence")
    if auth.get("ranking_source_artifact_digest") != ranking.get("source_artifact_digest"):
        raise RuntimeError("Presentation authorization ranking digest does not match certified evidence")
    if component.get("ranking_authority_id") != ranking.get("ranking_authority_id"):
        raise RuntimeError("Component evidence ranking authority differs from ranking certificate")
    if component.get("ranking_methodology_version") != ranking.get("ranking_methodology_version"):
        raise RuntimeError("Component evidence methodology differs from ranking certificate")
    if component.get("source_artifact_digest") != ranking.get("source_artifact_digest"):
        raise RuntimeError("Component evidence artifact digest differs from ranking certificate")
    if component.get("status") != "METALS_VEHICLE_RANKING_COMPONENT_EVIDENCE_CERTIFIED":
        raise RuntimeError("Metals vehicle component evidence is not certified")
    if component.get("presentation_only") is not True or component.get("ranking_recalculated") is not False:
        raise RuntimeError("Metals vehicle component evidence must be presentation-only and non-recalculated")
    if auth.get("central_publication_cron_restoration_authorized") is not False:
        raise RuntimeError("Metals vehicle projection refuses cron-restoration authority")
    if auth.get("automatic_execution_authorized") is not False:
        raise RuntimeError("Metals vehicle projection refuses automatic-execution authority")

    registered_rows = [
        dict(row)
        for row in registry.get("vehicles", [])
        if bool(row.get("enabled")) and str(row.get("ticker", "")).strip() in expected_tickers
    ]
    vehicles = _unique_index(registered_rows, "ticker", "Metals vehicle registry")
    costs = _unique_index([dict(row) for row in cost.get("vehicles", [])], "ticker", "Metals cost evidence")
    groups = _unique_index([dict(row) for row in ranking.get("groups", [])], "commodity_id", "Metals ranking evidence")
    component_groups = _unique_index([dict(row) for row in component.get("groups", [])], "commodity_id", "Metals ranking component evidence")
    authorizations = _unique_index([dict(row) for row in auth.get("commodities", [])], "commodity_id", "Metals presentation authorization")

    if set(vehicles) != expected_tickers:
        raise RuntimeError(f"Registered ranked Metals ticker set mismatch: {sorted(vehicles)}")
    if set(costs) != expected_tickers:
        raise RuntimeError(f"Certified Metals cost ticker set mismatch: {sorted(costs)}")
    if set(groups) != set(authorizations) or set(component_groups) != set(authorizations):
        raise RuntimeError("Ranking, component evidence, and presentation commodity groups differ")

    emitted: list[PresentationRecord] = []
    seen_tickers: set[str] = set()
    ranking_weights = dict(component.get("weights") or {})

    for commodity_id in sorted(authorizations):
        authorization = authorizations[commodity_id]
        ranking_group = groups[commodity_id]
        component_group = component_groups[commodity_id]
        ordered = list(authorization.get("certified_vehicle_order") or [])
        if ordered != list(ranking_group.get("certified_order") or []):
            raise RuntimeError(f"Certified vehicle order mismatch for {commodity_id}")
        if ordered != list(component_group.get("certified_order") or []):
            raise RuntimeError(f"Component evidence vehicle order mismatch for {commodity_id}")
        if not ordered:
            raise RuntimeError(f"Empty certified vehicle order for {commodity_id}")
        component_vehicles = _unique_index(
            [dict(row) for row in component_group.get("vehicles", [])],
            "ticker",
            f"Metals ranking component evidence {commodity_id}",
        )
        if set(component_vehicles) != set(ordered):
            raise RuntimeError(f"Component evidence ticker set mismatch for {commodity_id}")

        recommendation = str(authorization.get("recommendation", ""))
        tactical_state = str(authorization.get("tactical_state", ""))
        preferred = authorization.get("authorized_preferred_vehicle")
        authorized_label = authorization.get("authorized_label")
        scores = dict(ranking_group.get("scores") or {})

        if preferred is not None:
            if recommendation not in {"BUY", "STRONG_BUY"} or tactical_state != "TACTICAL_SUPPORTIVE":
                raise RuntimeError(f"Preferred vehicle would override upstream commodity state for {commodity_id}")
            if preferred != ranking_group.get("certified_leader"):
                raise RuntimeError(f"Authorized preferred vehicle is not the certified leader for {commodity_id}")
            if authorized_label != PREFERRED_LABEL:
                raise RuntimeError(f"Unexpected preferred label for {commodity_id}")
        elif authorized_label == PREFERRED_LABEL:
            raise RuntimeError(f"Preferred label exists without an authorized preferred vehicle for {commodity_id}")

        for rank, ticker in enumerate(ordered, start=1):
            if ticker in seen_tickers:
                raise RuntimeError(f"Vehicle {ticker} appears in more than one commodity group")
            seen_tickers.add(ticker)
            if ticker not in vehicles or ticker not in costs:
                raise RuntimeError(f"Missing governed implementation evidence for {ticker}")

            vehicle = vehicles[ticker]
            cost_row = costs[ticker]
            component_row = component_vehicles[ticker]
            certified_score = scores.get(ticker)
            if certified_score is not None and component_row.get("total_score") != certified_score:
                raise RuntimeError(f"Component evidence total score drifted for {ticker}")
            if certified_score is None and component_row.get("total_score") is not None:
                raise RuntimeError(f"Singleton vehicle {ticker} unexpectedly gained a competitive total score")

            label = None
            if preferred == ticker:
                label = PREFERRED_LABEL
            elif len(ordered) == 1 and authorized_label == ONLY_LABEL:
                label = ONLY_LABEL

            payload = {
                "authority_id": EXPECTED_AUTHORITY,
                "ranking_evidence_authority_id": EXPECTED_RANKING_AUTHORITY,
                "ranking_component_evidence_authority_id": EXPECTED_COMPONENT_AUTHORITY,
                "commodity_id": commodity_id,
                "ticker": ticker,
                "vehicle_id": vehicle["vehicle_id"],
                "vehicle_name": vehicle["name"],
                "vehicle_type": vehicle["vehicle_type"],
                "role": vehicle["role"],
                "official_url": vehicle["official_url"],
                "certified_rank_within_commodity": rank,
                "certified_implementation_score": certified_score,
                "ranking_weights": ranking_weights,
                "exposure_fidelity_score": component_row.get("exposure_fidelity_score"),
                "cost_efficiency_score": component_row.get("cost_efficiency_score"),
                "liquidity_implementation_friction_score": component_row.get("liquidity_implementation_friction_score"),
                "risk_efficiency_score": component_row.get("risk_efficiency_score"),
                "average_dollar_volume_usd": component_row.get("average_dollar_volume_usd"),
                "bid_ask_spread_bps": component_row.get("bid_ask_spread_bps"),
                "volatility": component_row.get("volatility"),
                "downside_volatility": component_row.get("downside_volatility"),
                "maximum_drawdown_magnitude": component_row.get("maximum_drawdown_magnitude"),
                "value_at_risk": component_row.get("value_at_risk"),
                "expense_ratio_pct": cost_row.get("expense_ratio_pct"),
                "cost_basis": cost_row.get("cost_basis"),
                "cost_evidence_status": cost_row.get("status"),
                "source_authority": cost_row.get("source_authority"),
                "source_as_of": cost_row.get("source_as_of"),
                "presentation_label": label,
                "presentation_state": authorization.get("presentation_state"),
                "upstream_recommendation": recommendation,
                "upstream_tactical_state": tactical_state,
                "adjusted_expected_return_12m": authorization.get("adjusted_expected_return_12m"),
                "preferred_buy_label_suppressed": preferred is None and len(ordered) > 1,
                "ranking_may_not_override_commodity_recommendation": True,
                "automatic_execution_authorized": False,
                "portfolio_allocation_authorized": False,
                "position_sizing_authorized": False,
                "central_publication_cron_restoration_authorized": False,
            }
            emitted.append(
                PresentationRecord(
                    record_type=RECORD_TYPE,
                    domain_id=DOMAIN_ID,
                    asset_id=commodity_id,
                    record_key=f"{commodity_id}|{rank:02d}|{ticker}",
                    payload=payload,
                )
            )

    if seen_tickers != expected_tickers or len(emitted) != len(expected_tickers):
        raise RuntimeError("Metals vehicle implementation projection did not emit exact ranked universe")

    silver = [r for r in emitted if r.asset_id == "metals:commodity:silver"]
    if any(r.payload.get("presentation_label") == PREFERRED_LABEL for r in silver):
        raise RuntimeError("Defensive Silver may not receive a preferred implementation label")

    return emitted
