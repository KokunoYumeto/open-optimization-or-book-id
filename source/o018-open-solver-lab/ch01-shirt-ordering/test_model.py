"""Uji regresi untuk laboratorium kaus.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from model import build_model, load_data, solve_model


HERE = Path(__file__).resolve().parent


class ShirtOrderingLabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.expected = json.loads(
            (HERE / "expected-results.json").read_text(encoding="utf-8")
        )
        cls.tolerance = float(cls.expected["tolerance"])

    def assert_mapping_close(
        self, actual: dict[str, float], expected: dict[str, float]
    ) -> None:
        self.assertEqual(set(actual), set(expected))
        for key in sorted(expected):
            self.assertAlmostEqual(
                actual[key], expected[key], delta=self.tolerance, msg=key
            )

    def test_model_topology_is_three_balances(self) -> None:
        model = build_model(self.data)
        self.assertEqual(len(model.P), 3)
        self.assertEqual(len(model.balance), 3)
        self.assertEqual(len(model.order), 3)
        self.assertEqual(len(model.inventory), 3)

    def test_lp_optimum(self) -> None:
        actual = solve_model(self.data, integer=False)
        expected = self.expected["modes"]["lp"]
        self.assertAlmostEqual(
            actual["objective"], expected["objective"], delta=self.tolerance
        )
        self.assert_mapping_close(actual["orders"], expected["orders"])
        self.assert_mapping_close(actual["inventory"], expected["inventory"])

    def test_integer_optimum_matches_lp(self) -> None:
        actual = solve_model(self.data, integer=True)
        expected = self.expected["modes"]["integer"]
        self.assertAlmostEqual(
            actual["objective"], expected["objective"], delta=self.tolerance
        )
        self.assert_mapping_close(actual["orders"], expected["orders"])
        self.assert_mapping_close(actual["inventory"], expected["inventory"])


if __name__ == "__main__":
    unittest.main()

