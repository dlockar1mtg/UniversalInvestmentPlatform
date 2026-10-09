"""Shared test settings."""
import pytest


@pytest.fixture(autouse=True)
def _synthetic_mtg_decisions_never_age(monkeypatch, request):
    """Synthetic MTG decision files carry fixed dates; only tests about staleness use the real age limit."""
    if "stale" not in request.node.name:
        monkeypatch.setenv("UIP_MTG_DECISIONS_MAX_AGE_DAYS", "100000")
