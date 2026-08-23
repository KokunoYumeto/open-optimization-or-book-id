"""Regresi matematika, solver, aksesibilitas, provenance, dan hak Bab 6.

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


class Chapter6FormalMathematicsLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.expected = json.loads(
            (HERE / "expected-results.json").read_text(encoding="utf-8")
        )
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

    def test_01_frozen_source_hashes_match_live_closure(self) -> None:
        sources = self.data["provenance"]["source_files"]
        self.assertEqual(len(sources), 4)
        self.assertEqual(
            {source["role"] for source in sources},
            {
                "authority_chapter",
                "authority_manual",
                "translated_chapter",
                "translated_manual",
            },
        )
        for source in sources:
            path = LANE_ROOT / source["path"]
            self.assertTrue(path.is_file(), str(path))
            payload = path.read_bytes()
            self.assertEqual(len(payload), source["bytes"], str(path))
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(), source["sha256"], str(path)
            )

    def test_02_visible_attribution_identities_match_machine_data(self) -> None:
        attribution = (HERE / "ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn(
            self.data["provenance"]["authority_commit"], attribution
        )
        for source in self.data["provenance"]["source_files"]:
            self.assertEqual(attribution.count(source["sha256"]), 1)
            formatted_bytes = f"{source['bytes']:,}".replace(",", ".")
            self.assertIn(f"{formatted_bytes} byte", attribution)

    def test_03_exact_exercise_titles_difficulties_and_scope(self) -> None:
        self.assertEqual(tuple(self.data["exercises"]), EXERCISE_IDS)
        self.assertEqual(self.results["summary"]["exercise_count"], 12)
        self.assertEqual(self.results["summary"]["verified_count"], 12)
        self.assertEqual(
            [spec["difficulty"] for spec in self.data["exercises"].values()],
            [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3],
        )
        self.assertTrue(
            all(
                result["title"] == self.data["exercises"][exercise_id]["title"]
                for exercise_id, result in self.results["exercises"].items()
            )
        )

    def test_04_expected_contract_covers_every_exercise(self) -> None:
        self.assertEqual(
            tuple(self.expected["exercises"]), tuple(self.results["exercises"])
        )
        self.assert_contract(self.expected, self.results)

    def test_05_vector_and_combination_arithmetic_is_exact(self) -> None:
        first = self.results["exercises"]["6.1"]["calculation"]
        self.assertEqual(first["vector_sum"], [2, -2, 6])
        self.assertEqual(first["scalar_multiple"], [6, -4, 8])
        self.assertEqual(first["dot_product"], 5)
        second = self.results["exercises"]["6.2"]["calculation"]
        self.assertTrue(
            all(
                item["is_linear_combination"]
                for item in second["linear_combination_checks"].values()
            )
        )
        self.assertEqual(
            [
                pair_id
                for pair_id, item in second["convex_pair_checks"].items()
                if item["feasible"]
            ],
            ["v1_v2"],
        )

    def test_06_rank_is_checked_exactly_and_with_numpy(self) -> None:
        result = self.results["exercises"]["6.3"]["calculation"]
        self.assertEqual(result["determinant"], 0)
        self.assertEqual(result["exact_rank"], 1)
        self.assertEqual(result["numpy_rank"], 1)
        active = self.results["exercises"]["6.8"]["calculation"]["points"]
        for point in active.values():
            self.assertEqual(point["active_rank_exact"], point["active_rank_numpy"])

    def test_07_convexity_claims_have_valid_direct_certificates(self) -> None:
        sets = self.results["exercises"]["6.4"]["calculation"]["sets"]
        self.assertEqual(
            {set_id: item["classification"] for set_id, item in sets.items()},
            {"D": "convex", "H": "convex", "R": "nonconvex", "S": "nonconvex"},
        )
        for set_id in ("D", "H"):
            self.assertTrue(sets[set_id]["proof"])
        for set_id in ("R", "S"):
            self.assertTrue(sets[set_id]["witness_endpoints_in_set"])
            self.assertFalse(sets[set_id]["midpoint_in_set"])

    def test_08_matrix_lp_point_and_solver_optimum_match(self) -> None:
        result = self.results["exercises"]["6.5"]["calculation"]
        self.assertEqual(result["lhs_Ax"], [6, 4, "-6/5", "-8/5"])
        self.assertEqual(result["slack"], [0, 0, "6/5", "8/5"])
        self.assertEqual(result["active_rows"], [1, 2])
        self.assertEqual(result["objective_at_point"], "34/5")
        self.assertEqual(result["solver_checks"][0]["objective_exact"], "34/5")

    def test_09_triangle_barycentric_checks_include_infeasibility(self) -> None:
        result = self.results["exercises"]["6.6"]["calculation"]
        self.assertEqual(
            result["points"]["inside_boundary"]["weights"], [0, "1/2", "1/2"]
        )
        self.assertEqual(
            result["points"]["outside"]["weights"], ["-1/2", "3/4", "3/4"]
        )
        self.assertEqual(
            [item["termination_condition"] for item in result["solver_checks"]],
            ["optimal", "infeasible"],
        )

    def test_10_halfspace_geometry_uses_general_proof_not_one_sample(self) -> None:
        result = self.results["exercises"]["6.7"]["calculation"]
        self.assertEqual(result["boundary_intercepts"], [[4, 0], [0, 2]])
        self.assertTrue(result["midpoint_in_halfspace"])
        self.assertIn("lambda", result["convexity_proof"])
        self.assertIn("a·x", result["convexity_proof"])
        note_ids = {item["id"] for item in self.data["interpretive_notes"]}
        self.assertIn("note.ch06.ex06-07-midpoint", note_ids)

    def test_11_active_set_and_nonextreme_witness_are_complete(self) -> None:
        result = self.results["exercises"]["6.8"]["calculation"]
        corner = result["points"]["corner"]
        other = result["points"]["non_extreme"]
        self.assertEqual(corner["active_constraints"], ["c2", "c3"])
        self.assertTrue(corner["is_extreme_point"])
        self.assertEqual(other["active_constraints"], ["c2"])
        self.assertFalse(other["is_extreme_point"])
        self.assertTrue(result["non_extreme_certificate"]["endpoints_feasible"])

    def test_12_convex_representation_has_exact_unique_weights(self) -> None:
        result = self.results["exercises"]["6.9"]["calculation"]
        self.assertEqual(result["weights"], ["1/4", "1/4", "1/2"])
        self.assertFalse(result["extreme_directions_needed"])
        self.assertEqual(
            result["solver_checks"][0]["termination_condition"], "optimal"
        )

    def test_13_union_counterexample_and_sufficient_condition_are_distinct(self) -> None:
        result = self.results["exercises"]["6.10"]["calculation"]
        counterexample = result["counterexample"]
        self.assertTrue(counterexample["witness_endpoints_in_union"])
        self.assertFalse(counterexample["midpoint_in_union"])
        self.assertEqual(counterexample["midpoint_squared_distances_to_centers"], [4, 4])
        self.assertTrue(result["containment_condition"]["is_sufficient"])
        self.assertFalse(result["containment_condition"]["is_necessary"])

    def test_14_boundedness_counterexample_certifies_lineality_and_optimum(self) -> None:
        result = self.results["exercises"]["6.11"]["calculation"]
        self.assertEqual(result["lineality_A_times_d"], [0, 0])
        self.assertEqual(result["maximum_active_rank"], 1)
        self.assertEqual(result["vertex_count"], 0)
        self.assertEqual(result["optimal_value"], 0)
        self.assertEqual(result["optimal_set"], "{(t,0):t_in_R}")
        self.assertFalse(result["boundedness_hypothesis_holds"])

    def test_15_arbitrary_intersection_proof_keeps_all_quantifier_steps(self) -> None:
        result = self.results["exercises"]["6.12"]["calculation"]
        self.assertEqual(len(result["proof_steps"]), 7)
        self.assertTrue(all(item["validated"] for item in result["proof_steps"]))
        self.assertTrue(result["applies_to_infinite_index_families"])
        self.assertFalse(result["uses_cardinality_bound_on_index_set"])
        self.assertEqual(result["empty_intersection_case"], "vacuously_convex")

    def test_16_solver_calls_terminations_and_violations_are_locked(self) -> None:
        checks = [
            check
            for exercise in self.results["exercises"].values()
            for check in exercise["calculation"].get("solver_checks", [])
        ]
        self.assertEqual(len(checks), 5)
        self.assertEqual(
            [item["termination_condition"] for item in checks].count("optimal"), 4
        )
        self.assertEqual(
            [item["termination_condition"] for item in checks].count("infeasible"), 1
        )
        self.assertTrue(
            all(
                item.get("maximum_violation", 0.0) <= TOLERANCE
                for item in checks
            )
        )
        self.assertEqual(self.results["summary"]["solver_call_count"], 5)
        self.assertLessEqual(
            self.results["summary"]["maximum_solver_violation"], TOLERANCE
        )

    def test_17_svg_inventory_hashes_accessibility_and_scope(self) -> None:
        self.assertEqual(
            set(self.plot_payloads),
            {"ex06-06.svg", "ex06-07.svg", "ex06-08.svg", "ex06-10.svg", "ex06-11.svg"},
        )
        self.assertEqual(self.results["summary"]["plot_count"], 5)
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        for exercise_id, exercise in self.results["exercises"].items():
            plot = exercise["plot"]
            if plot["status"] != "generated":
                self.assertNotIn(exercise_id, {"6.6", "6.7", "6.8", "6.10", "6.11"})
                continue
            payload = self.plot_payloads[Path(plot["path"]).name]
            self.assertEqual(len(payload), plot["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), plot["sha256"])
            root = ET.fromstring(payload)
            self.assertEqual(root.attrib["role"], "img")
            self.assertEqual(root.attrib["lang"], "id")
            self.assertEqual(
                root.attrib["{http://www.w3.org/XML/1998/namespace}lang"], "id-ID"
            )
            self.assertIn("aria-labelledby", root.attrib)
            self.assertIsNotNone(root.find("svg:title", namespace))
            self.assertIsNotNone(root.find("svg:desc", namespace))
            metadata = root.find("svg:metadata", namespace)
            self.assertIsNotNone(metadata)
            self.assertIn("CC BY-SA 4.0", metadata.text)
            self.assertEqual(root.findall(".//svg:image", namespace), [])

    def test_18_code_imports_spdx_rights_and_runtime_notices_are_complete(self) -> None:
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
            external_imports.update(
                imported - sys.stdlib_module_names - local_modules - {"__future__"}
            )
        self.assertEqual(external_imports, {"numpy", "pyomo"})
        self.assertTrue(
            all_imports.isdisjoint(
                {"cplex", "gurobipy", "httpx", "mosek", "requests", "socket", "urllib"}
            )
        )
        components = {item["name"]: item for item in self.data["runtime_components"]}
        self.assertEqual(
            set(components), {"Pyomo", "HiGHS/highspy", "NumPy", "renderer SVG lokal"}
        )
        self.assertEqual(self.data["content_license"], "CC-BY-SA-4.0")
        for filename in ("README.md", "ATTRIBUTION.md", "LICENSE-CODE.txt"):
            self.assertTrue((HERE / filename).is_file(), filename)

    def test_19_no_missing_data_or_silent_corrections(self) -> None:
        self.assertEqual(self.data["underdetermined_exercises"], [])
        self.assertEqual(self.data["corrections"], [])
        self.assertEqual(self.results["summary"]["underdetermined_count"], 0)
        self.assertEqual(self.results["summary"]["correction_count"], 0)
        for exercise in self.data["exercises"].values():
            self.assertNotEqual(exercise["method"], "parameter_required")

    def test_20_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(serialize_results(first_results), serialize_results(second_results))
        self.assertEqual(first_plots, second_plots)

    def test_21_committed_outputs_match_clean_replay(self) -> None:
        self.assertEqual(
            (HERE / "results.json").read_bytes(), serialize_results(self.results)
        )
        self.assertEqual(
            {path.name for path in (HERE / "plots").glob("*.svg")},
            set(self.plot_payloads),
        )
        for filename, payload in self.plot_payloads.items():
            self.assertEqual((HERE / "plots" / filename).read_bytes(), payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
