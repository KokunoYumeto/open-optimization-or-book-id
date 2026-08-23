"""Regresi numerik, geometri, aksesibilitas, dan hak Bab 5.

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

from pyomo.environ import Constraint, Var

from model import (
    EXERCISE_IDS,
    TOLERANCE,
    ParameterRequiredError,
    build_model,
    load_data,
)
from plot_svg import generate_plot_payloads
from run_lab import assemble_results, serialize_results
from verify_receipt import validate_provenance_closure


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]


class Chapter5GraphicalLabTests(unittest.TestCase):
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
            self.assertEqual(path.stat().st_size, source["bytes"], str(path))
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                source["sha256"],
                str(path),
            )
        validate_provenance_closure(self.data)

    def test_02_exact_exercise_and_scenario_scope(self) -> None:
        self.assertEqual(tuple(self.data["exercises"]), EXERCISE_IDS)
        self.assertEqual(len(self.data["exercises"]), 17)
        self.assertEqual(
            sum(
                len(spec["scenarios"])
                for spec in self.data["exercises"].values()
            ),
            19,
        )
        self.assertEqual(self.results["summary"]["scenario_solve_count"], 19)
        self.assertEqual(self.results["summary"]["executable_exercise_count"], 16)

    def test_03_model_topology_matches_machine_data(self) -> None:
        for exercise_id, spec in self.data["exercises"].items():
            if spec["model_status"] != "executable":
                continue
            for scenario_id in spec["scenarios"]:
                model = build_model(exercise_id, spec, scenario_id)
                self.assertEqual(
                    len(tuple(model.component_data_objects(Var, active=True))),
                    len(spec["variables"]),
                    f"{exercise_id}/{scenario_id}",
                )
                self.assertEqual(
                    len(tuple(model.component_data_objects(Constraint, active=True))),
                    len(spec["constraints"]),
                    f"{exercise_id}/{scenario_id}",
                )

    def test_04_expected_contract_covers_every_result(self) -> None:
        self.assertEqual(
            tuple(self.expected["exercises"]), tuple(self.results["exercises"])
        )
        self.assert_contract(self.expected, self.results)

    def test_05_solver_classifications_and_violations(self) -> None:
        counts: dict[str, int] = {}
        for exercise in self.results["exercises"].values():
            for scenario in exercise["scenarios"].values():
                classification = scenario["classification"]
                counts[classification] = counts.get(classification, 0) + 1
                execution = scenario["execution"]
                self.assertEqual(execution["solver"], "appsi_highs")
                if classification in {
                    "feasible_region_unbounded",
                    "optimal_nonunique",
                    "optimal_unique",
                }:
                    self.assertEqual(execution["termination_condition"], "optimal")
                    self.assertLessEqual(execution["maximum_violation"], TOLERANCE)
                elif classification == "infeasible":
                    self.assertEqual(execution["termination_condition"], "infeasible")
                elif classification == "unbounded":
                    self.assertEqual(execution["termination_condition"], "unbounded")
        self.assertEqual(counts, self.expected["summary"]["classification_counts"])
        self.assertLessEqual(
            self.results["summary"]["maximum_solver_violation"], TOLERANCE
        )

    def test_06_all_stated_vertices_are_independently_verified(self) -> None:
        for exercise_id, spec in self.data["exercises"].items():
            geometry = self.results["exercises"][exercise_id]["geometry"]
            if spec["model_status"] == "executable":
                self.assertEqual(geometry["status"], "verified")
                if len(spec["variables"]) == 2:
                    self.assert_contract(
                        sorted(spec["expected_vertices"]),
                        sorted(geometry["vertices"]),
                        f"vertices.{exercise_id}",
                    )
            else:
                self.assertEqual(geometry["status"], "not_run")

    def test_07_nonunique_optimal_sets_are_preserved_as_segments(self) -> None:
        expected_nonunique = {
            ("5.5", "original"),
            ("5.12", "manual_construction"),
            ("5.13", "lemon_edge"),
            ("5.13", "water_edge"),
            ("5.17", "edge_tie"),
        }
        actual_nonunique = {
            (exercise_id, scenario_id)
            for exercise_id, exercise in self.results["exercises"].items()
            for scenario_id, scenario in exercise["scenarios"].items()
            if scenario["classification"] == "optimal_nonunique"
        }
        self.assertEqual(actual_nonunique, expected_nonunique)
        for exercise_id, scenario_id in expected_nonunique:
            self.assertEqual(
                len(
                    self.results["exercises"][exercise_id]["scenarios"][scenario_id][
                        "segment"
                    ]
                ),
                2,
            )

    def test_08_unbounded_rays_and_pinned_direction_are_certified(self) -> None:
        unbounded = {
            ("5.8", "original"),
            ("5.9", "as_written"),
            ("5.15", "original"),
            ("5.16", "maximum"),
        }
        for exercise_id, scenario_id in unbounded:
            scenario = self.results["exercises"][exercise_id]["scenarios"][
                scenario_id
            ]
            self.assertTrue(scenario["improving_ray_certificates"])
        directions_516 = {
            tuple(ray["direction"])
            for ray in self.results["exercises"]["5.16"]["geometry"][
                "ray_certificates"
            ]
        }
        self.assertIn((2.0, 1.0), directions_516)
        self.assertNotIn((1.0, 2.0), directions_516)

    def test_09_diet_rhs_and_exact_optimum_use_pinned_authority(self) -> None:
        diet = self.data["exercises"]["5.10"]
        self.assertEqual([constraint["rhs"] for constraint in diet["constraints"]], [0.4, 0.3])
        result = self.results["exercises"]["5.10"]["scenarios"]["fractional_lp"]
        self.assertEqual(result["point_exact"], ["110/191", "280/191", "0"])
        self.assertEqual(result["objective_exact"], "11650/191")
        self.assertEqual(
            self.results["exercises"]["5.10"]["plot"]["reason"],
            "not_applicable_dimension_3",
        )

    def test_10_exercise_58_and_59_divergences_are_not_silently_repaired(self) -> None:
        constraint = self.data["exercises"]["5.8"]["constraints"][1]
        self.assertEqual(constraint["coefficients"], {"x": 1, "y": 3})
        self.assertEqual(constraint["rhs"], 3)
        self.assertEqual(
            self.results["exercises"]["5.9"]["scenarios"]["as_written"][
                "classification"
            ],
            "unbounded",
        )
        divergence_ids = {item["id"] for item in self.data["divergences"]}
        self.assertIn("div.ch05.ex05-08-manual-constraint", divergence_ids)
        self.assertIn("div.ch05.ex05-09-title-objective", divergence_ids)

    def test_11_conceptual_exercise_fails_closed(self) -> None:
        conceptual = self.data["exercises"]["5.11"]
        self.assertEqual(conceptual["variables"], [])
        self.assertEqual(conceptual["constraints"], [])
        self.assertEqual(conceptual["scenarios"], {})
        with self.assertRaisesRegex(ParameterRequiredError, "memerlukan parameter"):
            build_model("5.11", conceptual, "invented")
        result = self.results["exercises"]["5.11"]
        self.assertEqual(result["execution"]["status"], "not_run")
        self.assertEqual(result["plot"]["reason"], "parameter_required")

    def test_12_six_target_corrections_and_two_authority_facts_are_typed(self) -> None:
        correction_ids = {
            item["id"]
            for item in self.data["divergences"]
            if item["status"] in {"target_corrected", "target_accessibility_corrected"}
        }
        self.assertEqual(
            correction_ids,
            {
                "div.ch05.closing-figure-accessibility",
                "div.ch05.ex05-07-selected-solution-envelope",
                "div.ch05.furniture-alt-bound-change",
                "div.ch05.furniture-inactive-bound",
                "div.ch05.gradient-versus-level-curve",
                "div.ch05.unbounded-example-ray-start",
            },
        )
        self.assertEqual(
            {item["id"] for item in self.data["authority_facts"]},
            {
                "fact.ch05.ex05-10-pinned-rhs-repair",
                "fact.ch05.ex05-16-pinned-direction-repair",
            },
        )
        self.assertTrue(
            all(
                item["status"] == "present_in_pinned_authority"
                for item in self.data["authority_facts"]
            )
        )

    def test_13_plot_inventory_hashes_and_accessibility(self) -> None:
        self.assertEqual(len(self.plot_payloads), 18)
        self.assertEqual(self.results["summary"]["plot_count"], 18)
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        for exercise_id, exercise in self.results["exercises"].items():
            plot_record = exercise["plot"]
            if plot_record["status"] != "generated":
                self.assertIn(exercise_id, {"5.10", "5.11"})
                self.assertTrue(plot_record["description_id"])
                continue
            for scenario in plot_record["scenarios"].values():
                filename = Path(scenario["path"]).name
                payload = self.plot_payloads[filename]
                self.assertEqual(len(payload), scenario["bytes"])
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(), scenario["sha256"]
                )
                root = ET.fromstring(payload)
                self.assertEqual(root.attrib["role"], "img")
                self.assertIn("aria-labelledby", root.attrib)
                self.assertEqual(root.attrib["lang"], "id")
                self.assertEqual(
                    root.attrib["{http://www.w3.org/XML/1998/namespace}lang"],
                    "id-ID",
                )
                self.assertIsNotNone(root.find("svg:title", namespace))
                self.assertIsNotNone(root.find("svg:desc", namespace))
                self.assertTrue(scenario["alt_text_id"])

    def test_14_infeasible_plot_has_no_false_feasible_polygon(self) -> None:
        payload = self.plot_payloads["ex05_06_original.svg"]
        root = ET.fromstring(payload)
        regions = [
            element
            for element in root.iter()
            if element.tag.endswith("polygon") and element.attrib.get("class") == "region"
        ]
        self.assertEqual(regions, [])

    def test_15_code_has_no_proprietary_or_network_imports(self) -> None:
        local_modules = {
            "model",
            "plot_svg",
            "run_lab",
            "test_models",
            "verify_receipt",
        }
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
        self.assertEqual(external_imports, {"pyomo"})
        self.assertTrue(
            all_imports.isdisjoint(
                {"cplex", "gurobipy", "httpx", "mosek", "requests", "socket", "urllib"}
            )
        )

    def test_16_rights_and_component_manifest_are_complete(self) -> None:
        self.assertEqual(self.data["content_license"], "CC-BY-SA-4.0")
        components = {item["name"]: item for item in self.data["runtime_components"]}
        self.assertEqual(
            set(components), {"Pyomo", "HiGHS/highspy", "NumPy", "renderer SVG lokal"}
        )
        self.assertEqual(components["Pyomo"]["license_expression"], "BSD-3-Clause")
        self.assertEqual(components["HiGHS/highspy"]["license_expression"], "MIT")
        self.assertEqual(components["renderer SVG lokal"]["license_expression"], "MIT")
        for filename in ("ATTRIBUTION.md", "LICENSE-CODE.txt", "README.md"):
            self.assertTrue((HERE / filename).is_file(), filename)

    def test_17_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(serialize_results(first_results), serialize_results(second_results))
        self.assertEqual(first_plots, second_plots)

    def test_18_committed_outputs_match_clean_replay(self) -> None:
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
