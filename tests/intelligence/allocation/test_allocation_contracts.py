from datetime import datetime, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.allocation import (
    AllocationBounds,
    AllocationLine,
    AllocationReasonCode,
    AllocationRequest,
    AllocationStatus,
    CapitalAllocationResult,
    CapitalPool,
    CapitalPoolType,
)


def test_capital_pool_calculates_deployable_capital():
    pool = CapitalPool("monthly", CapitalPoolType.RECURRING, 3000, 500)
    assert pool.gross_capital == Decimal("3000")
    assert pool.deployable_capital == Decimal("2500")


def test_allocation_bounds_enforce_ordering():
    assert AllocationBounds(100, 250, 500).target_amount == Decimal("250")
    with pytest.raises(ValueError):
        AllocationBounds(300, 200, 500)


def test_request_preserves_ranking_handoff():
    request = AllocationRequest(
        "req-1", "BTC", "rank-1", 92.5, "P1", AllocationBounds(50, 300, 500), "crypto", "crypto"
    )
    assert request.priority_score == Decimal("92.5")
    with pytest.raises(ValueError):
        AllocationRequest("req-2", "BTC", "rank-1", 101, "P1", AllocationBounds(1, 2, 3), "crypto", "crypto")


def test_allocation_line_calculates_unmet_amount():
    line = AllocationLine(
        "req-1", "BTC", 300, 200, AllocationStatus.PARTIALLY_ALLOCATED,
        (AllocationReasonCode.PARTIAL_CAPITAL_LIMIT,),
    )
    assert line.unmet_amount == Decimal("100")


def test_result_enforces_capital_conservation_and_line_total():
    line = AllocationLine(
        "req-1", "BTC", 700, 700, AllocationStatus.ALLOCATED,
        (AllocationReasonCode.TARGET_FUNDED,),
    )
    result = CapitalAllocationResult(
        "allocation-1", "rank-1", "monthly", 1000, 200, 700, 100, (line,),
        datetime.now(timezone.utc),
    )
    assert result.allocated_capital == Decimal("700")
    with pytest.raises(ValueError):
        CapitalAllocationResult("bad", "rank-1", "monthly", 1000, 200, 700, 200, (line,))


def test_pool_rejects_reserve_above_gross_capital():
    with pytest.raises(ValueError):
        CapitalPool("monthly", CapitalPoolType.RECURRING, 100, 101)
