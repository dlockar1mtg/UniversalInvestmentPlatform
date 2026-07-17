from decimal import Decimal

import pytest

from foundation.intelligence.scoring.score_band import (
    DEFAULT_SCORE_BANDS,
    ScoreBand,
    classify_score,
    validate_score_bands,
)


def test_default_score_bands_cover_full_range() -> None:
    validated = validate_score_bands(DEFAULT_SCORE_BANDS)
    assert validated[0].minimum_score == Decimal("0")
    assert validated[-1].maximum_score == Decimal("100")


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        ("0", "critical"),
        ("19.999", "critical"),
        ("20", "very_weak"),
        ("50", "neutral"),
        ("79.999", "strong"),
        ("90", "exceptional"),
        ("100", "exceptional"),
    ],
)
def test_classify_score(score: str, expected: str) -> None:
    assert classify_score(Decimal(score)).name == expected


def test_score_band_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        ScoreBand("bad", "Bad", Decimal("50"), Decimal("50"), "Invalid")


def test_classify_score_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        classify_score(Decimal("100.01"))
