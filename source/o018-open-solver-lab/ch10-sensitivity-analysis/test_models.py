"""Uji laboratorium analisis sensitivitas Bab 10.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from model import EXERCISE_IDS, LANE_ROOT, evaluate_all, load_data
from plot_svg import PLOT_IDS, generate_plot_payloads
from run_lab import assemble_results, compare_outputs, serialize_results


HERE = Path(__file__).resolve().parent


class SensitivityLabTests(unittest.TestCase):
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
        oracle = dict(self.expected[exercise_id])
        oracle.pop("status", None)
        return oracle

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
        for correction in self.data["corrections"]:
            self.assertIn(correction["id"], attribution)
        for notice in ("CC BY-SA 4.0", "MIT", "Pyomo 6.10.1", "HiGHS 1.15.1"):
            self.assertIn(notice, attribution)

    def test_03_exact_scope_order_titles_and_difficulties(self) -> None:
        self.assertEqual(EXERCISE_IDS, tuple(self.data["exercises"]))
        expected_titles = [
            "Harga Bayangan dari Kamus Akhir",
            "Rentang Sensitivitas Ruas Kanan",
            "Sensitivitas Koefisien Objektif",
            "Analisis Sensitivitas Lengkap",
            "Menentukan Rentang Koefisien Basis dan Nonbasis",
            "Sensitivitas dari Invers Basis",
            "Membaca Laporan Sensitivitas",
            "Penafsiran Harga Bayangan",
            "Mengapa Kendala Berslack Berharga Nol",
            "Mengapa Rentang Itu Ada",
            "Ketika Prediksi Harga Bayangan Gagal",
            "Melampaui Rentang",
        ]
        self.assertEqual(
            expected_titles,
            [spec["title"] for spec in self.data["exercises"].values()],
        )
        self.assertEqual(
            [1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3],
            [spec["difficulty"] for spec in self.data["exercises"].values()],
        )

    def test_04_independent_expected_oracle_covers_every_exercise(self) -> None:
        self.assertEqual(
            set(EXERCISE_IDS) | {"summary"}, set(self.expected)
        )
        self.assert_subset(
            self.expected["summary"], self.results["summary"]
        )

    def test_05_three_target_corrections_are_closed_and_algebraic(self) -> None:
        self.assertEqual(3, len(self.results["corrections"]))
        ids = [item["id"] for item in self.results["corrections"]]
        self.assertEqual(
            [
                "CORR-CH10-RHS-B1-SLACK",
                "CORR-CH10-RHS-B3-SLACK",
                "CORR-CH10-MATRIX-AN-SIGNS",
            ],
            ids,
        )
        matrix = self.results["exercises"]["10.1"]["certificate"][
            "matrix_sign_correction"
        ]["A_B_inverse_A_N"]
        self.assertEqual([[2, -1], [-1, 1], [-3, 1]], matrix)
        basis = np.array([[1, 1, 0], [2, 1, 1], [1, 2, 0]], dtype=float)
        nonbasic = np.array([[1, 0], [0, 0], [0, 1]], dtype=float)
        np.testing.assert_allclose(
            np.linalg.inv(basis) @ nonbasic,
            np.array(matrix, dtype=float),
            atol=1e-12,
        )
        self.assertEqual(0, self.results["summary"]["o018_math_correction_count"])

    def test_06_exercise_10_1_dictionary_prices_and_offer(self) -> None:
        self.assert_subset(
            self.oracle_for("10.1"),
            self.results["exercises"]["10.1"]["certificate"],
        )

    def test_07_exercise_10_2_rhs_range(self) -> None:
        self.assert_subset(
            self.oracle_for("10.2"),
            self.results["exercises"]["10.2"]["certificate"],
        )

    def test_08_exercise_10_3_cost_range(self) -> None:
        self.assert_subset(
            self.oracle_for("10.3"),
            self.results["exercises"]["10.3"]["certificate"],
        )

    def test_09_exercise_10_4_complete_sensitivity(self) -> None:
        self.assert_subset(
            self.oracle_for("10.4"),
            self.results["exercises"]["10.4"]["certificate"],
        )

    def test_10_exercise_10_5_basic_and_nonbasic_costs(self) -> None:
        self.assert_subset(
            self.oracle_for("10.5"),
            self.results["exercises"]["10.5"]["certificate"],
        )

    def test_11_exercise_10_6_basis_inverse(self) -> None:
        self.assert_subset(
            self.oracle_for("10.6"),
            self.results["exercises"]["10.6"]["certificate"],
        )

    def test_12_exercise_10_7_fails_closed_without_primal_matrix(self) -> None:
        exercise = self.results["exercises"]["10.7"]
        self.assertEqual("verified_fail_closed", exercise["status"])
        self.assertEqual([], exercise["solver_checks"])
        self.assert_subset(
            self.oracle_for("10.7"), exercise["certificate"]
        )
        self.assertIn("tidak tersedia", exercise["certificate"]["fail_closed_reason"])

    def test_13_exercise_10_8_shadow_prices(self) -> None:
        self.assert_subset(
            self.oracle_for("10.8"),
            self.results["exercises"]["10.8"]["certificate"],
        )

    def test_14_exercise_10_9_nonbinding_proof(self) -> None:
        certificate = self.results["exercises"]["10.9"]["certificate"]
        self.assert_subset(self.oracle_for("10.9"), certificate)
        self.assertEqual(4, len(certificate["proof_steps"]))

    def test_15_exercise_10_10_range_certificate(self) -> None:
        certificate = self.results["exercises"]["10.10"]["certificate"]
        self.assert_subset(self.oracle_for("10.10"), certificate)
        self.assertEqual(2, len(certificate["endpoint_events"]))

    def test_16_exercise_10_11_degenerate_one_sided_prices(self) -> None:
        self.assert_subset(
            self.oracle_for("10.11"),
            self.results["exercises"]["10.11"]["certificate"],
        )

    def test_17_exercise_10_12_extrapolation_failure(self) -> None:
        certificate = self.results["exercises"]["10.12"]["certificate"]
        self.assert_subset(self.oracle_for("10.12"), certificate)
        self.assertEqual(3, len(certificate["piecewise_value"]))

    def test_18_solver_calls_terminations_and_violation_are_locked(self) -> None:
        checks = [
            check
            for exercise in self.results["exercises"].values()
            for check in exercise["solver_checks"]
        ]
        self.assertEqual(29, len(checks))
        self.assertTrue(
            all(
                check["solver"] == "appsi_highs"
                and check["termination_condition"] == "optimal"
                for check in checks
            )
        )
        self.assertLessEqual(
            max(float(check["maximum_violation"]) for check in checks),
            1e-8,
        )
        self.assertEqual(
            {"optimal": 29},
            self.results["summary"]["solver_termination_counts"],
        )

    def test_19_methods_statuses_and_missing_data_are_visible(self) -> None:
        self.assertEqual(
            12, len(self.results["summary"]["method_counts"])
        )
        self.assertEqual(
            1, self.results["summary"]["underdetermined_count"]
        )
        self.assertEqual(
            ["10.7"],
            [
                item["exercise_id"]
                for item in self.results["underdetermined_exercises"]
            ],
        )
        self.assertEqual(
            12, self.results["summary"]["verified_count"]
        )

    def test_20_svg_inventory_hashes_accessibility_and_scope(self) -> None:
        self.assertEqual(
            {"ex10-03.svg", "ex10-11.svg", "ex10-12.svg"},
            set(self.plots),
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
            self.assertEqual("id-ID", root.attrib["{http://www.w3.org/XML/1998/namespace}lang"])
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

    def test_21_code_spdx_rights_runtime_and_no_proprietary_imports(self) -> None:
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
        requirements = (HERE.parent / "requirements.lock").read_text(
            encoding="utf-8"
        )
        for requirement in (
            "pyomo==6.10.1",
            "highspy==1.15.1",
            "numpy==2.5.2",
            "--require-hashes",
        ):
            self.assertIn(requirement, requirements)

    def test_22_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(
            serialize_results(first_results),
            serialize_results(second_results),
        )
        self.assertEqual(first_plots, second_plots)

    def test_23_committed_outputs_match_clean_replay(self) -> None:
        payload = serialize_results(self.results)
        self.assertEqual(
            [],
            compare_outputs(
                HERE / "results.json",
                HERE / "plots",
                payload,
                self.plots,
            ),
        )


if __name__ == "__main__":
    unittest.main()
