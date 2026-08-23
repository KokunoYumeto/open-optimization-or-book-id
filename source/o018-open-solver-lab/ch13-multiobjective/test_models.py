"""Uji laboratorium optimisasi multiobjektif Bab 13.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from model import EXERCISE_IDS, LANE_ROOT, evaluate_all, load_data
from plot_svg import PLOT_IDS, generate_plot_payloads
from run_lab import assemble_results, compare_outputs, serialize_results


HERE = Path(__file__).resolve().parent


class MultiobjectiveLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.results, cls.plots = assemble_results(cls.data)
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

    def oracle_for(self, exercise_id: str) -> dict:
        return self.expected[exercise_id]

    def test_01_frozen_authority_and_translation_hashes_match(self) -> None:
        for record in self.data["provenance"]["source_files"]:
            path = LANE_ROOT / record["path"]
            self.assertTrue(path.is_file(), path)
            payload = path.read_bytes()
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(
                record["sha256"], hashlib.sha256(payload).hexdigest()
            )

    def test_02_visible_attribution_matches_machine_provenance(self) -> None:
        attribution = (HERE / "ATTRIBUTION.md").read_text(encoding="utf-8")
        for record in self.data["provenance"]["source_files"]:
            self.assertIn(record["sha256"], attribution)
        for defect in self.data["source_defects"]:
            self.assertIn(defect["id"], attribution)
        for notice in ("CC BY-SA 4.0", "MIT", "Pyomo 6.10.1", "HiGHS 1.15.1"):
            self.assertIn(notice, attribution)

    def test_03_exact_scope_order_labels_titles_and_difficulties(self) -> None:
        self.assertEqual(EXERCISE_IDS, tuple(self.data["exercises"]))
        self.assertEqual(
            [1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 3],
            [spec["difficulty"] for spec in self.data["exercises"].values()],
        )
        expected_labels = [
            "ex:pareto-def",
            "ex:moo-dominance",
            "ex:moo-weighted-scores",
            "ex:pareto-table",
            "ex:weighted-sum-projects",
            "ex:eps-constraint-lp",
            "ex:eps-triangle",
            "ex:tradeoff-analysis",
            "ex:nonconvex-weights",
            "ex:lex-vs-weighted",
            "ex:furniture-weights",
        ]
        self.assertEqual(
            expected_labels,
            [spec["book_label"] for spec in self.data["exercises"].values()],
        )

    def test_04_manual_discrepancy_is_explicit_without_renumbering(self) -> None:
        mapping = {
            key: spec["manual_mapping"]
            for key, spec in self.data["exercises"].items()
        }
        for index in range(1, 10):
            exercise_id = f"13.{index}"
            self.assertEqual("aligned", mapping[exercise_id]["status"])
            self.assertEqual(exercise_id, mapping[exercise_id]["manual_id"])
        self.assertEqual("missing_from_manual", mapping["13.10"]["status"])
        self.assertIsNone(mapping["13.10"]["manual_id"])
        self.assertEqual("manual_stale_alias", mapping["13.11"]["status"])
        self.assertEqual("13.10", mapping["13.11"]["manual_id"])
        self.assertEqual(list(EXERCISE_IDS), self.results["manual_alignment"]["book_primary_ids"])

    def test_05_independent_expected_oracle_covers_every_exercise(self) -> None:
        self.assertEqual(set(EXERCISE_IDS) | {"summary"}, set(self.expected))
        self.assert_subset(self.expected["summary"], self.results["summary"])

    def test_06_source_defect_inventory_and_o018_correction_count(self) -> None:
        self.assertEqual(3, len(self.results["source_defects"]))
        self.assertEqual(
            [
                "DEF-CH13-MANUAL-OMISSION",
                "DEF-CH13-70PCT-FIGURE",
                "DEF-CH13-REVENUE-PROFIT-TERMS",
            ],
            [item["id"] for item in self.results["source_defects"]],
        )
        self.assertEqual(0, self.results["summary"]["o018_math_correction_count"])

    def test_07_exercise_13_1_definition(self) -> None:
        self.assert_subset(
            self.oracle_for("13.1"),
            self.results["exercises"]["13.1"]["certificate"],
        )

    def test_08_exercise_13_2_dominance_and_frontier(self) -> None:
        exercise = self.results["exercises"]["13.2"]
        self.assert_subset(self.oracle_for("13.2"), exercise["certificate"])
        self.assertEqual(4, len(exercise["solver_checks"]))

    def test_09_exercise_13_3_weighted_scores(self) -> None:
        self.assert_subset(
            self.oracle_for("13.3"),
            self.results["exercises"]["13.3"]["certificate"],
        )

    def test_10_exercise_13_4_supported_and_unsupported_frontier(self) -> None:
        exercise = self.results["exercises"]["13.4"]
        self.assert_subset(self.oracle_for("13.4"), exercise["certificate"])
        self.assertEqual("A", exercise["solver_checks"][-1]["selected"])

    def test_11_exercise_13_5_projects(self) -> None:
        self.assert_subset(
            self.oracle_for("13.5"),
            self.results["exercises"]["13.5"]["certificate"],
        )

    def test_12_exercise_13_6_continuous_epsilon_lp(self) -> None:
        exercise = self.results["exercises"]["13.6"]
        self.assert_subset(self.oracle_for("13.6"), exercise["certificate"])
        points = [check["point"] for check in exercise["solver_checks"]]
        self.assertEqual(
            [
                {"x1": 3, "x2": 1},
                {"x1": 1, "x2": 3},
                {"x1": 4, "x2": 0},
                {"x1": 0, "x2": 4},
            ],
            points,
        )

    def test_13_exercise_13_7_triangle_sweep(self) -> None:
        exercise = self.results["exercises"]["13.7"]
        self.assert_subset(self.oracle_for("13.7"), exercise["certificate"])
        self.assertEqual(
            [6, 10, 14, 18],
            [check["epsilon"] for check in exercise["solver_checks"]],
        )

    def test_14_exercise_13_8_tradeoff_and_budget(self) -> None:
        exercise = self.results["exercises"]["13.8"]
        self.assert_subset(self.oracle_for("13.8"), exercise["certificate"])
        self.assertEqual("S2", exercise["solver_checks"][0]["selected"])

    def test_15_exercise_13_9_nonconvex_frontier(self) -> None:
        exercise = self.results["exercises"]["13.9"]
        self.assert_subset(self.oracle_for("13.9"), exercise["certificate"])
        self.assertEqual("Q", exercise["solver_checks"][-1]["selected"])

    def test_16_exercise_13_10_is_solved_without_manual_entry(self) -> None:
        exercise = self.results["exercises"]["13.10"]
        self.assert_subset(self.oracle_for("13.10"), exercise["certificate"])
        self.assertEqual("verified_without_manual_solution", exercise["status"])
        self.assertEqual("missing_from_manual", exercise["manual_mapping"]["status"])
        self.assertEqual({"x": 10, "y": 8}, exercise["solver_checks"][1]["point"])

    def test_17_exercise_13_11_stale_manual_alias_and_breakpoints(self) -> None:
        exercise = self.results["exercises"]["13.11"]
        self.assert_subset(self.oracle_for("13.11"), exercise["certificate"])
        self.assertEqual("manual_stale_alias", exercise["manual_mapping"]["status"])
        self.assertEqual("13.10", exercise["manual_mapping"]["manual_id"])
        self.assertEqual(
            [{"x": 0, "y": 0}, {"x": 0, "y": 20}, {"x": 10, "y": 8}],
            [check["point"] for check in exercise["solver_checks"][:3]],
        )

    def test_18_solver_calls_terminations_and_violation_are_locked(self) -> None:
        checks = [
            check
            for exercise in self.results["exercises"].values()
            for check in exercise["solver_checks"]
        ]
        self.assertEqual(36, len(checks))
        self.assertTrue(
            all(
                check["solver"] == "appsi_highs"
                and check["termination_condition"] == "optimal"
                for check in checks
            )
        )
        self.assertLessEqual(
            max(float(check["maximum_violation"]) for check in checks), 1e-8
        )
        self.assertEqual(
            {"optimal": 36}, self.results["summary"]["solver_termination_counts"]
        )

    def test_19_methods_statuses_and_unresolved_inventory(self) -> None:
        self.assertEqual(11, len(self.results["summary"]["method_counts"]))
        self.assertEqual([], self.results["unresolved_exercises"])
        self.assertEqual(0, self.results["summary"]["unresolved_count"])
        self.assertEqual(11, self.results["summary"]["verified_count"])

    def test_20_figure_70_percent_defect_certificate_is_exact(self) -> None:
        self.assertEqual(68000, 8000 * Fraction(17, 2) + 2000 * 0)
        self.assertEqual(68000, 8000 * 5 + 2000 * 14)
        self.assertEqual(67200, Fraction(7, 10) * 96000)
        self.assertEqual(
            Fraction(67200),
            8000 * Fraction(34, 7) + 2000 * Fraction(496, 35),
        )

    def test_21_svg_inventory_hashes_accessibility_and_scope(self) -> None:
        self.assertEqual(
            {"ex13-04.svg", "ex13-07.svg", "ex13-09.svg"}, set(self.plots)
        )
        generated_ids = {
            exercise_id
            for exercise_id, exercise in self.results["exercises"].items()
            if exercise["plot"]["status"] == "generated"
        }
        self.assertEqual(set(PLOT_IDS), generated_ids)
        namespace = "{http://www.w3.org/2000/svg}"
        for filename, payload in self.plots.items():
            root = ET.fromstring(payload)
            self.assertEqual("img", root.attrib["role"])
            self.assertEqual(
                "id-ID",
                root.attrib["{http://www.w3.org/XML/1998/namespace}lang"],
            )
            title = root.find(f"{namespace}title")
            description = root.find(f"{namespace}desc")
            metadata = root.find(f"{namespace}metadata")
            self.assertTrue(title is not None and (title.text or "").strip())
            self.assertTrue(
                description is not None and (description.text or "").strip()
            )
            self.assertIsNotNone(metadata)
            machine = json.loads(metadata.text or "{}")
            self.assertEqual("id-ID", machine["language"])
            self.assertIn("alternative_text", machine)
            record = next(
                exercise["plot"]
                for exercise in self.results["exercises"].values()
                if exercise["plot"].get("path") == f"plots/{filename}"
            )
            self.assertEqual(len(payload), record["bytes"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(), record["sha256"]
            )

    def test_22_plot_generation_covers_only_declared_exercises(self) -> None:
        payloads, records = generate_plot_payloads(self.data)
        self.assertEqual(self.plots, payloads)
        self.assertEqual(3, sum(item["status"] == "generated" for item in records.values()))
        self.assertEqual(8, sum(item["status"] == "not_required" for item in records.values()))

    def test_23_code_spdx_rights_and_no_proprietary_or_network_imports(self) -> None:
        code_files = [
            "model.py",
            "plot_svg.py",
            "run_lab.py",
            "test_models.py",
            "verify_receipt.py",
        ]
        forbidden_import = re.compile(
            r"^\s*(?:from|import)\s+(?:gurobi|gurobipy|cplex|mosek|requests|urllib|socket)\b",
            re.MULTILINE,
        )
        for filename in code_files:
            path = HERE / filename
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("SPDX-License-Identifier: MIT", text)
            self.assertIsNone(forbidden_import.search(text))

    def test_24_frozen_runtime_lock_is_visible(self) -> None:
        requirements = (HERE.parent / "requirements.lock").read_text(encoding="utf-8")
        for requirement in (
            "pyomo==6.10.1",
            "highspy==1.15.1",
            "numpy==2.5.2",
            "--require-hashes",
        ):
            self.assertIn(requirement, requirements)

    def test_25_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(
            serialize_results(first_results), serialize_results(second_results)
        )
        self.assertEqual(first_plots, second_plots)

    def test_26_committed_outputs_match_clean_replay(self) -> None:
        payload = serialize_results(self.results)
        self.assertEqual(
            [],
            compare_outputs(
                HERE / "results.json", HERE / "plots", payload, self.plots
            ),
        )


if __name__ == "__main__":
    unittest.main()
