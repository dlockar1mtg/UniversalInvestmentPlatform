"""Build a versioned, read-only presentation bundle from certified UIP authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .read_model_contracts import (
    PresentationReadModelContract,
    load_presentation_contract,
    validate_authority_schema,
)

PUBLICATION_VERSION = "1.0.0"
SOURCE_CLASSIFICATION = "AUTHORITATIVE_MULTI_DOMAIN_PRODUCTION_STATE_R3_CERTIFIED"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class PresentationRecord:
    record_type: str
    domain_id: str
    asset_id: str | None
    record_key: str
    payload: Mapping[str, Any]

    def canonical(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "domain_id": self.domain_id,
            "asset_id": self.asset_id,
            "record_key": self.record_key,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class PresentationPublication:
    publication_id: str
    publication_version: str
    source_database_sha256: str
    source_database_classification: str
    published_at_utc: str
    publication_status: str
    records: tuple[PresentationRecord, ...]

    @property
    def content_fingerprint(self) -> str:
        document = {
            "publication_version": self.publication_version,
            "source_database_sha256": self.source_database_sha256,
            "source_database_classification": self.source_database_classification,
            "records": [item.canonical() for item in self.records],
        }
        return hashlib.sha256(_canonical_json(document).encode("utf-8")).hexdigest()


def _rows(connection: Any, sql: str, parameters: Iterable[Any] = ()) -> tuple[dict[str, Any], ...]:
    cursor = connection.execute(sql, list(parameters))
    names = [str(item[0]) for item in cursor.description]
    return tuple(dict(zip(names, row)) for row in cursor.fetchall())


def _record(record_type: str, domain_id: str, asset_id: str | None, key: str, payload: Mapping[str, Any]) -> PresentationRecord:
    return PresentationRecord(record_type, domain_id, asset_id, key, dict(payload))


def _generic_records(connection: Any, domain_id: str) -> list[PresentationRecord]:
    records: list[PresentationRecord] = []

    assets = _rows(connection, """
        SELECT universal_asset_id, platform_asset_id, asset_name, asset_symbol,
               asset_class, asset_subclass, currency, investable, active,
               last_observed_date, last_updated_at_utc, source_system,
               metadata_json, run_id, _import_id, _package_id, _manifest_sha256,
               _imported_at_utc
        FROM asset_master_current
        WHERE lower(platform_id)=?
        ORDER BY universal_asset_id
    """, [domain_id])
    for row in assets:
        asset_id = str(row["universal_asset_id"])
        row["current_price_usd"] = None
        row["current_price_authority_available"] = False
        row["current_price_authority_state"] = "NOT_BOUND_IN_DASH_READ_1_GENERIC_SURFACE"
        records.append(_record("asset", domain_id, asset_id, asset_id, row))

    recommendations = _rows(connection, """
        SELECT universal_asset_id, recommendation, normalized_score,
               confidence_score, rationale, risk_summary, time_horizon_months,
               source_system, model_version, generated_at_utc, metadata_json,
               run_id, _import_id, _package_id, _manifest_sha256, _imported_at_utc
        FROM recommendations_current
        WHERE lower(platform_id)=?
        ORDER BY universal_asset_id
    """, [domain_id])
    for row in recommendations:
        asset_id = str(row["universal_asset_id"])
        row["native_recommendation"] = row["recommendation"]
        row["cross_domain_rank"] = None
        records.append(_record("recommendation", domain_id, asset_id, asset_id, row))

    forecasts = _rows(connection, """
        SELECT universal_asset_id, forecast_origin_date, forecast_horizon_months,
               forecast_method, point_forecast, lower_bound, upper_bound,
               expected_return, probability_positive, confidence_score,
               scenario, source_system, model_version, generated_at_utc,
               metadata_json, run_id, _import_id, _package_id, _manifest_sha256,
               _imported_at_utc
        FROM forecasts_current
        WHERE lower(platform_id)=?
        ORDER BY universal_asset_id, forecast_horizon_months, forecast_method
    """, [domain_id])
    for row in forecasts:
        asset_id = str(row["universal_asset_id"])
        key = f"{asset_id}|{row['forecast_horizon_months']}|{row['forecast_method']}"
        records.append(_record("forecast", domain_id, asset_id, key, row))

    risks = _rows(connection, """
        SELECT universal_asset_id, risk_score, risk_level, volatility,
               downside_volatility, maximum_drawdown, value_at_risk,
               expected_shortfall, beta, liquidity_score, concentration_score,
               source_system, model_version, generated_at_utc, notes,
               metadata_json, run_id, _import_id, _package_id, _manifest_sha256,
               _imported_at_utc
        FROM risk_metrics_current
        WHERE lower(platform_id)=?
        ORDER BY universal_asset_id
    """, [domain_id])
    for row in risks:
        asset_id = str(row["universal_asset_id"])
        records.append(_record("risk", domain_id, asset_id, asset_id, row))

    return records


SECRET_LAIR_MODEL_STATUS = {
    "BUY": "BUY_CANDIDATE_NOW",
    "WAIT": "WAIT_FOR_LISTING_DISCOUNT",
    "NO_PRICE": "NO_CURRENT_MARKET_PRICE",
}


def _model_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def apply_secret_lair_model_decisions(records: list[PresentationRecord]) -> int:
    """Add Secret Lair v2 model decisions to MTG recommendation records, when enabled.

    The certified native authority (native_purchase_status, native_rank, native_rank_type,
    purchase_semantic) is preserved unchanged, as the MTG parity contract requires; the daily
    v2 decision travels beside it in explicit model_* fields, which consumers prefer when present.
    Enabled by UIP_MTG_SECRET_LAIR_V2_ENABLED=1 with UIP_MTG_SECRET_LAIR_V2_PATH set.
    """
    path = str(os.environ.get("UIP_MTG_SECRET_LAIR_V2_PATH", "")).strip()
    if os.environ.get("UIP_MTG_SECRET_LAIR_V2_ENABLED") != "1" or not path:
        return 0
    from .mtg_secret_lair_v2_projection import load_decisions

    decisions, summary = load_decisions(Path(path))
    applied = 0
    for record in records:
        if record.record_type != "recommendation" or not str(record.asset_id).startswith("SECRET_LAIR_V1_1|"):
            continue
        native = str(record.asset_id).split("|", 1)[1]
        decision = decisions.get(native) or {}
        call = decision.get("call") or "NO_PRICE"
        rank = str(decision.get("rank") or "").strip()
        record.payload.update({
            "model_version": "secret-lair-v2",
            "model_call": call,
            "model_purchase_status": SECRET_LAIR_MODEL_STATUS[call],
            "model_rank": int(rank) if rank.isdigit() else None,
            "model_ranked_products": int(decision["ranked_products"]) if str(decision.get("ranked_products") or "").isdigit() else None,
            "model_rank_type": "SECRET_LAIR_V2_EXPECTED_NET_RETURN_6M",
            "model_price_usd": decision.get("market_price") or None,
            "model_note": decision.get("note") or ("" if decision else "NOT_IN_DAILY_PRICE_FEED"),
            "model_as_of": decision.get("as_of") or summary.get("as_of"),
            "model_buy_price_usd": _model_number(decision.get("buy_price")),
            "model_buy_basis": decision.get("buy_price_basis") or None,
            "model_gap": _model_number(decision.get("gap")),
            "model_expected_return_6m": _model_number(decision.get("expected_return_6m")),
            "model_expected_net_return_6m": _model_number(decision.get("expected_net_return_6m")),
            "model_prob_profit_6m": _model_number(decision.get("prob_profit_6m")),
            "model_tcgplayer_product_id": str(decision.get("tcgplayer_product_id") or "").strip() or None,
            "model_market_index": list(summary.get("market_index") or [])[-24:],
        })
        applied += 1
    return applied


PRECOLLECTOR_MODEL_STATUS = {"BUY": "BUY_CANDIDATE_NOW", "HOLD": "HOLD_NO_BUY_SIGNAL", "NO_PRICE": "NO_CURRENT_MARKET_PRICE"}


def apply_precollector_model_decisions(records: list[PresentationRecord]) -> int:
    """Add Pre-Collector v2 model decisions (price tiers) to MTG recommendation records, when enabled.

    As for Secret Lair v2, the certified native authority is preserved unchanged and the daily
    decision travels beside it in model_* fields. Enabled by UIP_MTG_PRECOLLECTOR_V2_ENABLED=1 with
    UIP_MTG_PRECOLLECTOR_V2_PATH set to the MTG precollector_v2_decisions.csv; its .json summary
    (tier history) and precollector_v2_history.json (monthly prices) are read from beside it.
    """
    import csv as _csv
    import json as _json

    path = str(os.environ.get("UIP_MTG_PRECOLLECTOR_V2_PATH", "")).strip()
    if os.environ.get("UIP_MTG_PRECOLLECTOR_V2_ENABLED") != "1" or not path:
        return 0
    decisions_path = Path(path)
    with decisions_path.open(newline="", encoding="utf-8") as handle:
        decisions = {str(r.get("tcgplayer_product_id") or "").strip(): r for r in _csv.DictReader(handle)}
    summary_path = decisions_path.with_suffix(".json")
    summary = _json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
    history_path = decisions_path.with_name("precollector_v2_history.json")
    history = _json.loads(history_path.read_text(encoding="utf-8")) if history_path.is_file() else {}
    tiers = summary.get("tier_history") or {}
    applied = 0
    for record in records:
        asset = str(record.asset_id)
        if record.record_type != "recommendation" or not asset.startswith("PRE_COLLECTOR_V1|"):
            continue
        product = asset.split("tcgplayer:", 1)[1].strip() if "tcgplayer:" in asset else ""
        decision = decisions.get(product) or {}
        call = decision.get("call") or "NO_PRICE"
        if call not in PRECOLLECTOR_MODEL_STATUS:
            raise ValueError(f"Pre-Collector v2 decision has an unknown call {call!r} for {asset}")
        tier = str(decision.get("tier") or "").strip()
        rank = str(decision.get("rank") or "").strip()
        ranked = str(decision.get("ranked_boxes") or "").strip()
        record.payload.update({
            "model_version": "precollector-v2",
            "model_call": call,
            "model_purchase_status": PRECOLLECTOR_MODEL_STATUS[call],
            "model_rank": int(rank) if rank.isdigit() else None,
            "model_ranked_products": int(ranked) if ranked.isdigit() else None,
            "model_rank_type": "PRECOLLECTOR_V2_PRICE_TIER",
            "model_tier": int(tier) if tier.isdigit() else None,
            "model_price_usd": _model_number(decision.get("price")),
            "model_price_date": decision.get("price_date") or None,
            "model_price_source": decision.get("price_source") or None,
            "model_release_date": decision.get("release_date") or None,
            "model_note": decision.get("note") or ("" if decision else "NOT_IN_PRICE_FEED"),
            "model_as_of": decision.get("as_of") or summary.get("as_of"),
            "model_tcgplayer_product_id": product or None,
            "model_tier_history": tiers.get(tier) if tier else None,
            "model_buy_tiers": summary.get("buy_tiers"),
            "model_price_history": list(history.get(product, []))[-36:],
        })
        applied += 1
    return applied


def _mtg_records(connection: Any) -> list[PresentationRecord]:
    records: list[PresentationRecord] = []
    rows = _rows(connection, """
        SELECT mtg_asset_id, mtg_lane, native_asset_id, product_name,
               lane_authority_state, current_price_usd,
               current_price_authority_available, forecast_authority_available,
               forecast_1y_price_usd, forecast_1y_return,
               risk_authority_available, native_rank, native_rank_type,
               native_purchase_status, purchase_semantic, evidence_state,
               actionability_state, execution_ready_purchase_certified,
               manual_execution_price_check_required, native_authority_pointer,
               native_authority_sha256, snapshot_population_is_permanent,
               automatic_purchase_execution, _import_id, _package_id,
               _source_platform, _source_filename, _source_row_number,
               _manifest_sha256, _imported_at_utc
        FROM mtg_native_authority_current
        ORDER BY mtg_asset_id
    """)
    for row in rows:
        asset_id = str(row["mtg_asset_id"])
        records.append(_record("asset", "mtg", asset_id, asset_id, {
            "universal_asset_id": asset_id,
            "native_asset_id": row["native_asset_id"],
            "asset_name": row["product_name"],
            "asset_subclass": row["mtg_lane"],
            "current_price_usd": row["current_price_usd"],
            "current_price_authority_available": row["current_price_authority_available"],
            "lane_authority_state": row["lane_authority_state"],
            "_import_id": row["_import_id"],
            "_package_id": row["_package_id"],
            "_manifest_sha256": row["_manifest_sha256"],
            "_imported_at_utc": row["_imported_at_utc"],
        }))
        records.append(_record("recommendation", "mtg", asset_id, asset_id, {
            "universal_asset_id": asset_id,
            "native_purchase_status": row["native_purchase_status"],
            "purchase_semantic": row["purchase_semantic"],
            "native_rank": row["native_rank"],
            "native_rank_type": row["native_rank_type"],
            "evidence_state": row["evidence_state"],
            "actionability_state": row["actionability_state"],
            "execution_ready_purchase_certified": row["execution_ready_purchase_certified"],
            "manual_execution_price_check_required": row["manual_execution_price_check_required"],
            "automatic_purchase_execution": row["automatic_purchase_execution"],
            "native_authority_pointer": row["native_authority_pointer"],
            "native_authority_sha256": row["native_authority_sha256"],
            "_import_id": row["_import_id"],
            "_package_id": row["_package_id"],
            "_manifest_sha256": row["_manifest_sha256"],
            "_imported_at_utc": row["_imported_at_utc"],
        }))
        if row["forecast_authority_available"]:
            records.append(_record("forecast", "mtg", asset_id, f"{asset_id}|12|mtg_native_1y", {
                "universal_asset_id": asset_id,
                "forecast_horizon_months": 12,
                "forecast_method": "mtg_native_1y",
                "point_forecast": row["forecast_1y_price_usd"],
                "expected_return": row["forecast_1y_return"],
                "forecast_authority_available": True,
                "_import_id": row["_import_id"],
                "_package_id": row["_package_id"],
                "_manifest_sha256": row["_manifest_sha256"],
                "_imported_at_utc": row["_imported_at_utc"],
            }))
        records.append(_record("native_authority", "mtg", asset_id, asset_id, row))
    apply_secret_lair_model_decisions(records)
    apply_precollector_model_decisions(records)
    return records



def _mtg_premium_records_from_environment() -> list[PresentationRecord]:
    """
    Add certified MTG premium research only when an explicit
    external sidecar path is supplied.

    No filesystem discovery, repository search, sidecar copy,
    database ingestion, or publication activation occurs here.
    """
    # Secret Lair model v2 replaces the August certified research when enabled together with the
    # MTG delivery overlay (MTG_SECRET_LAIR_V2); otherwise the certified sidecar path below is used.
    v2_path = str(os.environ.get("UIP_MTG_SECRET_LAIR_V2_PATH", "")).strip()
    export_path = str(os.environ.get("UIP_MTG_EXPORT_PAYLOAD_PATH", "")).strip()
    if os.environ.get("UIP_MTG_SECRET_LAIR_V2_ENABLED") == "1" and v2_path and export_path:
        from .mtg_secret_lair_v2_projection import build_secret_lair_v2_records

        return build_secret_lair_v2_records(Path(v2_path), Path(export_path))

    raw_path = str(
        os.environ.get(
            "UIP_MTG_PREMIUM_SIDECAR_PATH",
            "",
        )
    ).strip()

    if not raw_path:
        return []

    sidecar_path = Path(raw_path)

    if not sidecar_path.is_file():
        raise RuntimeError(
            f"Explicit MTG premium sidecar is missing: {sidecar_path}"
        )

    from .mtg_premium_projection import (
        EXPECTED_MTG_HEAD,
        build_mtg_premium_records,
    )

    return build_mtg_premium_records(
        sidecar_path,
        mtg_head=EXPECTED_MTG_HEAD,
    )


def _mtg_lane_native_research_records_from_environment() -> list[PresentationRecord]:
    """
    Append certified Collector / Pre-Collector research only when all
    four explicit external sidecar paths are supplied.

    No filesystem discovery, source copying, database ingestion,
    recommendation recalculation, or publication activation occurs.
    """
    environment_names = (
        "UIP_MTG_COLLECTOR_RESEARCH_PATH",
        "UIP_MTG_COLLECTOR_HORIZON_RESEARCH_PATH",
        "UIP_MTG_PRECOLLECTOR_RESEARCH_PATH",
        "UIP_MTG_PRECOLLECTOR_SCENARIO_RESEARCH_PATH",
    )

    raw = {
        name: str(
            os.environ.get(
                name,
                "",
            )
        ).strip()
        for name in environment_names
    }

    present = {
        name
        for name, value in raw.items()
        if value
    }

    if not present:
        return []

    if len(present) != len(environment_names):
        missing = sorted(
            set(environment_names)
            - present
        )

        raise RuntimeError(
            "Partial MTG lane-native research sidecar configuration "
            f"is forbidden; missing={missing}"
        )

    paths = {
        name: Path(value)
        for name, value in raw.items()
    }

    for name, sidecar_path in paths.items():
        if not sidecar_path.is_file():
            raise RuntimeError(
                "Explicit MTG lane-native research sidecar is missing: "
                f"{name}={sidecar_path}"
            )

    from .mtg_lane_native_research_projection import (
        EXPECTED_MTG_HEAD,
        build_mtg_lane_native_research_records,
    )

    return build_mtg_lane_native_research_records(
        paths["UIP_MTG_COLLECTOR_RESEARCH_PATH"],
        paths["UIP_MTG_COLLECTOR_HORIZON_RESEARCH_PATH"],
        paths["UIP_MTG_PRECOLLECTOR_RESEARCH_PATH"],
        paths["UIP_MTG_PRECOLLECTOR_SCENARIO_RESEARCH_PATH"],
        mtg_head=EXPECTED_MTG_HEAD,
    )

def _domain_health_records(connection: Any) -> list[PresentationRecord]:
    rows = _rows(connection, """
        SELECT domain_id, domain_name, platform_id, ownership_type,
               source_repository, publication_boundary, certification_state,
               dynamic_asset_universe, native_semantics_authoritative,
               cross_asset_ranking_authorized, automatic_execution_authorized,
               registry_version, platform_name, platform_version,
               adapter_version, contract_version, import_registry_status,
               last_package_id, last_run_id, last_import_id,
               last_import_status, last_imported_at_utc,
               last_data_as_of_date, warning_count, error_count, status_message
        FROM universal_domain_operational_status
        ORDER BY domain_id
    """)
    return [
        _record("domain_health", str(row["domain_id"]), None, str(row["domain_id"]), row)
        for row in rows
    ]


def build_presentation_publication(
    repository_root: Path,
    database_path: Path,
    connection: Any,
    *,
    publication_id: str | None = None,
    published_at_utc: str | None = None,
    contract: PresentationReadModelContract | None = None,
) -> PresentationPublication:
    """Project current certified analytical state without mutating its source."""
    contract = contract or load_presentation_contract(repository_root)
    validate_authority_schema(connection, contract)
    records: list[PresentationRecord] = []
    records.extend(_domain_health_records(connection))
    records.extend(_generic_records(connection, "crypto"))
    records.extend(_generic_records(connection, "metals"))
    records.extend(_mtg_records(connection))
    records.extend(_mtg_premium_records_from_environment())
    records.extend(_mtg_lane_native_research_records_from_environment())
    records.sort(key=lambda item: (item.record_type, item.domain_id, item.asset_id or "", item.record_key))
    return PresentationPublication(
        publication_id=publication_id or str(uuid4()),
        publication_version=PUBLICATION_VERSION,
        source_database_sha256=sha256_file(database_path),
        source_database_classification=SOURCE_CLASSIFICATION,
        published_at_utc=published_at_utc or datetime.now(timezone.utc).isoformat(),
        publication_status="STAGED",
        records=tuple(records),
    )
