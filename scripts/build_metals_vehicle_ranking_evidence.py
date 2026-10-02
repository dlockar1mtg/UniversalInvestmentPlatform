"""Build the committed Metals vehicle ranking evidence from a ranking rehearsal.

Replaces the manual step that turned a four-factor ranking rehearsal into the three
files the dashboard projection reads:

  config/presentation/metals_vehicle_ranking_evidence_v1.json
  config/presentation/metals_vehicle_ranking_component_evidence_v1.json
  config/presentation/metals_vehicle_presentation_authorization_v1.json

The current files are used as templates, so their governance fields are preserved;
only the data (orders, scores, components, labels) and the source binding (run,
artifact, digest, methodology version) change. A preferred label follows the same
rule the projection enforces: BUY or STRONG_BUY, TACTICAL_SUPPORTIVE, the ranking
leader, and (from methodology 1.3.0) a leader that clears the liquidity floor.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / "config" / "presentation"
RANKING_PATH = PRESENTATION / "metals_vehicle_ranking_evidence_v1.json"
COMPONENT_PATH = PRESENTATION / "metals_vehicle_ranking_component_evidence_v1.json"
AUTH_PATH = PRESENTATION / "metals_vehicle_presentation_authorization_v1.json"

PREFERRED_LABEL = "PREFERRED_IMPLEMENTATION_CANDIDATE"
ONLY_LABEL = "ONLY_REGISTERED_IMPLEMENTATION"
ACTIONABLE_RECOMMENDATIONS = {"BUY", "STRONG_BUY"}
ACTIONABLE_TACTICAL_STATE = "TACTICAL_SUPPORTIVE"
COMPONENT_FIELDS = (
    "ticker",
    "vehicle_id",
    "vehicle_type",
    "total_score",
    "exposure_fidelity_score",
    "cost_efficiency_score",
    "liquidity_implementation_friction_score",
    "risk_efficiency_score",
    "liquidity_floor_passed",
    "cost_of_ownership_pct",
    "average_dollar_volume_usd",
    "bid_ask_spread_bps",
    "expense_ratio_pct",
    "volatility",
    "downside_volatility",
    "maximum_drawdown_magnitude",
    "value_at_risk",
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _presentation_state(order: list[str], leader_row: dict | None, state: dict) -> tuple[str, str | None, str | None]:
    if len(order) == 1:
        return "ONLY_REGISTERED_IMPLEMENTATION_AUTHORIZED", None, ONLY_LABEL
    recommendation = str(state.get("recommendation", ""))
    tactical = str(state.get("tactical_state", ""))
    if recommendation not in ACTIONABLE_RECOMMENDATIONS:
        return "RANKING_INFORMATIONAL_ONLY_UPSTREAM_NOT_BUY", None, None
    if tactical != ACTIONABLE_TACTICAL_STATE:
        if "DEFENSIVE" in tactical:
            return "RANKING_INFORMATIONAL_ONLY_UPSTREAM_DEFENSIVE", None, None
        return "RANKING_INFORMATIONAL_ONLY_UPSTREAM_NOT_SUPPORTIVE", None, None
    if leader_row is not None and leader_row.get("liquidity_floor_passed") is False:
        return "RANKING_INFORMATIONAL_ONLY_LEADER_BELOW_LIQUIDITY_FLOOR", None, None
    return "PREFERRED_IMPLEMENTATION_AUTHORIZED", order[0], PREFERRED_LABEL


def build(
    rehearsal: dict,
    commodity_state: dict,
    templates: tuple[dict, dict, dict],
    source: dict,
) -> tuple[dict, dict, dict]:
    if rehearsal.get("status") != "METALS_FOUR_FACTOR_RANKING_V1_REHEARSAL_PASS":
        raise ValueError("ranking rehearsal did not pass")
    ranking_template, component_template, auth_template = templates
    ranking = copy.deepcopy(ranking_template)
    component = copy.deepcopy(component_template)
    auth = copy.deepcopy(auth_template)

    ranking_groups: list[dict] = []
    component_groups: list[dict] = []
    commodities: list[dict] = []
    vehicle_count = 0
    for group in sorted(rehearsal["groups"], key=lambda item: item["commodity_id"]):
        commodity_id = group["commodity_id"]
        rows = list(group["vehicles"])
        order = [row["ticker"] for row in rows]
        vehicle_count += len(order)
        single = len(order) == 1
        leader = None if single else order[0]
        components = [{key: row[key] for key in COMPONENT_FIELDS if key in row} for row in rows]
        if single:
            ranking_groups.append(
                {"commodity_id": commodity_id, "state": ONLY_LABEL, "certified_order": order, "certified_leader": None}
            )
            component_groups.append(
                {"commodity_id": commodity_id, "state": ONLY_LABEL, "certified_order": order,
                 "certified_leader": None, "vehicles": components}
            )
        else:
            ranking_groups.append(
                {"commodity_id": commodity_id, "certified_order": order, "certified_leader": leader,
                 "scores": {row["ticker"]: row["total_score"] for row in rows}}
            )
            component_groups.append(
                {"commodity_id": commodity_id, "certified_order": order, "certified_leader": leader,
                 "vehicles": components}
            )
        state = commodity_state.get(commodity_id)
        if state is None:
            raise ValueError(f"no current recommendation/tactical state for {commodity_id}")
        presentation_state, preferred, label = _presentation_state(order, None if single else rows[0], state)
        commodities.append(
            {
                "commodity_id": commodity_id,
                "recommendation": state.get("recommendation"),
                "tactical_state": state.get("tactical_state"),
                "adjusted_expected_return_12m": state.get("adjusted_expected_return_12m"),
                "certified_vehicle_order": order,
                "presentation_state": presentation_state,
                "authorized_preferred_vehicle": preferred,
                "authorized_label": label,
            }
        )

    binding = {
        "ranking_methodology_version": rehearsal["methodology_version"],
        "source_run_id": source["run_id"],
        "source_head_sha": source["head_sha"],
        "source_artifact_id": source.get("artifact_id"),
        "source_artifact_name": source["artifact_name"],
        "source_artifact_digest": source["artifact_digest"],
        "source_production_run_id": source.get("production_run_id"),
        "source_production_artifact_id": source.get("production_artifact_id"),
        "source_production_artifact_digest": source.get("production_artifact_digest"),
        "risk_output_sha256": source.get("risk_output_sha256"),
    }
    for key, value in binding.items():
        if key in ranking:
            ranking[key] = value
        if key in component:
            component[key] = value
    ranking["ranking_authority_id"] = rehearsal["authority_id"]
    component["ranking_authority_id"] = rehearsal["authority_id"]
    ranking["registered_vehicle_count"] = vehicle_count
    ranking["commodity_group_count"] = len(ranking_groups)
    ranking["weights"] = rehearsal["weights"]
    component["weights"] = rehearsal["weights"]
    ranking["groups"] = ranking_groups
    component["groups"] = component_groups
    auth["ranking_evidence_authority_id"] = ranking["authority_id"]
    auth["ranking_source_artifact_digest"] = source["artifact_digest"]
    auth["commodities"] = commodities
    return ranking, component, auth


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rehearsal", type=Path, required=True)
    parser.add_argument("--commodity-state", type=Path, required=True,
                        help="JSON {commodity_id: {recommendation, tactical_state, adjusted_expected_return_12m}}")
    parser.add_argument("--source", type=Path, required=True,
                        help="JSON with run_id, head_sha, artifact_name, optional artifact_id and production fields")
    parser.add_argument("--output-root", type=Path, default=PRESENTATION)
    args = parser.parse_args(argv)

    source = _read(args.source)
    source.setdefault("artifact_digest", file_digest(args.rehearsal))
    outputs = build(
        _read(args.rehearsal),
        _read(args.commodity_state),
        (_read(RANKING_PATH), _read(COMPONENT_PATH), _read(AUTH_PATH)),
        source,
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    for name, document in zip((RANKING_PATH.name, COMPONENT_PATH.name, AUTH_PATH.name), outputs):
        _write(args.output_root / name, document)
    ranking, _, auth = outputs
    print(f"METALS VEHICLE RANKING EVIDENCE: methodology {ranking['ranking_methodology_version']}, "
          f"{ranking['registered_vehicle_count']} vehicles, {ranking['commodity_group_count']} groups")
    for item in auth["commodities"]:
        print(f"  {item['commodity_id']}: {item['certified_vehicle_order']} -> {item['presentation_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
