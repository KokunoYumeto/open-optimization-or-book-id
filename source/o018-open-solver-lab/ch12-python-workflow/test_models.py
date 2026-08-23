"""Uji laboratorium alur kerja Python Bab 12.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

from model import EXERCISE_IDS, LANE_ROOT, evaluate_all, load_data
from run_lab import assemble_results, compare_output, serialize_results


HERE = Path(__file__).resolve().parent


class PythonWorkflowLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.results = assemble_results(cls.data)
        cls.expected = json.loads(
            (HERE / "expected-results.json").read_text(encoding="utf-8")
        )

    def assert_subset(self, expected, actual) -> None:
        if isinstance(expected, dict):
            self.assertIsInstance(actual, dict)
            for key, expected_value in expected.items():
                self.assertIn(key, actual)
                self.assert_subset(expected_value, actual[key])
        elif isinstance(expected, list):
            self.assertEqual(len(expected), len(actual))
            for expected_value, actual_value in zip(expected, actual):
                self.assert_subset(expected_value, actual_value)
        else:
            self.assertEqual(expected, actual)

    def test_01_frozen_authority_and_translation_hashes_match(self) -> None:
        for record in self.data["provenance"]["source_files"]:
            path = LANE_ROOT / record["path"]
            self.assertTrue(path.is_file(), path)
            payload = path.read_bytes()
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())

    def test_02_visible_attribution_matches_machine_provenance(self) -> None:
        attribution = (HERE / "ATTRIBUTION.md").read_text(encoding="utf-8")
        for record in self.data["provenance"]["source_files"]:
            self.assertIn(record["sha256"], attribution)
        for notice in ("CC BY-SA 4.0", "MIT", "Pyomo 6.10.1", "HiGHS 1.15.1"):
            self.assertIn(notice, attribution)

    def test_03_scope_order_labels_titles_and_difficulties(self) -> None:
        self.assertEqual(EXERCISE_IDS, tuple(self.data["exercises"]))
        self.assertEqual([1, 1, 1, 2, 2, 2, 2, 2, 3], [x["difficulty"] for x in self.data["exercises"].values()])
        self.assertEqual(9, len({x["book_label"] for x in self.data["exercises"].values()}))
        self.assertEqual(9, len({x["title"] for x in self.data["exercises"].values()}))

    def test_04_book_manual_mapping_is_complete(self) -> None:
        for exercise_id, spec in self.data["exercises"].items():
            self.assertEqual(
                {"manual_id": exercise_id, "status": "aligned"},
                spec["manual_mapping"],
            )

    def test_05_expected_summary_matches(self) -> None:
        self.assert_subset(self.expected["summary"], self.results["summary"])

    def test_06_exercise_12_1_new_profit(self) -> None:
        self.assert_subset(self.expected["12.1"], self.results["exercises"]["12.1"]["certificate"])

    def test_07_exercise_12_2_translation(self) -> None:
        self.assert_subset(self.expected["12.2"], self.results["exercises"]["12.2"]["certificate"])

    def test_08_exercise_12_3_demand_change(self) -> None:
        exercise = self.results["exercises"]["12.3"]
        self.assert_subset(self.expected["12.3"], exercise["certificate"])
        self.assertTrue(all(value == 0 for value in exercise["solver_checks"][0]["market_surplus"].values()))

    def test_09_exercise_12_4_three_plant_transport(self) -> None:
        exercise = self.results["exercises"]["12.4"]
        self.assert_subset(self.expected["12.4"], exercise["certificate"])
        self.assertTrue(all(value == 0 for value in exercise["solver_checks"][0]["market_surplus"].values()))

    def test_10_exercise_12_5_duals_and_slacks(self) -> None:
        self.assert_subset(self.expected["12.5"], self.results["exercises"]["12.5"]["certificate"])

    def test_11_exercise_12_6_epsilon_sweep(self) -> None:
        exercise = self.results["exercises"]["12.6"]
        self.assert_subset(self.expected["12.6"], exercise["certificate"])
        self.assertEqual(5, len(exercise["solver_checks"]))

    def test_12_exercise_12_7_model_bugs_are_detected_by_invariants(self) -> None:
        exercise = self.results["exercises"]["12.7"]
        self.assert_subset(self.expected["12.7"], exercise["certificate"])
        self.assertNotEqual(
            exercise["certificate"]["overwritten_objective_equivalent"]["reported_objective"],
            exercise["certificate"]["overwritten_objective_equivalent"]["actual_profit"],
        )

    def test_13_exercise_12_8_objective_sense(self) -> None:
        self.assert_subset(self.expected["12.8"], self.results["exercises"]["12.8"]["certificate"])

    def test_14_exercise_12_9_rhs_sweep(self) -> None:
        exercise = self.results["exercises"]["12.9"]
        self.assert_subset(self.expected["12.9"], exercise["certificate"])
        self.assertEqual(
            ["3/4", "3/4", "3/4", "1/4", "1/4", "1/4", "1/4", 0, 0, 0],
            [check["labor_dual"] for check in exercise["solver_checks"]],
        )

    def test_15_solver_calls_terminations_and_violation_are_locked(self) -> None:
        checks = [
            check
            for exercise in self.results["exercises"].values()
            for check in exercise["solver_checks"]
        ]
        self.assertEqual(25, len(checks))
        self.assertTrue(
            all(
                check["solver"] == "appsi_highs"
                and check["termination_condition"] == "optimal"
                for check in checks
            )
        )
        self.assertLessEqual(max(float(check["maximum_violation"]) for check in checks), 1e-8)
        self.assertEqual({"optimal": 25}, self.results["summary"]["solver_termination_counts"])

    def test_16_no_unresolved_defects_or_o018_math_corrections(self) -> None:
        self.assertEqual([], self.results["unresolved_exercises"])
        self.assertEqual([], self.results["source_defects"])
        self.assertEqual(0, self.results["summary"]["o018_math_correction_count"])

    def test_17_all_exercises_are_verified_and_methods_are_distinct(self) -> None:
        self.assertEqual(9, self.results["summary"]["verified_count"])
        self.assertTrue(all(item["status"] == "verified" for item in self.results["exercises"].values()))
        self.assertEqual(9, len(self.results["summary"]["method_counts"]))

    def test_18_readme_exposes_six_step_open_workflow(self) -> None:
        readme = (HERE / "README.md").read_text(encoding="utf-8")
        for marker in (
            "ConcreteModel",
            "Var",
            "Objective",
            "Constraint",
            'SolverFactory("appsi_highs")',
            "status",
            "pelanggaran maksimum",
        ):
            self.assertIn(marker, readme)

    def test_19_code_spdx_and_no_proprietary_network_or_pulp_imports(self) -> None:
        forbidden_import = re.compile(
            r"^\s*(?:from|import)\s+(?:gurobi|gurobipy|cplex|mosek|pulp|requests|urllib|socket)\b",
            re.MULTILINE,
        )
        for filename in ("model.py", "run_lab.py", "test_models.py", "verify_receipt.py"):
            path = HERE / filename
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("SPDX-License-Identifier: MIT", text)
            self.assertIsNone(forbidden_import.search(text))

    def test_20_frozen_runtime_lock_is_visible(self) -> None:
        requirements = (HERE.parent / "requirements.lock").read_text(encoding="utf-8")
        for requirement in ("pyomo==6.10.1", "highspy==1.15.1", "numpy==2.5.2", "--require-hashes"):
            self.assertIn(requirement, requirements)

    def test_21_generation_is_byte_deterministic_in_memory(self) -> None:
        first = serialize_results(evaluate_all(self.data))
        second = serialize_results(evaluate_all(self.data))
        self.assertEqual(first, second)

    def test_22_committed_output_matches_clean_replay(self) -> None:
        payload = serialize_results(self.results)
        self.assertEqual([], compare_output(HERE / "results.json", payload))


if __name__ == "__main__":
    unittest.main()
