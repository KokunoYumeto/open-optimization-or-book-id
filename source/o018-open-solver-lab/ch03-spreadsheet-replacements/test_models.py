"""Regresi numerik dan kontrak sumber untuk pendamping terbuka Bab 3.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import ast
import json
import sys
import unittest
from numbers import Real
from pathlib import Path

from pyomo.environ import Constraint, Var

from model import (
    TOLERANCE,
    build_exercise_3_1,
    build_exercise_3_2,
    build_exercise_3_3,
    build_exercise_3_4,
    build_exercise_3_5,
    build_exercise_3_6,
    build_exercise_3_7,
    build_exercise_3_9,
    load_data,
    solve_all,
)
from run_lab import serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]


class Chapter3OpenLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.expected = json.loads(
            (HERE / "expected-results.json").read_text(encoding="utf-8")
        )
        cls.results = solve_all(cls.data)

    def assert_contract(self, expected, actual, path: str = "root") -> None:
        if isinstance(expected, bool):
            self.assertIs(actual, expected, path)
        elif isinstance(expected, Real):
            self.assertIsInstance(actual, Real, path)
            self.assertAlmostEqual(
                float(actual),
                float(expected),
                delta=float(self.expected["numerical_tolerance"]),
                msg=path,
            )
        elif isinstance(expected, dict):
            self.assertIsInstance(actual, dict, path)
            for key, value in expected.items():
                self.assertIn(key, actual, f"{path}.{key}")
                self.assert_contract(value, actual[key], f"{path}.{key}")
        elif isinstance(expected, list):
            self.assertIsInstance(actual, list, path)
            self.assertEqual(len(expected), len(actual), path)
            for index, value in enumerate(expected):
                self.assert_contract(value, actual[index], f"{path}[{index}]")
        else:
            self.assertEqual(actual, expected, path)

    def test_01_provenance_hashes_match_frozen_sources(self) -> None:
        for source in self.data["provenance"].values():
            if not isinstance(source, dict):
                continue
            path = LANE_ROOT / source["path"]
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])

    def test_02_model_topology_and_domains(self) -> None:
        specs = self.data["exercises"]
        models_and_counts = (
            (build_exercise_3_1(specs["3.1"]), 4, 4),
            (build_exercise_3_2(specs["3.2"]), 20, 10),
            (build_exercise_3_3(specs["3.3"]), 5, 4),
            (build_exercise_3_4(specs["3.4"]), 2, 2),
            (build_exercise_3_5(specs["3.5"]), 6, 5),
            (build_exercise_3_6(specs["3.6"]), 3, 3),
            (build_exercise_3_7(specs["3.7"]), 9, 6),
            (build_exercise_3_9(specs["3.9"], short_selling=False), 2, 1),
            (build_exercise_3_9(specs["3.9"], short_selling=True), 2, 1),
        )
        for model, variable_count, constraint_count in models_and_counts:
            self.assertEqual(
                len(tuple(model.component_data_objects(Var, active=True))),
                variable_count,
                model.name,
            )
            self.assertEqual(
                len(tuple(model.component_data_objects(Constraint, active=True))),
                constraint_count,
                model.name,
            )
        free_model = models_and_counts[-1][0]
        self.assertIsNone(free_model.asset_a.lb)
        self.assertIsNone(free_model.asset_a.ub)

    def test_03_every_executable_case_is_optimal_and_feasible(self) -> None:
        executions: list[dict] = []

        def visit(node) -> None:
            if isinstance(node, dict):
                if "execution" in node:
                    executions.append(node["execution"])
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(self.results["exercises"])
        self.assertEqual(len(executions), 13)
        for execution in executions:
            self.assertEqual(execution["solver"], "appsi_highs")
            self.assertEqual(execution["termination_condition"], "optimal")
            self.assertIn(execution["status"], {"ok", "warning"})
            self.assertLessEqual(execution["maximum_violation"], TOLERANCE)

    def test_04_exercise_3_1_min_cost_network(self) -> None:
        self.assert_contract(
            self.expected["exercises"]["3.1"], self.results["exercises"]["3.1"]
        )

    def test_05_exercise_3_2_ten_period_production(self) -> None:
        self.assert_contract(
            self.expected["exercises"]["3.2"], self.results["exercises"]["3.2"]
        )

    def test_06_exercise_3_3_continuous_diet(self) -> None:
        expected = self.expected["exercises"]["3.3"]
        result = self.results["exercises"]["3.3"]
        self.assert_contract(
            {"active_minimums": expected["active_minimums"], "objective": expected["objective"]},
            result,
        )
        self.assertEqual(expected["exact_objective_fraction"], "2407651/760055")

    def test_07_exercise_3_4_duals_and_profit_rerun(self) -> None:
        self.assert_contract(
            self.expected["exercises"]["3.4"], self.results["exercises"]["3.4"]
        )

    def test_08_exercise_3_5_balanced_transportation(self) -> None:
        result = self.results["exercises"]["3.5"]
        self.assert_contract(self.expected["exercises"]["3.5"], result)
        self.assertNotIn("saturated_routes", result)

    def test_09_exercise_3_6_sensitivity(self) -> None:
        self.assert_contract(
            self.expected["exercises"]["3.6"], self.results["exercises"]["3.6"]
        )

    def test_10_exercise_3_7_degenerate_reporting_and_duals(self) -> None:
        result = self.results["exercises"]["3.7"]
        self.assert_contract(self.expected["exercises"]["3.7"], result)
        self.assertNotIn("route_flow", result)
        self.assertNotIn("plant_total", result)

    def test_11_exercise_3_8_method_comparison(self) -> None:
        result = self.results["exercises"]["3.8"]
        self.assertEqual(
            [item["method"] for item in result["comparison"]],
            ["Simplex LP", "GRG Nonlinear", "Evolutionary"],
        )
        self.assertIn("titik awal", result["comparison"][1]["global_guarantee"])
        self.assertIn("epsilon > 0", result["smooth_example"])
        self.assertIn("nonlinear", result["formula_case"])

    def test_12_exercise_3_9_free_variable_and_short_selling(self) -> None:
        self.assert_contract(
            self.expected["exercises"]["3.9"], self.results["exercises"]["3.9"]
        )

    def test_13_expected_contract_covers_all_executable_exercises(self) -> None:
        self.assertEqual(
            tuple(self.expected["exercises"]),
            ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.9"),
        )
        for exercise_id, expected in self.expected["exercises"].items():
            self.assert_contract(expected, self.results["exercises"][exercise_id])

    def test_14_serialization_is_deterministic(self) -> None:
        first = serialize_results(self.results)
        second = serialize_results(self.results)
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))

    def test_15_committed_results_match_frozen_replay(self) -> None:
        self.assertEqual(
            (HERE / "results.json").read_bytes(),
            serialize_results(self.results),
        )

    def test_16_rights_and_open_runtime_contract(self) -> None:
        self.assertEqual(self.data["content_license"], "CC-BY-SA-4.0")
        self.assertEqual(self.expected["content_license"], "CC-BY-SA-4.0")

        local_modules = {"model", "run_lab", "test_models"}
        external_imports: set[str] = set()
        for path in sorted(HERE.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            self.assertIn("SPDX-License-Identifier: MIT", source, path.name)
            tree = ast.parse(source)
            imported = {
                alias.name.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            imported.update(
                node.module.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            )
            external_imports.update(
                imported - sys.stdlib_module_names - local_modules - {"__future__"}
            )
        self.assertEqual(external_imports, {"pyomo"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
