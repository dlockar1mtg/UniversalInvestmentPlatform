import csv
import io
import json

from foundation.intelligence.ranking.competition import CompetitionPolicy
from foundation.intelligence.ranking.orchestrator import PortfolioRankingItem, run_portfolio_ranking
from foundation.intelligence.ranking.serialization import (
    AUDIT_COLUMNS,
    RANKING_COLUMNS,
    ranking_audit_csv,
    ranking_audit_rows,
    ranking_batch_json,
    ranking_dashboard_csv,
    ranking_dashboard_rows,
)


def result():
    items = [
        PortfolioRankingItem("BTC", 90, "P1", {"confidence": 85, "liquidity": 95}),
        PortfolioRankingItem("GLD", 80, "P2", {"confidence": 80}, penalties={"capacity": 2}),
    ]
    return run_portfolio_ranking("batch-1", items, CompetitionPolicy(max_selected=1))


def test_json_is_valid_complete_and_deterministic():
    batch = result()
    first = ranking_batch_json(batch)
    second = ranking_batch_json(batch)
    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == "5.2.9"
    assert payload["batch_fingerprint"] == batch.batch_fingerprint
    assert len(payload["ranking"]) == 2
    assert len(payload["audit_records"]) == 12


def test_dashboard_rows_preserve_rank_and_disposition():
    rows = ranking_dashboard_rows(result())
    assert [row["opportunity_id"] for row in rows] == ["BTC", "GLD"]
    assert [row["rank"] for row in rows] == [1, 2]
    assert rows[0]["disposition"] == "SELECTED"
    assert rows[1]["disposition"] == "DEFERRED"
    assert rows[0]["priority_tier"] == "P1"


def test_dashboard_csv_has_fixed_columns_and_round_trips():
    text = ranking_dashboard_csv(result())
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert tuple(parsed[0]) == RANKING_COLUMNS
    assert len(parsed) == 2
    assert text.endswith("\n")


def test_audit_rows_and_csv_follow_artifact_sequence():
    batch = result()
    rows = ranking_audit_rows(batch)
    assert [row["sequence"] for row in rows] == list(range(1, 13))
    assert json.loads(rows[0]["evidence_json"])["status"] == "COMPARABLE"
    parsed = list(csv.DictReader(io.StringIO(ranking_audit_csv(batch))))
    assert tuple(parsed[0]) == AUDIT_COLUMNS
    assert len(parsed) == 12


def test_machine_outputs_do_not_emit_python_enum_or_decimal_representations():
    batch = result()
    combined = ranking_batch_json(batch) + ranking_dashboard_csv(batch) + ranking_audit_csv(batch)
    assert "Decimal(" not in combined
    assert "CompetitionDisposition." not in combined


def test_competing_winner_field_is_blank_in_csv_when_absent():
    parsed = list(csv.DictReader(io.StringIO(ranking_dashboard_csv(result()))))
    assert parsed[0]["competed_with"] == ""
