from __future__ import annotations
import unittest
from pathlib import Path

from exchange.metals.adapter.contracts import load_contract


class ContractLoaderTests(unittest.TestCase):
    def test_missing_contract_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_contract(Path("not_here.csv"))


if __name__ == "__main__": unittest.main()
