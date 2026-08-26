from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundation.presentation.read_api import (
    PresentationReadRepository,
    install_presentation_read_routes,
)


class FakeCursor:
    def __init__(self, rows_by_query):
        self.rows_by_query = rows_by_query
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        normalized = " ".join(
            str(query).split()
        )

        if (
            "SELECT publication_id FROM "
            "presentation_active_publication"
            in normalized
        ):
            self.rows = [
                ("pub-1",)
            ]
            return

        if (
            "SELECT record_type, record_key, "
            "payload_json"
            in normalized
            and "presentation_records"
            in normalized
        ):
            key = (
                str(params[1]),
                str(params[2]),
            )

            self.rows = list(
                self.rows_by_query.get(
                    key,
                    [],
                )
            )
            return

        raise AssertionError(
            f"Unexpected query: {normalized}"
        )

    def fetchone(self):
        if not self.rows:
            return None
        return self.rows[0]

    def fetchall(self):
        return list(self.rows)


class FakeConnection:
    def __init__(self, rows_by_query):
        self.rows_by_query = rows_by_query

    def cursor(self):
        return FakeCursor(
            self.rows_by_query
        )

    def close(self):
        return None


def repository(rows_by_query):
    return PresentationReadRepository(
        lambda: FakeConnection(
            rows_by_query
        )
    )


def test_secret_lair_full_research_projection_preserves_native_semantics():
    repo = repository({
        ("mtg", "sl-1"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Example Secret Lair",
                    "mtg_lane": "SECRET_LAIR_V1_1",
                },
            ),
            (
                "forecast",
                "forecast:1y",
                {
                    "horizon_years": 1,
                    "output_class": "DIRECT_1Y_FORECAST_DISTRIBUTION",
                    "q10_terminal_value_usd": 80.0,
                    "q50_terminal_value_usd": 120.0,
                    "q90_terminal_value_usd": 180.0,
                },
            ),
            (
                "risk_metric",
                "risk:1y",
                {
                    "probability_of_loss": 0.2,
                    "probability_of_positive_return": 0.8,
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_rank": 4,
                    "native_rank_type": "COMPETITION_RANK",
                    "native_purchase_status": "BUY_CANDIDATE_NOW",
                    "purchase_semantic": "MODEL_QUALIFIED_ENTRY_CANDIDATE",
                    "evidence_state": "CERTIFIED",
                    "actionability_state": "ACTIONABLE",
                    "manual_execution_price_check_required": True,
                    "execution_ready_purchase_certified": False,
                    "automatic_purchase_execution": False,
                },
            ),
            (
                "recommendation",
                "recommendation",
                {
                    "evidence_state": "CERTIFIED",
                    "actionability_state": "ACTIONABLE",
                },
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "sl-1"
    )

    assert result is not None
    assert (
        result["presentation_state"]
        == "SECRET_LAIR_PREMIUM_RESEARCH"
    )
    assert result["research_state"] == "FULL"

    assert (
        result["native_authority"]
        ["native_rank"]
        == 4
    )

    assert (
        result["native_authority"]
        ["native_purchase_status"]
        == "BUY_CANDIDATE_NOW"
    )

    semantics = result[
        "presentation_semantics"
    ]

    assert (
        semantics["cross_domain_rank_created"]
        is False
    )
    assert (
        semantics["universal_mtg_rank_created"]
        is False
    )
    assert (
        semantics["automatic_purchase_execution_authorized"]
        is False
    )


def test_secret_lair_partial_research_does_not_synthesize_rank():
    repo = repository({
        ("mtg", "sl-gap"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Evidence Gap",
                    "mtg_lane": "SECRET_LAIR_V1_1",
                },
            ),
            (
                "forecast",
                "forecast",
                {
                    "three_year_output_class": (
                        "SCENARIO_DISTRIBUTION_NOT_DIRECTLY_VALIDATED"
                    )
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_rank": None,
                    "native_purchase_status": None,
                    "automatic_purchase_execution": False,
                },
            ),
            (
                "recommendation",
                "recommendation",
                {},
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "sl-gap"
    )

    assert result is not None
    assert result["research_state"] == "PARTIAL"

    assert (
        result["authority_availability"]
        ["native_rank_state"]
        == "MISSING"
    )

    assert (
        result["authority_availability"]
        ["native_purchase_state"]
        == "MISSING"
    )

    assert (
        result["native_authority"]
        ["native_rank"]
        is None
    )


def test_precollector_is_fail_closed_for_premium_promotion():
    repo = repository({
        ("mtg", "pre-1"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Old Booster Box",
                    "mtg_lane": "PRE_COLLECTOR",
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_purchase_status": "WATCH",
                    "automatic_purchase_execution": False,
                },
            ),
            (
                "recommendation",
                "recommendation",
                {},
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "pre-1"
    )

    assert result is not None

    assert (
        result["presentation_state"]
        == "PRECOLLECTOR_CERTIFICATION_BRIDGE_REQUIRED"
    )

    assert result["research_state"] == "BLOCKED"

    assert "blocked_reason" in result


def test_collector_core_exposes_native_core_but_not_rank_bridge():
    repo = repository({
        ("mtg", "collector-1"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Collector Box",
                    "mtg_lane": "COLLECTOR_V1",
                },
            ),
            (
                "forecast",
                "forecast:365",
                {
                    "horizon_days": 365,
                    "median_price": 150.0,
                    "probability_of_loss": 0.15,
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_purchase_status": "PURCHASE_CANDIDATE",
                    "purchase_semantic": "NATIVE_COLLECTOR_PURCHASE",
                    "native_rank": None,
                    "automatic_purchase_execution": False,
                },
            ),
            (
                "recommendation",
                "recommendation",
                {},
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "collector-1"
    )

    assert result is not None

    assert (
        result["presentation_state"]
        == "COLLECTOR_CERTIFIED_CORE"
    )

    assert (
        result["ranking_bridge_state"]
        == "IDENTITY_BRIDGE_REQUIRED"
    )

    assert (
        result["native_authority"]
        ["native_rank"]
        is None
    )


def test_projection_rejects_automatic_purchase_execution():
    repo = repository({
        ("mtg", "bad-1"): [
            (
                "asset",
                "asset",
                {
                    "mtg_lane": "SECRET_LAIR_V1_1"
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "automatic_purchase_execution": True
                },
            ),
            (
                "recommendation",
                "recommendation",
                {},
            ),
        ]
    })

    try:
        repo.mtg_premium_research(
            "bad-1"
        )
    except ValueError as exc:
        assert (
            "automatic purchase execution"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "Expected fail-closed automatic execution rejection."
        )


def test_projection_returns_none_for_missing_asset():
    repo = repository({})

    assert (
        repo.mtg_premium_research(
            "missing"
        )
        is None
    )


def test_authenticated_mtg_research_endpoint():
    rows = {
        ("mtg", "sl-2"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Endpoint Product",
                    "mtg_lane": "SECRET_LAIR_V1_1",
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_rank": 7,
                    "native_purchase_status": "WAIT_FOR_Q10_ENTRY",
                    "automatic_purchase_execution": False,
                },
            ),
            (
                "recommendation",
                "recommendation",
                {},
            ),
        ]
    }

    app = FastAPI()

    install_presentation_read_routes(
        app,
        {
            "tester": (
                "secret-key",
                ("operator",),
            )
        },
        repository(rows),
    )

    client = TestClient(app)

    unauthenticated = client.get(
        "/v1/presentation/mtg-research/sl-2"
    )

    assert unauthenticated.status_code == 401

    authenticated = client.get(
        "/v1/presentation/mtg-research/sl-2",
        headers={
            "x-api-key": "secret-key"
        },
    )

    assert authenticated.status_code == 200

    body = authenticated.json()

    assert body["domain_id"] == "mtg"
    assert body["asset_id"] == "sl-2"
    assert (
        body["presentation_state"]
        == "SECRET_LAIR_PREMIUM_RESEARCH"
    )


def test_mtg_research_endpoint_returns_404_for_missing_asset():
    app = FastAPI()

    install_presentation_read_routes(
        app,
        {
            "tester": (
                "secret-key",
                ("operator",),
            )
        },
        repository({}),
    )

    client = TestClient(app)

    response = client.get(
        "/v1/presentation/mtg-research/missing",
        headers={
            "x-api-key": "secret-key"
        },
    )

    assert response.status_code == 404


def test_mtg_projection_uses_explicit_native_authority_record():
    repo = repository({
        ("mtg", "collector-example"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Example Collector",
                    "mtg_lane": "COLLECTOR_V1",
                    "current_price_usd": 100.0,
                },
            ),
            (
                "recommendation",
                "recommendation",
                {
                    "evidence_state": "RANKING_ELIGIBLE_WITH_LIMITATIONS",
                    "actionability_state": "STRONG_PURCHASE_CANDIDATE",
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_purchase_status": "STRONG_PURCHASE_CANDIDATE",
                    "native_rank": 3,
                    "native_rank_type": "COLLECTOR_FINAL_GOVERNED_RANK",
                    "purchase_semantic": "NATIVE_COLLECTOR_PURCHASE_STATUS",
                    "manual_execution_price_check_required": True,
                    "execution_ready_purchase_certified": False,
                    "automatic_purchase_execution": False,
                    "evidence_state": "RANKING_ELIGIBLE_WITH_LIMITATIONS",
                    "actionability_state": "STRONG_PURCHASE_CANDIDATE",
                },
            ),
            (
                "forecast",
                "forecast",
                {
                    "forecast_horizon_months": 12,
                    "forecast_1y_price_usd": 150.0,
                    "forecast_1y_return": 0.5,
                    "point_forecast": 150.0,
                    "expected_return": 0.5,
                },
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "collector-example"
    )

    assert result is not None

    authority = result["native_authority"]

    assert authority["native_rank"] == 3
    assert (
        authority["native_purchase_status"]
        == "STRONG_PURCHASE_CANDIDATE"
    )

    availability = result["authority_availability"]

    assert (
        availability["native_authority_record_count"]
        == 1
    )
    assert (
        availability["recommendation_record_count"]
        == 1
    )
    assert availability["forecast_record_count"] == 1

    assert len(result["native_authorities"]) == 1
    assert len(result["recommendations"]) == 1
    assert len(result["forecasts"]) == 1


def test_recommendation_payload_cannot_impersonate_native_authority():
    repo = repository({
        ("mtg", "collector-no-native-authority"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Example Collector",
                    "mtg_lane": "COLLECTOR_V1",
                },
            ),
            (
                "recommendation",
                "recommendation",
                {
                    "native_purchase_status": "SHOULD_NOT_BE_USED",
                    "native_rank": 999,
                },
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "collector-no-native-authority"
    )

    assert result is not None

    authority = result["native_authority"]

    assert authority["native_rank"] is None
    assert authority["native_purchase_status"] is None

    availability = result["authority_availability"]

    assert (
        availability["native_authority_record_count"]
        == 0
    )
    assert (
        availability["native_rank_state"]
        == "MISSING"
    )
    assert (
        availability["native_purchase_state"]
        == "MISSING"
    )


def test_string_false_execution_values_are_fail_safe():
    repo = repository({
        ("mtg", "bool-false"): [
            (
                "asset",
                "asset",
                {
                    "mtg_lane": "SECRET_LAIR_V1_1",
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_rank": 1,
                    "native_purchase_status": "BUY_CANDIDATE_NOW",
                    "execution_ready_purchase_certified": "NO",
                    "automatic_purchase_execution": "false",
                },
            ),
            (
                "recommendation",
                "recommendation",
                {},
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "bool-false"
    )

    assert result is not None

    authority = result["native_authority"]

    assert (
        authority["execution_ready_purchase_certified"]
        is False
    )
    assert (
        authority["automatic_purchase_execution"]
        is False
    )


def test_string_true_automatic_execution_is_rejected():
    for raw_value in (
        "YES",
        "true",
        "1",
    ):
        repo = repository({
            ("mtg", f"bool-true-{raw_value}"): [
                (
                    "asset",
                    "asset",
                    {
                        "mtg_lane": "SECRET_LAIR_V1_1",
                    },
                ),
                (
                    "native_authority",
                    "native_authority",
                    {
                        "automatic_purchase_execution": raw_value,
                    },
                ),
                (
                    "recommendation",
                    "recommendation",
                    {},
                ),
            ]
        })

        try:
            repo.mtg_premium_research(
                f"bool-true-{raw_value}"
            )
        except ValueError as exc:
            assert (
                "automatic purchase execution"
                in str(exc).lower()
            )
        else:
            raise AssertionError(
                "Expected automatic execution rejection "
                f"for value {raw_value!r}."
            )


def test_unknown_boolean_authority_value_fails_closed():
    repo = repository({
        ("mtg", "bool-unknown"): [
            (
                "asset",
                "asset",
                {
                    "mtg_lane": "COLLECTOR_V1",
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "execution_ready_purchase_certified": "MAYBE",
                    "automatic_purchase_execution": False,
                },
            ),
            (
                "recommendation",
                "recommendation",
                {},
            ),
        ]
    })

    try:
        repo.mtg_premium_research(
            "bool-unknown"
        )
    except ValueError as exc:
        message = str(exc).lower()

        assert (
            "unsupported mtg boolean authority value"
            in message
        )
        assert (
            "execution_ready_purchase_certified"
            in message
        )
    else:
        raise AssertionError(
            "Expected unsupported boolean authority "
            "value to fail closed."
        )

