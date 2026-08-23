"""Regresi numerik dan kontrak sumber untuk pendamping terbuka Bab 4.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from numbers import Real
from pathlib import Path

from pyomo.environ import Constraint, Var

from model import (
    TOLERANCE,
    IncompleteModelError,
    build_absolute_deviation,
    build_airline_max_flow,
    build_assignment,
    build_min_cost_flow_unstructured,
    build_min_cost_flow_warehouses,
    build_multi_period_investment,
    build_multicommodity_fractional,
    build_multicommodity_integer,
    build_production_10period,
    build_production_overtime,
    load_data,
    solve_all,
)
from run_lab import serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]


class Chapter4OpenLabTests(unittest.TestCase):
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

    def test_01_source_hashes_match_complete_frozen_closure(self) -> None:
        sources = self.data["provenance"]["source_files"]
        self.assertEqual(len(sources), 36)
        for source in sources:
            path = LANE_ROOT / source["path"]
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(path.stat().st_size, source["bytes"], str(path))
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                source["sha256"],
                str(path),
            )

    def test_02_operational_source_counts_are_exact(self) -> None:
        paths = [Path(item["path"]) for item in self.data["provenance"]["source_files"]]
        self.assertEqual(sum(path.suffix == ".xlsx" for path in paths), 11)
        self.assertEqual(sum(path.suffix == ".ipynb" for path in paths), 22)
        self.assertEqual(sum(path.suffix == ".csv" for path in paths), 1)
        self.assertEqual(sum(path.suffix == ".tex" for path in paths), 2)

    def test_03_model_topology_and_domains(self) -> None:
        specs = self.data["cases"]
        models_and_counts = (
            (build_production_10period(specs["production_10period"]), 20, 10),
            (
                build_assignment(
                    specs["assignment_machine"], name="topology_machine"
                ),
                16,
                8,
            ),
            (
                build_assignment(
                    specs["assignment_school_bus"], name="topology_bus"
                ),
                25,
                10,
            ),
            (
                build_assignment(
                    specs["assignment_generic"], name="topology_generic"
                ),
                9,
                6,
            ),
            (build_absolute_deviation(specs["absolute_deviation"]), 4, 6),
            (
                build_min_cost_flow_warehouses(specs["min_cost_flow_warehouses"]),
                4,
                4,
            ),
            (
                build_min_cost_flow_unstructured(
                    specs["min_cost_flow_unstructured"]
                ),
                10,
                8,
            ),
            (build_airline_max_flow(specs["airline_max_flow"]), 12, 5),
            (
                build_multicommodity_integer(specs["multicommodity_integer"]),
                8,
                12,
            ),
            (
                build_multicommodity_fractional(
                    specs["multicommodity_fractional"]
                ),
                10,
                13,
            ),
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
        integer_model = models_and_counts[-2][0]
        self.assertTrue(
            all(
                variable.is_integer()
                for variable in integer_model.component_data_objects(Var, active=True)
            )
        )
        assignment_model = models_and_counts[1][0]
        self.assertTrue(
            all(
                variable.is_binary()
                for variable in assignment_model.component_data_objects(Var, active=True)
            )
        )

    def test_04_every_executable_case_is_optimal_and_feasible(self) -> None:
        executions: list[dict] = []

        def visit(node) -> None:
            if isinstance(node, dict):
                if "execution" in node:
                    executions.append(node["execution"])
                for nested in node.values():
                    visit(nested)
            elif isinstance(node, list):
                for nested in node:
                    visit(nested)

        visit(self.results["cases"])
        solved = [item for item in executions if item["status"] != "not_run"]
        skipped = [item for item in executions if item["status"] == "not_run"]
        self.assertEqual(len(solved), 10)
        self.assertEqual(len(skipped), 2)
        for execution in solved:
            self.assertEqual(execution["solver"], "appsi_highs")
            self.assertEqual(execution["termination_condition"], "optimal")
            self.assertIn(execution["status"], {"ok", "warning"})
            self.assertLessEqual(execution["maximum_violation"], TOLERANCE)

    def test_05_production_ten_periods(self) -> None:
        self.assert_contract(
            self.expected["cases"]["production_10period"],
            self.results["cases"]["production_10period"],
        )

    def test_06_three_assignment_instances(self) -> None:
        for case_id in (
            "assignment_machine",
            "assignment_school_bus",
            "assignment_generic",
        ):
            self.assert_contract(
                self.expected["cases"][case_id], self.results["cases"][case_id]
            )
        generic = self.results["cases"]["assignment_generic"]
        self.assertEqual(
            generic["objective"],
            38.0 + 33.0 + 27.0,
            "Answer Report workbook yang menyatakan 129 tidak boleh diwarisi",
        )

    def test_07_absolute_deviation_keeps_x_free(self) -> None:
        model = build_absolute_deviation(self.data["cases"]["absolute_deviation"])
        self.assertIsNone(model.x.lb)
        self.assertIsNone(model.x.ub)
        self.assert_contract(
            self.expected["cases"]["absolute_deviation"],
            self.results["cases"]["absolute_deviation"],
        )

    def test_08_warehouse_min_cost_flow(self) -> None:
        self.assert_contract(
            self.expected["cases"]["min_cost_flow_warehouses"],
            self.results["cases"]["min_cost_flow_warehouses"],
        )

    def test_09_unstructured_flow_uses_corrected_arc_and_positive_demand(self) -> None:
        spec = self.data["cases"]["min_cost_flow_unstructured"]
        result = self.results["cases"]["min_cost_flow_unstructured"]
        self.assertIn("d->b", spec["arc_cost"])
        self.assertNotIn("b->d", spec["arc_cost"])
        self.assert_contract(
            self.expected["cases"]["min_cost_flow_unstructured"], result
        )
        flows = result["route_flow"]
        for node, demand in spec["net_demand"].items():
            inflow = sum(
                flow for arc, flow in flows.items() if arc.partition("->")[2] == node
            )
            outflow = sum(
                flow for arc, flow in flows.items() if arc.partition("->")[0] == node
            )
            self.assertAlmostEqual(inflow - outflow, demand, delta=TOLERANCE)

    def test_10_airline_max_flow_uses_dt_and_cut_certificate(self) -> None:
        spec = self.data["cases"]["airline_max_flow"]
        result = self.results["cases"]["airline_max_flow"]
        self.assertEqual(spec["arc_capacity"]["d->t"], 7)
        self.assertNotIn("d->e", spec["arc_capacity"])
        self.assert_contract(self.expected["cases"]["airline_max_flow"], result)
        self.assertAlmostEqual(
            result["objective"], result["certifying_cut_capacity"], delta=TOLERANCE
        )

    def test_11_integer_multicommodity_cost_and_direction(self) -> None:
        result = self.results["cases"]["multicommodity_integer"]
        self.assert_contract(
            self.expected["cases"]["multicommodity_integer"], result
        )
        self.assertEqual(result["route_flow"]["1->3"], {"1": 0.0, "2": 5.0})
        self.assertNotIn("3->1", result["route_flow"])

    def test_12_fractional_multicommodity_omits_degenerate_split(self) -> None:
        result = self.results["cases"]["multicommodity_fractional"]
        self.assert_contract(
            self.expected["cases"]["multicommodity_fractional"], result
        )
        self.assertNotIn("per_commodity_route_flow", result)
        self.assertTrue(result["per_commodity_routes_omitted_due_to_degeneracy"])

    def test_13_balance_conventions_are_distinct_and_explicit(self) -> None:
        conventions = self.data["balance_conventions"]
        self.assertEqual(
            tuple(sorted(conventions)),
            (
                "positive_demand_in_minus_out",
                "positive_supply_out_minus_in",
                "source_sink_fraction",
            ),
        )
        self.assertIn("keluar", conventions["positive_supply_out_minus_in"])
        self.assertIn("masuk", conventions["positive_demand_in_minus_out"])

    def test_14_incomplete_cases_fail_closed(self) -> None:
        cases = self.data["cases"]
        with self.assertRaisesRegex(IncompleteModelError, "regular_capacity"):
            build_production_overtime(cases["production_overtime"])
        with self.assertRaisesRegex(IncompleteModelError, "kas menganggur"):
            build_multi_period_investment(cases["investment_multi_period"])
        for case_id in ("production_overtime", "investment_multi_period"):
            self.assert_contract(
                self.expected["cases"][case_id], self.results["cases"][case_id]
            )

    def test_15_divergence_register_is_complete_and_deduplicated(self) -> None:
        divergences = self.data["divergences"]
        identifiers = [item["id"] for item in divergences]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(
            set(identifiers),
            {
                "div.ch04.airline-terminal-arc",
                "div.ch04.assignment-workbook-report",
                "div.ch04.investment-semantics",
                "div.ch04.multicommodity-direction-and-cost",
                "div.ch04.overtime-capacity-omission",
                "div.ch04.unstructured-arc-direction",
            },
        )

    def test_16_expected_contract_covers_all_cases(self) -> None:
        self.assertEqual(
            tuple(self.expected["cases"]), tuple(self.results["cases"])
        )
        for case_id, expected in self.expected["cases"].items():
            self.assert_contract(expected, self.results["cases"][case_id])

    def test_17_serialization_is_deterministic(self) -> None:
        first = serialize_results(self.results)
        second = serialize_results(self.results)
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))

    def test_18_committed_results_match_frozen_replay(self) -> None:
        self.assertEqual(
            (HERE / "results.json").read_bytes(),
            serialize_results(self.results),
        )

    def test_19_rights_and_open_runtime_contract(self) -> None:
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
