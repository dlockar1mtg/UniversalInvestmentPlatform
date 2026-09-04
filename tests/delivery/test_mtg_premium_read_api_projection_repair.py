from __future__ import annotations

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
                ("active-premium",)
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


def premium_payload() -> dict:
    return {
        "mtg_asset_id": (
            "SECRET_LAIR_V1_1|SL-EXAMPLE"
        ),
        "secret_lair_id": "SL-EXAMPLE",
        "product_name": "Example Secret Lair",

        "current_tcg_market_price_usd": "100.00",

        "certified_1y_point_forecast_usd": "125.00",
        "certified_1y_point_return": "0.25",

        "y1_q10_break_even_entry_price_usd": "82.50",
        "current_price_margin_to_q10_break_even": "-17.50",
        "current_price_vs_q10_break_even_state": "ABOVE_Q10_BREAK_EVEN",

        "y1_probability_of_loss": "0.20",
        "y1_probability_of_positive_return": "0.80",
        "y1_downside_tail_mean_total_return": "-0.25",
        "y1_upside_tail_mean_total_return": "0.55",

        "y1_q10_terminal_value_usd": "85.00",
        "y1_q50_terminal_value_usd": "125.00",
        "y1_q90_terminal_value_usd": "170.00",

        "y3_median_total_return_scenario": "0.60",
        "y3_probability_of_loss_scenario": "0.15",
        "y3_q10_terminal_value_scenario_usd": "90.00",
        "y3_q50_terminal_value_scenario_usd": "160.00",
        "y3_q90_terminal_value_scenario_usd": "240.00",

        "y5_median_total_return_scenario": "1.10",
        "y5_probability_of_loss_scenario": "0.10",
        "y5_q10_terminal_value_scenario_usd": "100.00",
        "y5_q50_terminal_value_scenario_usd": "210.00",
        "y5_q90_terminal_value_scenario_usd": "350.00",

        "own_history_evidence_class": "FULL",
        "history_span_days": "900",
        "historical_observation_count": "120",

        "exact_structural_comparable_support": "TRUE",
        "exact_structural_comparable_product_count": "4",
        "global_comparable_product_count": "25",
        "exact_structural_comparable_event_count": "10",
        "global_comparable_event_count": "100",

        "source_authority_path": (
            "docs/phase_8/secret_lair/"
            "secret_lair_v1_purchase_analysis.csv"
        ),
        "source_authority_sha256": (
            "eb5efced959116eb7b174d4aff27c06d"
            "321e774eda39b3f8572d958499441cdb"
        ),
    }


def full_secret_lair_rows(
    *,
    include_premium: bool = True,
):
    rows = [
        (
            "asset",
            "asset",
            {
                "asset_name": "Example Secret Lair",
                "mtg_lane": "SECRET_LAIR_V1_1",
            },
        ),
        (
            "native_authority",
            "native_authority",
            {
                "native_rank": 5,
                "native_rank_type": "COMPETITION_RANK",
                "native_purchase_status": (
                    "WAIT_FOR_Q10_ENTRY"
                ),
                "purchase_semantic": (
                    "MODEL_QUALIFIED_ENTRY_CANDIDATE"
                ),
                "execution_ready_purchase_certified": False,
                "automatic_purchase_execution": False,
            },
        ),
        (
            "forecast",
            "forecast:1y",
            {
                "horizon_years": 1,
            },
        ),
        (
            "risk_metric",
            "risk:1y",
            {
                "probability_of_loss": 0.2,
            },
        ),
        (
            "recommendation",
            "recommendation",
            {},
        ),
    ]

    if include_premium:
        rows.append(
            (
                "mtg_premium_research",
                (
                    "SECRET_LAIR_V1_1|"
                    "SL-EXAMPLE"
                ),
                premium_payload(),
            )
        )

    return rows


def test_full_secret_lair_projects_exact_lossless_premium_payload():
    repo = repository({
        (
            "mtg",
            "SECRET_LAIR_V1_1|SL-EXAMPLE",
        ): full_secret_lair_rows()
    })

    result = repo.mtg_premium_research(
        "SECRET_LAIR_V1_1|SL-EXAMPLE"
    )

    assert result is not None

    assert (
        result["premium_research"]
        == premium_payload()
    )

    assert (
        result["authority_availability"]
        ["premium_research_record_count"]
        == 1
    )


def test_premium_projection_preserves_q10_and_one_year_fields():
    repo = repository({
        ("mtg", "premium-1"): (
            full_secret_lair_rows()
        )
    })

    result = repo.mtg_premium_research(
        "premium-1"
    )

    assert result is not None

    premium = result[
        "premium_research"
    ]

    assert premium is not None

    assert (
        premium[
            "y1_q10_break_even_entry_price_usd"
        ]
        == "82.50"
    )

    assert (
        premium[
            "certified_1y_point_forecast_usd"
        ]
        == "125.00"
    )

    assert (
        premium[
            "certified_1y_point_return"
        ]
        == "0.25"
    )


def test_premium_projection_preserves_3y_5y_scenario_names():
    repo = repository({
        ("mtg", "premium-scenarios"): (
            full_secret_lair_rows()
        )
    })

    result = repo.mtg_premium_research(
        "premium-scenarios"
    )

    assert result is not None

    premium = result[
        "premium_research"
    ]

    assert premium is not None

    assert (
        premium[
            "y3_median_total_return_scenario"
        ]
        == "0.60"
    )

    assert (
        premium[
            "y5_median_total_return_scenario"
        ]
        == "1.10"
    )

    assert (
        "y3_median_total_return"
        not in premium
    )

    assert (
        "y5_median_total_return"
        not in premium
    )


def test_premium_projection_preserves_source_lineage():
    repo = repository({
        ("mtg", "premium-lineage"): (
            full_secret_lair_rows()
        )
    })

    result = repo.mtg_premium_research(
        "premium-lineage"
    )

    assert result is not None

    premium = result[
        "premium_research"
    ]

    assert premium is not None

    assert (
        premium["source_authority_path"]
        == (
            "docs/phase_8/secret_lair/"
            "secret_lair_v1_purchase_analysis.csv"
        )
    )

    assert (
        premium["source_authority_sha256"]
        == (
            "eb5efced959116eb7b174d4aff27c06d"
            "321e774eda39b3f8572d958499441cdb"
        )
    )


def test_missing_premium_authority_remains_missing():
    repo = repository({
        ("mtg", "no-premium"): (
            full_secret_lair_rows(
                include_premium=False
            )
        )
    })

    result = repo.mtg_premium_research(
        "no-premium"
    )

    assert result is not None

    assert (
        result["premium_research"]
        is None
    )

    assert (
        result["authority_availability"]
        ["premium_research_record_count"]
        == 0
    )


def test_duplicate_premium_authority_fails_closed():
    premium = premium_payload()

    rows = full_secret_lair_rows()

    rows.append(
        (
            "mtg_premium_research",
            "duplicate",
            dict(premium),
        )
    )

    repo = repository({
        ("mtg", "duplicate-premium"): rows
    })

    try:
        repo.mtg_premium_research(
            "duplicate-premium"
        )
    except ValueError as exc:
        assert (
            "duplicate"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "Duplicate premium authority must fail closed."
        )


def test_premium_execution_surface_fails_closed():
    premium = premium_payload()
    premium[
        "automatic_purchase_execution"
    ] = False

    rows = full_secret_lair_rows(
        include_premium=False
    )

    rows.append(
        (
            "mtg_premium_research",
            "premium",
            premium,
        )
    )

    repo = repository({
        ("mtg", "execution-surface"): rows
    })

    try:
        repo.mtg_premium_research(
            "execution-surface"
        )
    except ValueError as exc:
        assert (
            "execution authority surface"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "Premium execution surface must fail closed."
        )


def test_precollector_behavior_remains_blocked():
    repo = repository({
        ("mtg", "precollector"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Old Booster",
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
        ]
    })

    result = repo.mtg_premium_research(
        "precollector"
    )

    assert result is not None

    assert (
        result["presentation_state"]
        == "PRECOLLECTOR_CERTIFICATION_BRIDGE_REQUIRED"
    )

    assert result["research_state"] == "BLOCKED"

    assert (
        result["premium_research"]
        is None
    )


def test_collector_identity_bridge_behavior_remains_unchanged():
    repo = repository({
        ("mtg", "collector"): [
            (
                "asset",
                "asset",
                {
                    "asset_name": "Collector Box",
                    "mtg_lane": "COLLECTOR_V1",
                },
            ),
            (
                "native_authority",
                "native_authority",
                {
                    "native_rank": None,
                    "native_purchase_status": (
                        "PURCHASE_CANDIDATE"
                    ),
                    "automatic_purchase_execution": False,
                },
            ),
        ]
    })

    result = repo.mtg_premium_research(
        "collector"
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
        result["premium_research"]
        is None
    )


def test_existing_authenticated_endpoint_returns_premium_payload():
    asset_id = (
        "SECRET_LAIR_V1_1|SL-EXAMPLE"
    )

    rows = {
        (
            "mtg",
            asset_id,
        ): full_secret_lair_rows()
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

    response = client.get(
        (
            "/v1/presentation/"
            "mtg-research/"
            + asset_id
        ),
        headers={
            "x-api-key": "secret-key"
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["premium_research"]
        == premium_payload()
    )

    assert (
        body["authority_availability"]
        ["premium_research_record_count"]
        == 1
    )


def test_premium_projection_does_not_create_rank_or_execution():
    repo = repository({
        ("mtg", "premium-governance"): (
            full_secret_lair_rows()
        )
    })

    result = repo.mtg_premium_research(
        "premium-governance"
    )

    assert result is not None

    semantics = result[
        "presentation_semantics"
    ]

    assert (
        semantics[
            "cross_domain_rank_created"
        ]
        is False
    )

    assert (
        semantics[
            "universal_mtg_rank_created"
        ]
        is False
    )

    assert (
        semantics[
            "automatic_purchase_execution_authorized"
        ]
        is False
    )
