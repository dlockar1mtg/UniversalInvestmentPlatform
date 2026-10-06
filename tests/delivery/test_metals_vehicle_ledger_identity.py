"""Metals ETFs (governed vehicles) can be recorded in the transaction ledger."""
from __future__ import annotations

from foundation.presentation.asset_catalog import GovernedAssetCatalogRepository


class _Cursor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, *args, **kwargs):
        return None

    def fetchall(self):
        return []

    def fetchone(self):
        return None


class _Connection:
    def cursor(self):
        return _Cursor()

    def close(self):
        return None


def _repository():
    return GovernedAssetCatalogRepository(lambda: _Connection())


def test_enabled_metals_vehicles_are_valid_identities():
    repository = _repository()
    for ticker in ("GLD", "IAU", "SGOL", "SLV", "SIVR", "BIL"):
        assert repository.asset_exists("metals", f"metals:vehicle:{ticker}")
    assert not repository.asset_exists("metals", "metals:vehicle:NOT-A-FUND")
    assert not repository.asset_exists("crypto", "metals:vehicle:GLD")


def test_metals_search_lists_vehicles_for_the_picker():
    items = _repository().search_assets(domain_id="metals", query="sivr")
    assert [item["asset_id"] for item in items] == ["metals:vehicle:SIVR"]
    assert items[0]["asset_symbol"] == "SIVR"
    assert _repository().search_assets(domain_id="crypto", query="sivr") == ()
