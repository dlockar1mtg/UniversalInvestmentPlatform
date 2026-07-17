from pathlib import Path

from foundation.portfolio_engine.rebalancing import load_rebalance_policy


ROOT = Path(__file__).resolve().parents[2]


def test_default_policy_is_contribution_only() -> None:
    policy = load_rebalance_policy(
        ROOT / "config/portfolios/rebalance_policy.yaml"
    )
    assert policy.method == "contribution_only"
    assert not policy.permit_sales
