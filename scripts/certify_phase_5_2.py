"""Run the reference cross-asset Phase 5.2 certification scenario."""

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from foundation.intelligence.ranking.certification import certify_phase_5_2
from foundation.intelligence.ranking.competition import CompetitionPolicy
from foundation.intelligence.ranking.orchestrator import PortfolioRankingItem


items = [
    PortfolioRankingItem("BTC", 92, "P1", {"confidence": 85}, group_key="crypto"),
    PortfolioRankingItem("VOO", 88, "P1", {"confidence": 90}, group_key="etf"),
    PortfolioRankingItem("GLD", 81, "P2", {"confidence": 80}, group_key="metals"),
    PortfolioRankingItem("MTG-BOX", 74, "P3", {"confidence": 70}, group_key="mtg"),
]
report = certify_phase_5_2(
    items,
    CompetitionPolicy(max_selected=3, max_selected_per_group=1),
)
print(report.to_json())
raise SystemExit(0 if report.passed else 1)
