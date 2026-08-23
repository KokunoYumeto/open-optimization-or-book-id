"""Uji regresi laboratorium dualitas Bab 11.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np

from model import EXERCISE_IDS, load_data
from run_lab import assemble_results, compare_outputs, serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]
PLOT_IDS = ("11.16",)


class DualityLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.expected = json.loads(
            (HERE / "expected-results.json").read_text(encoding="utf-8")
        )
        cls.results, cls.plots = assemble_results(cls.data)

    def assert_subset(self, expected, actual) -> None:
        if isinstance(expected, dict):
            self.assertIsInstance(actual, dict)
            for key, expected_value in expected.items():
                self.assertIn(key, actual)
                self.assert_subset(expected_value, actual[key])
        elif isinstance(expected, list):
            self.assertIsInstance(actual, list)
            self.assertEqual(len(expected), len(actual))
            for expected_value, actual_value in zip(expected, actual):
                self.assert_subset(expected_value, actual_value)
        else:
            self.assertEqual(expected, actual)

    def oracle_for(self, exercise_id: str) -> dict:
        return self.expected[exercise_id]

    def all_solver_checks(self) -> list[dict]:
        checks = [
            check
            for exercise in self.results["exercises"].values()
            for check in exercise["solver_checks"]
        ]
        checks.extend(
            check
            for correction in self.results["corrections"]
            for check in correction["solver_checks"]
        )
        return checks

    def test_01_frozen_authority_and_translation_hashes_match(self) -> None:
        self.assertEqual(6, len(self.data["provenance"]["source_files"]))
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
        for defect in self.data["upstream_defects"]:
            self.assertIn(defect["id"], attribution)
        for notice in (
            "CC BY-SA 4.0",
            "MIT",
            "Pyomo 6.10.1",
            "HiGHS 1.15.1",
            "NumPy 2.5.2",
        ):
            self.assertIn(notice, attribution)

    def test_03_exact_scope_order_titles_and_difficulties(self) -> None:
        self.assertEqual(EXERCISE_IDS, tuple(self.data["exercises"]))
        expected_titles = [
            "Masalah Dual Toko Roti Kecil",
            "Rumuskan Masalah Dual",
            "Memverifikasi Dualitas Lemah",
            "Batas Dualitas Lemah",
            "Masalah Dual dengan Kendala Campuran",
            "Harga Bayangan dan Variabel Dual",
            "Sertifikat dengan Kata-kata Anda Sendiri",
            "Dualitas Kuat dan Ketaklayakan",
            "Dual dari Dual adalah Primal",
            "Memeriksa Syarat-syarat",
            "Produksi Toko Roti dan Interpretasi Dualitas",
            "Kendala Kotak dan Sertifikat Dual",
            "Menurunkan Solusi Primal dari Tebakan Dual",
            "Harga Positif pada Kendala yang Longgar",
            "Menyangkal Klaim Solusi Optimal",
            "Optimisasi Paket Makanan dan Dualitas",
            "Dualitas dengan Jenis Kendala Campuran: Perusahaan Rintisan Kemasan Ramah Lingkungan",
        ]
        self.assertEqual(
            expected_titles,
            [spec["title"] for spec in self.data["exercises"].values()],
        )
        self.assertEqual(
            [1, 1, 1, 2, 2, 2, 2, 2, 3, 1, 2, 2, 2, 2, 2, 3, 3],
            [spec["difficulty"] for spec in self.data["exercises"].values()],
        )

    def test_04_independent_expected_oracle_covers_every_exercise(self) -> None:
        self.assertEqual(set(EXERCISE_IDS) | {"summary"}, set(self.expected))
        self.assert_subset(self.expected["summary"], self.results["summary"])

    def test_05_three_source_corrections_are_preserved_and_closed(self) -> None:
        ids = [item["id"] for item in self.results["corrections"]]
        self.assertEqual(
            [
                "CORR-CH11-CASE2-GEQ",
                "CORR-CH11-MIXED-SIGNS-FREE",
                "CORR-CH11-EX11-13-CANDIDATE",
            ],
            ids,
        )
        first = self.results["corrections"][0]["verification"]
        self.assertEqual(first["corrected_primal_value"], first["corrected_dual_value"])
        second = self.results["corrections"][1]["verification"]
        self.assertGreater(
            float(second["primal_x1_lower_bound"].split("/")[0])
            / float(second["primal_x1_lower_bound"].split("/")[1]),
            float(second["primal_x1_upper_bound"].split("/")[0])
            / float(second["primal_x1_upper_bound"].split("/")[1]),
        )
        self.assertEqual(-1, second["ray_objective_change"])
        self.assertFalse(
            self.results["corrections"][2]["verification"]["candidate_is_dual_feasible"]
        )
        self.assertEqual(0, self.results["summary"]["o018_math_correction_count"])

    def test_06_two_high_confidence_upstream_defects_have_certificates(self) -> None:
        defects = self.results["upstream_defects"]
        self.assertEqual(2, len(defects))
        self.assertTrue(all(item["confidence"] == "high" for item in defects))
        self.assertEqual("0<=-2", self.results["exercises"]["11.8"]["certificate"]["primal_sum_certificate"])
        material = np.array([4, 6, 4], dtype=float)
        retail = np.array([6, 9, 8], dtype=float)
        np.testing.assert_array_equal(1.5 * material + np.array([0, 0, 2]), retail)
        self.assertEqual(360, self.results["exercises"]["11.17"]["certificate"]["retail_implied_lower_bound"])

    def test_07_exercise_11_1_small_bakery_dual(self) -> None:
        self.assert_subset(self.oracle_for("11.1"), self.results["exercises"]["11.1"]["certificate"])

    def test_08_exercise_11_2_matrix_transpose_dual(self) -> None:
        self.assert_subset(self.oracle_for("11.2"), self.results["exercises"]["11.2"]["certificate"])

    def test_09_exercise_11_3_weak_duality_sandwich(self) -> None:
        self.assert_subset(self.oracle_for("11.3"), self.results["exercises"]["11.3"]["certificate"])

    def test_10_exercise_11_4_coincident_bounds(self) -> None:
        self.assert_subset(self.oracle_for("11.4"), self.results["exercises"]["11.4"]["certificate"])

    def test_11_exercise_11_5_mixed_form(self) -> None:
        self.assert_subset(self.oracle_for("11.5"), self.results["exercises"]["11.5"]["certificate"])

    def test_12_exercise_11_6_shadow_price_and_cs(self) -> None:
        self.assert_subset(self.oracle_for("11.6"), self.results["exercises"]["11.6"]["certificate"])

    def test_13_exercise_11_7_certificate_proof_record(self) -> None:
        exercise = self.results["exercises"]["11.7"]
        self.assertEqual("verified_proof", exercise["status"])
        self.assertEqual([], exercise["solver_checks"])
        self.assert_subset(self.oracle_for("11.7"), exercise["certificate"])
        self.assertEqual(4, len(exercise["certificate"]["proof_steps"]))

    def test_14_exercise_11_8_both_sides_infeasible(self) -> None:
        exercise = self.results["exercises"]["11.8"]
        self.assert_subset(self.oracle_for("11.8"), exercise["certificate"])
        self.assertEqual(
            ["infeasible", "infeasible"],
            [check["termination_condition"] for check in exercise["solver_checks"]],
        )

    def test_15_exercise_11_9_symbolic_involution(self) -> None:
        exercise = self.results["exercises"]["11.9"]
        self.assertEqual("verified_proof", exercise["status"])
        self.assert_subset(self.oracle_for("11.9"), exercise["certificate"])
        self.assertEqual(4, len(exercise["certificate"]["proof_steps"]))

    def test_16_exercise_11_10_termwise_cs(self) -> None:
        self.assert_subset(self.oracle_for("11.10"), self.results["exercises"]["11.10"]["certificate"])

    def test_17_exercise_11_11_bakery_perturbations(self) -> None:
        exercise = self.results["exercises"]["11.11"]
        self.assert_subset(self.oracle_for("11.11"), exercise["certificate"])
        self.assertEqual(5, len(exercise["solver_checks"]))

    def test_18_exercise_11_12_box_certificate(self) -> None:
        self.assert_subset(self.oracle_for("11.12"), self.results["exercises"]["11.12"]["certificate"])

    def test_19_exercise_11_13_feasibility_gate(self) -> None:
        certificate = self.results["exercises"]["11.13"]["certificate"]
        self.assert_subset(self.oracle_for("11.13"), certificate)
        self.assertFalse(certificate["candidate_is_dual_feasible"])
        self.assertEqual("17<23", certificate["weak_duality_alarm"])

    def test_20_exercise_11_14_joint_optimality_logic(self) -> None:
        exercise = self.results["exercises"]["11.14"]
        self.assertEqual("verified_proof", exercise["status"])
        self.assert_subset(self.oracle_for("11.14"), exercise["certificate"])
        self.assertEqual(3, len(exercise["certificate"]["logical_possibilities"]))

    def test_21_exercise_11_15_claim_disproof(self) -> None:
        self.assert_subset(self.oracle_for("11.15"), self.results["exercises"]["11.15"]["certificate"])

    def test_22_exercise_11_16_meal_kit_geometry(self) -> None:
        self.assert_subset(self.oracle_for("11.16"), self.results["exercises"]["11.16"]["certificate"])

    def test_23_exercise_11_17_mixed_startup_and_redundancy(self) -> None:
        certificate = self.results["exercises"]["11.17"]["certificate"]
        self.assert_subset(self.oracle_for("11.17"), certificate)
        self.assertTrue(certificate["retail_redundancy_verified"])

    def test_24_solver_calls_classifications_and_zero_violation_are_locked(self) -> None:
        checks = self.all_solver_checks()
        self.assertEqual(36, len(checks))
        self.assertTrue(all(check["solver"] == "appsi_highs" for check in checks))
        self.assertEqual(
            Counter({"optimal": 32, "infeasible": 3, "unbounded": 1}),
            Counter(check["termination_condition"] for check in checks),
        )
        optimal = [check for check in checks if check["termination_condition"] == "optimal"]
        self.assertTrue(all(check["maximum_violation"] == 0 for check in optimal))
        nonoptimal = [check for check in checks if check["termination_condition"] != "optimal"]
        self.assertTrue(all(check["maximum_violation"] is None for check in nonoptimal))
        self.assertEqual(0, self.results["summary"]["maximum_solver_violation"])

    def test_25_methods_statuses_proofs_and_missing_data_are_visible(self) -> None:
        self.assertEqual(17, len(self.results["summary"]["method_counts"]))
        self.assertEqual(3, self.results["summary"]["proof_only_count"])
        self.assertEqual([], self.results["underdetermined_exercises"])
        self.assertEqual(0, self.results["summary"]["underdetermined_count"])
        self.assertEqual(17, self.results["summary"]["verified_count"])
        self.assertEqual(
            ["11.7", "11.9", "11.14"],
            [
                exercise_id
                for exercise_id, exercise in self.results["exercises"].items()
                if exercise["status"] == "verified_proof"
            ],
        )

    def test_26_svg_inventory_hash_accessibility_and_scope(self) -> None:
        self.assertEqual({"ex11-16.svg"}, set(self.plots))
        generated_ids = {
            exercise_id
            for exercise_id, exercise in self.results["exercises"].items()
            if exercise["plot"]["status"] == "generated"
        }
        self.assertEqual(set(PLOT_IDS), generated_ids)
        namespace = "{http://www.w3.org/2000/svg}"
        payload = self.plots["ex11-16.svg"]
        root = ET.fromstring(payload)
        self.assertEqual("img", root.attrib["role"])
        self.assertEqual("id-ID", root.attrib["{http://www.w3.org/XML/1998/namespace}lang"])
        title = root.find(f"{namespace}title")
        description = root.find(f"{namespace}desc")
        metadata = root.find(f"{namespace}metadata")
        self.assertTrue(title is not None and (title.text or "").strip())
        self.assertTrue(description is not None and (description.text or "").strip())
        self.assertIsNotNone(metadata)
        machine = json.loads(metadata.text or "{}")
        self.assertEqual("id-ID", machine["language"])
        self.assertIn("alternative_text", machine)
        record = self.results["exercises"]["11.16"]["plot"]
        self.assertEqual(len(payload), record["bytes"])
        self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])

    def test_27_code_spdx_rights_runtime_and_no_proprietary_imports(self) -> None:
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
        requirements = (HERE.parent / "requirements.lock").read_text(encoding="utf-8")
        for requirement in (
            "pyomo==6.10.1",
            "highspy==1.15.1",
            "numpy==2.5.2",
            "--require-hashes",
        ):
            self.assertIn(requirement, requirements)

    def test_28_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(serialize_results(first_results), serialize_results(second_results))
        self.assertEqual(first_plots, second_plots)

    def test_29_committed_outputs_match_clean_replay(self) -> None:
        payload = serialize_results(self.results)
        self.assertEqual(
            [],
            compare_outputs(HERE / "results.json", HERE / "plots", payload, self.plots),
        )


if __name__ == "__main__":
    unittest.main()
