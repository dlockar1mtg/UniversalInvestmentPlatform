from pathlib import Path

from foundation.portfolio_engine.allocation import load_allocation_targets


ROOT = Path(__file__).resolve().parents[2]


def test_default_targets_load_and_total_one() -> None:
    targets = load_allocation_targets(
        ROOT / "config/portfolios/allocation_targets.yaml"
    )
    assert len(targets) == 5
    assert sum(target.target_weight for target in targets) == 1
