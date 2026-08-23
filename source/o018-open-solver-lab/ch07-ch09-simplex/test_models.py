"""Regresi matematika, solver, SVG, provenance, dan hak klaster simpleks.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from numbers import Real
from pathlib import Path

from model import EXERCISE_IDS, TOLERANCE, load_data
from plot_svg import generate_plot_payloads
from run_lab import assemble_results, serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]


class SimplexClusterLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.expected = json.loads((HERE / "expected-results.json").read_text(encoding="utf-8"))
        cls.results, cls.plot_payloads = assemble_results(cls.data)

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
            for key, value_ in expected.items():
                self.assertIn(key, actual, f"{path}.{key}")
                self.assert_contract(value_, actual[key], f"{path}.{key}")
        elif isinstance(expected, list):
            self.assertIsInstance(actual, list, path)
            self.assertEqual(len(expected), len(actual), path)
            for index, value_ in enumerate(expected):
                self.assert_contract(value_, actual[index], f"{path}[{index}]")
        else:
            self.assertEqual(actual, expected, path)

    def test_01_frozen_authority_and_translation_hashes_match(self) -> None:
        sources = self.data["provenance"]["source_files"]
        self.assertEqual(len(sources), 12)
        self.assertEqual(len({source["role"] for source in sources}), 12)
        self.assertEqual(sum(source["role"].startswith("authority_") for source in sources), 6)
        self.assertEqual(sum(source["role"].startswith("translated_") for source in sources), 6)
        for source in sources:
            path = LANE_ROOT / source["path"]
            self.assertTrue(path.is_file(), str(path))
            payload = path.read_bytes()
            self.assertEqual(len(payload), source["bytes"], str(path))
            self.assertEqual(hashlib.sha256(payload).hexdigest(), source["sha256"], str(path))

    def test_02_visible_attribution_matches_machine_provenance(self) -> None:
        attribution = (HERE / "ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn(self.data["authority_commit"], attribution)
        for source in self.data["provenance"]["source_files"]:
            self.assertEqual(attribution.count(source["sha256"]), 1)
            formatted = f"{source['bytes']:,}".replace(",", ".")
            self.assertIn(f"{formatted} byte", attribution)

    def test_03_exact_scope_order_titles_and_difficulties(self) -> None:
        self.assertEqual(tuple(self.data["exercises"]), EXERCISE_IDS)
        self.assertEqual(self.results["summary"]["chapter_counts"], {"7": 17, "8": 9, "9": 12})
        self.assertEqual(self.results["summary"]["difficulty_counts"], {"1": 12, "2": 23, "3": 3})
        self.assertTrue(
            all(
                self.results["exercises"][exercise_id]["title"] == spec["title"]
                for exercise_id, spec in self.data["exercises"].items()
            )
        )

    def test_04_independent_expected_oracle_covers_every_exercise(self) -> None:
        self.assertEqual(tuple(self.expected["exercises"]), tuple(self.results["exercises"]))
        contract = {
            key: value_
            for key, value_ in self.expected.items()
            if key != "numerical_tolerance"
        }
        self.assert_contract(contract, self.results)

    def test_05_standardization_is_symbolic_and_exact(self) -> None:
        seven_two = self.results["exercises"]["7.2"]["calculation"]
        self.assertEqual(seven_two["equations"][1]["coefficients"]["s2"], -1)
        seven_three = self.results["exercises"]["7.3"]["calculation"]
        self.assertEqual(seven_three["substitutions"]["x3"], {"x3_plus": 1, "x3_minus": -1})
        seven_four = self.results["exercises"]["7.4"]["calculation"]
        self.assertEqual(seven_four["objective"]["x3_neg"], 3)
        self.assertTrue(all(self.results["exercises"][item]["calculation"]["all_variables_nonnegative"] for item in ("7.2", "7.3", "7.4", "7.5", "7.6")))

    def test_06_dictionary_paths_preserve_every_source_pivot(self) -> None:
        for exercise_id in ("7.7", "7.8", "7.9", "7.10", "7.11"):
            spec = self.data["exercises"][exercise_id]
            path = self.results["exercises"][exercise_id]["calculation"]["path"]
            actual = [[pivot["entering"], pivot["leaving"]] for pivot in path["pivots"]]
            self.assertEqual(actual, spec["expected_pivots"], exercise_id)
            self.assertEqual(len(path["states"]), len(actual) + 1)
            self.assertEqual(path["classification"], "optimal")
            self.assertTrue(all(pivot["ratios"] for pivot in path["pivots"]))

    def test_07_symbolic_big_m_paths_remove_artificials(self) -> None:
        for exercise_id in ("7.12", "7.13"):
            calculation = self.results["exercises"][exercise_id]["calculation"]
            self.assertEqual(set(calculation["artificial_variables_final"].values()), {0})
            self.assertTrue(any("M" in str(value_) for value_ in calculation["path"]["states"][0]["objective_reduced_costs"].values()))
            final_costs = calculation["path"]["states"][-1]["objective_reduced_costs"]
            self.assertFalse(
                any(
                    "M" in str(value_)
                    for variable, value_ in final_costs.items()
                    if not variable.startswith("a")
                )
            )
        self.assertEqual(self.results["exercises"]["7.13"]["calculation"]["final_decision_point"], {"x1": "15/4", "x2": "35/4", "x3": 0})

    def test_08_dictionary_parameter_conditions_have_direct_certificates(self) -> None:
        calculation = self.results["exercises"]["7.14"]["calculation"]
        self.assertEqual(calculation["conditions"]["current_basis_infeasible"], "b<0")
        self.assertIn("a2<=0", calculation["conditions"]["feasible_and_unbounded_sufficient"])
        self.assertEqual(calculation["certificate"]["unbounded_ray_effect"]["z"], "+c1*t")

    def test_09_geometry_basis_and_pivot_are_exact(self) -> None:
        calculation = self.results["exercises"]["7.15"]["calculation"]
        self.assertEqual(calculation["D"]["slacks"], {"s1": 9, "s2": "13/3", "s3": "28/3", "s4": 0})
        self.assertEqual(calculation["pivot_D_to_C"], {"entering": "x1", "leaving": "s3", "edge_keeps_nonbasic": "s4"})
        self.assertEqual(calculation["solver_checks"][0]["objective"], 17.0)

    def test_10_wrong_ratio_row_exposes_infeasible_basis(self) -> None:
        calculation = self.results["exercises"]["7.16"]["calculation"]
        self.assertEqual(calculation["correct_ratio_test"]["minimum_rows"], ["s1"])
        wrong = calculation["wrong_pivot"]["resulting_dictionary"]
        self.assertEqual(wrong["basic_solution"], {"x": 6, "y": 4, "s1": -1, "s2": 0, "s3": 0})
        self.assertEqual(wrong["objective_value"], 24)

    def test_11_ratio_tie_preserves_both_degenerate_branches(self) -> None:
        calculation = self.results["exercises"]["7.17"]["calculation"]
        self.assertEqual(calculation["tied_rows"], ["s1", "s2"])
        self.assertEqual(calculation["branch_s1_leaves"]["basic_solution"]["s2"], 0)
        self.assertEqual(calculation["branch_s2_leaves"]["basic_solution"]["s1"], 0)
        self.assertEqual(calculation["branch_s2_leaves"]["objective_reduced_costs"]["y"], 0)
        self.assertIn("bukan solusi optimal berbeda", calculation["zero_reduced_cost_interpretation"])

    def test_12_basis_solutions_use_fraction_and_numpy_checks(self) -> None:
        for exercise_id in ("8.1", "8.2", "8.3"):
            calculation = self.results["exercises"][exercise_id]["calculation"]
            self.assertTrue(calculation["numpy_agrees"])
            self.assertTrue(calculation["nonsingular"])
        self.assertFalse(self.results["exercises"]["8.2"]["calculation"]["feasible"])

    def test_13_reduced_costs_distinguish_nonoptimal_and_optimal_bases(self) -> None:
        bases = self.results["exercises"]["8.4"]["calculation"]["bases"]
        self.assertEqual(bases[0]["reduced_costs"], {"x": "1/2", "s3": "-3/2"})
        self.assertFalse(bases[0]["optimal_for_max"])
        self.assertEqual(bases[1]["reduced_costs"], {"s1": -1, "s3": -1})
        self.assertTrue(bases[1]["optimal_for_max"])

    def test_14_all_six_two_column_bases_and_singular_example_are_kept(self) -> None:
        calculation = self.results["exercises"]["8.5"]["calculation"]
        records = calculation["basis_records"]
        self.assertEqual(len(records), 6)
        self.assertEqual(sum(record["feasible"] for record in records), 4)
        self.assertEqual([record["determinant"] for record in records], [-7, -5, 1, -3, 2, 1])
        self.assertFalse(calculation["dependent_column_example"]["nonsingular"])

    def test_15_matrix_formula_reconstructs_full_dictionary(self) -> None:
        dictionary = self.results["exercises"]["8.6"]["calculation"]["dictionary"]
        self.assertEqual(dictionary["equations"]["x"], {"constant": 6, "coefficients": {"s1": "-3/4", "s2": "1/4"}})
        self.assertEqual(dictionary["equations"]["y"], {"constant": 5, "coefficients": {"s1": "5/4", "s2": "-3/4"}})
        self.assertEqual(dictionary["objective"], {"constant": 17, "coefficients": {"s1": "-1/4", "s2": "-1/4"}})

    def test_16_matrix_proofs_retain_identity_sign_and_uniqueness_cases(self) -> None:
        self.assertTrue(self.results["exercises"]["8.7"]["calculation"]["validated"])
        self.assertTrue(self.results["exercises"]["8.8"]["calculation"]["validated"])
        proof = self.results["exercises"]["8.9"]["calculation"]
        self.assertTrue(proof["unique_optimum"])
        self.assertEqual([case["condition"] for case in proof["cases"]], ["x_N!=0", "x_N=0"])

    def test_17_tableau_reading_keeps_sign_convention(self) -> None:
        first = self.results["exercises"]["9.1"]["calculation"]
        self.assertFalse(first["optimal"])
        self.assertEqual(first["dictionary"]["objective_reduced_costs"], {"x": "1/2", "s3": "-3/2"})
        second = self.results["exercises"]["9.2"]["calculation"]
        self.assertTrue(second["optimal"])
        self.assertEqual(second["dictionary"]["objective_reduced_costs"], {"s1": -3, "s2": -1})

    def test_18_ratio_and_one_pivot_tableau_match_exact_rows(self) -> None:
        third = self.results["exercises"]["9.3"]["calculation"]
        self.assertEqual(third["ratios"], {"s1": 3, "s2": 2, "s3": 4})
        fourth = self.results["exercises"]["9.4"]["calculation"]["tableau_after_pivot"]
        self.assertEqual(fourth["objective"], {"coefficients": [0, -2, 0, 1, 0], "rhs": 8})
        self.assertEqual(fourth["rows"][2]["coefficients"], [0, "13/4", 0, "-3/4", 1])

    def test_19_complete_tableau_paths_have_initial_and_every_pivot(self) -> None:
        for exercise_id in ("9.5", "9.6"):
            calculation = self.results["exercises"][exercise_id]["calculation"]
            self.assertEqual(len(calculation["tableau_path"]), 3)
            self.assertEqual(len(calculation["path"]["states"]), 3)
            self.assertEqual(calculation["tableau_path"][-1]["basis"], ["x", "y"])
            self.assertEqual(calculation["path"]["classification"], "optimal")

    def test_20_big_m_tableau_keeps_symbolic_objective_and_full_path(self) -> None:
        calculation = self.results["exercises"]["9.7"]["calculation"]
        self.assertEqual(calculation["initial_symbolic_tableau"]["objective"]["coefficients"], ["-M-4", "-M-3", "M", 0, 0])
        self.assertEqual([(item["entering"], item["leaving"]) for item in calculation["full_path"]["pivots"]], [("x", "a1"), ("e1", "s2")])
        self.assertEqual(calculation["final_decision_point"], {"x": 10, "y": 0})

    def test_21_tableau_sign_and_dictionary_conversion_are_exact(self) -> None:
        sign = self.results["exercises"]["9.8"]["calculation"]
        self.assertEqual(sign["tableau_objective_row"], {"x1": -3, "x2": 2, "rhs": 12})
        dictionary = self.results["exercises"]["9.9"]["calculation"]["dictionary"]
        self.assertEqual(dictionary["equations"]["x1"]["coefficients"], {"s1": -2, "s2": 1})
        self.assertEqual(dictionary["objective_value"], 40)

    def test_22_unbounded_and_infeasible_certificates_fail_closed(self) -> None:
        ten = self.results["exercises"]["9.10"]["calculation"]
        self.assertEqual(ten["classification"], "unbounded")
        self.assertEqual(ten["limiting_rows"], [])
        self.assertIn("tidak direka", ten["scope_note"])
        eleven = self.results["exercises"]["9.11"]["calculation"]
        self.assertEqual(eleven["classification_original_lp"], "infeasible")
        self.assertEqual(eleven["positive_artificial_basic_value"], {"a1": 3})
        twelve = self.results["exercises"]["9.12"]["calculation"]
        self.assertEqual(twelve["ray"]["direction"], [1, 1])
        self.assertEqual(twelve["solver_checks"][0]["termination_condition"], "unbounded")

    def test_23_solver_calls_terminations_and_violations_are_locked(self) -> None:
        checks = [
            check
            for exercise in self.results["exercises"].values()
            for check in exercise["calculation"].get("solver_checks", [])
        ]
        self.assertEqual(len(checks), 16)
        self.assertEqual(sum(item["termination_condition"] == "optimal" for item in checks), 15)
        self.assertEqual(sum(item["termination_condition"] == "unbounded" for item in checks), 1)
        self.assertTrue(all(item.get("maximum_violation", 0.0) <= TOLERANCE for item in checks))
        self.assertLessEqual(self.results["summary"]["maximum_solver_violation"], TOLERANCE)

    def test_24_svg_inventory_hashes_accessibility_and_scope(self) -> None:
        self.assertEqual(set(self.plot_payloads), {"ex07-15.svg", "ex07-17.svg", "ex09-12.svg"})
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        for exercise_id, exercise in self.results["exercises"].items():
            plot = exercise["plot"]
            if plot["status"] != "generated":
                self.assertNotIn(exercise_id, {"7.15", "7.17", "9.12"})
                continue
            payload = self.plot_payloads[Path(plot["path"]).name]
            self.assertEqual(len(payload), plot["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), plot["sha256"])
            root = ET.fromstring(payload)
            self.assertEqual(root.attrib["role"], "img")
            self.assertEqual(root.attrib["lang"], "id")
            self.assertEqual(root.attrib["{http://www.w3.org/XML/1998/namespace}lang"], "id-ID")
            self.assertIn("aria-labelledby", root.attrib)
            self.assertIsNotNone(root.find("svg:title", namespace))
            self.assertIsNotNone(root.find("svg:desc", namespace))
            metadata = root.find("svg:metadata", namespace)
            self.assertIsNotNone(metadata)
            self.assertIn("CC BY-SA 4.0", metadata.text)
            self.assertEqual(root.findall(".//svg:image", namespace), [])

    def test_25_code_imports_spdx_rights_and_runtime_notices_close(self) -> None:
        local_modules = {"model", "plot_svg", "run_lab", "test_models", "verify_receipt"}
        external_imports: set[str] = set()
        all_imports: set[str] = set()
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
            all_imports.update(imported)
            external_imports.update(imported - sys.stdlib_module_names - local_modules - {"__future__"})
        self.assertEqual(external_imports, {"numpy", "pyomo"})
        self.assertTrue(all_imports.isdisjoint({"cplex", "gurobipy", "httpx", "mosek", "requests", "socket", "urllib"}))
        self.assertEqual(self.data["content_license"], "CC-BY-SA-4.0")
        self.assertEqual(self.data["code_license"], "MIT")
        components = {item["name"] for item in self.data["runtime_components"]}
        self.assertEqual(components, {"Pyomo", "HiGHS/highspy", "NumPy", "renderer SVG lokal"})

    def test_26_no_missing_data_silent_corrections_or_hidden_divergence(self) -> None:
        self.assertEqual(self.data["underdetermined_exercises"], [])
        self.assertEqual(self.data["corrections"], [])
        self.assertEqual([item["exercise"] for item in self.data["source_manual_divergences"]], ["7.12", "7.13", "8.8"])
        self.assertTrue(all(item["kind"] == "title_only" for item in self.data["source_manual_divergences"]))
        self.assertEqual(self.results["summary"]["source_manual_title_divergence_count"], 3)

    def test_27_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(serialize_results(first_results), serialize_results(second_results))
        self.assertEqual(first_plots, second_plots)

    def test_28_committed_outputs_match_clean_replay(self) -> None:
        self.assertEqual((HERE / "results.json").read_bytes(), serialize_results(self.results))
        self.assertEqual({path.name for path in (HERE / "plots").glob("*.svg")}, set(self.plot_payloads))
        for filename, payload in self.plot_payloads.items():
            self.assertEqual((HERE / "plots" / filename).read_bytes(), payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
