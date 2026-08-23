"""Uji regresi laboratorium pemrograman bilangan bulat Bab 15.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

from model import evaluate_all, load_data
from plot_svg import generate_plot_payloads
from run_lab import assemble_results, compare_outputs, serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]


class IntegerProgrammingLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(HERE / "data.json")
        cls.expected = json.loads(
            (HERE / "expected-results.json").read_text(encoding="utf-8")
        )
        cls.results = json.loads(
            (HERE / "results.json").read_text(encoding="utf-8")
        )
        cls.generated, cls.plots = assemble_results(cls.data)
        cls.plot_payloads, cls.plot_records = generate_plot_payloads(cls.data)

    def _answer_without_checks(self, exercise_id: str) -> dict:
        answer = dict(self.results["exercises"][exercise_id]["answer"])
        answer.pop("solver_checks")
        return answer

    def test_01_schema_lab_and_authority_identity(self) -> None:
        self.assertEqual("1.0.0", self.data["schema_version"])
        self.assertEqual("o018.ch15.integer_programming", self.data["lab_id"])
        self.assertEqual(
            "1745df89b608899f66983834fa4ec8c8910d18ff",
            self.data["authority_commit"],
        )

    def test_02_complete_stable_exercise_order(self) -> None:
        expected = [f"15.{number}" for number in range(1, 17)]
        self.assertEqual(expected, self.data["exercise_order"])
        self.assertEqual(set(expected), set(self.results["exercises"]))
        self.assertEqual(
            expected, self.results["manual_alignment"]["book_primary_ids"]
        )

    def test_03_all_book_labels_are_present_in_live_chapter(self) -> None:
        chapter = (
            LANE_ROOT
            / self.data["provenance"]["source_files"][2]["path"]
        ).read_text(encoding="utf-8")
        for spec in self.data["exercises"].values():
            self.assertIn(f"\\label{{{spec['book_label']}}}", chapter)

    def test_04_all_manual_entries_are_present_and_aligned(self) -> None:
        manual = (
            LANE_ROOT
            / self.data["provenance"]["source_files"][3]["path"]
        ).read_text(encoding="utf-8")
        ids = re.findall(r"\\exsol\{(15\.\d+)\}", manual)
        expected = [f"15.{number}" for number in range(1, 17)]
        self.assertEqual(expected, ids)
        self.assertEqual(
            expected,
            [
                self.data["exercises"][exercise_id]["manual_mapping"]["manual_id"]
                for exercise_id in self.data["exercise_order"]
            ],
        )

    def test_05_frozen_source_witnesses_match_live_bytes_and_hashes(self) -> None:
        for record in self.data["provenance"]["source_files"]:
            path = LANE_ROOT / record["path"]
            payload = path.read_bytes()
            self.assertEqual(record["bytes"], len(payload), path)
            self.assertEqual(
                record["sha256"], hashlib.sha256(payload).hexdigest(), path
            )

    def test_06_rights_and_source_defects_are_explicit(self) -> None:
        self.assertEqual("CC-BY-SA-4.0", self.data["content_license"])
        self.assertEqual("MIT", self.data["code_license"])
        self.assertEqual(
            ["DEF-CH15-FIRE-PLACEMENTS", "DEF-CH15-EITHER-OR-SEMANTICS"],
            [item["id"] for item in self.data["source_defects"]],
        )

    def test_07_no_unresolved_exercises(self) -> None:
        self.assertEqual([], self.data["unresolved_exercises"])
        self.assertEqual([], self.results["unresolved_exercises"])

    def test_08_exercise_15_1_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.1"], self._answer_without_checks("15.1"))

    def test_09_exercise_15_2_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.2"], self._answer_without_checks("15.2"))

    def test_10_exercise_15_3_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.3"], self._answer_without_checks("15.3"))

    def test_11_exercise_15_4_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.4"], self._answer_without_checks("15.4"))

    def test_12_exercise_15_5_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.5"], self._answer_without_checks("15.5"))

    def test_13_exercise_15_6_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.6"], self._answer_without_checks("15.6"))

    def test_14_exercise_15_7_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.7"], self._answer_without_checks("15.7"))

    def test_15_exercise_15_8_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.8"], self._answer_without_checks("15.8"))

    def test_16_exercise_15_9_matches_independent_oracle(self) -> None:
        self.assertEqual(self.expected["15.9"], self._answer_without_checks("15.9"))

    def test_17_exercise_15_10_matches_independent_oracle(self) -> None:
        self.assertEqual(
            self.expected["15.10"], self._answer_without_checks("15.10")
        )

    def test_18_exercise_15_11_matches_independent_oracle(self) -> None:
        self.assertEqual(
            self.expected["15.11"], self._answer_without_checks("15.11")
        )

    def test_19_exercise_15_12_matches_independent_oracle(self) -> None:
        self.assertEqual(
            self.expected["15.12"], self._answer_without_checks("15.12")
        )

    def test_20_exercise_15_13_matches_independent_oracle(self) -> None:
        self.assertEqual(
            self.expected["15.13"], self._answer_without_checks("15.13")
        )

    def test_21_exercise_15_14_matches_independent_oracle(self) -> None:
        self.assertEqual(
            self.expected["15.14"], self._answer_without_checks("15.14")
        )

    def test_22_exercise_15_15_matches_independent_oracle(self) -> None:
        self.assertEqual(
            self.expected["15.15"], self._answer_without_checks("15.15")
        )

    def test_23_exercise_15_16_matches_independent_oracle(self) -> None:
        self.assertEqual(
            self.expected["15.16"], self._answer_without_checks("15.16")
        )

    def test_24_summary_matches_oracle_and_solver_contract(self) -> None:
        summary = self.results["summary"]
        for key, value in self.expected["summary"].items():
            self.assertEqual(value, summary[key], key)
        self.assertEqual({"optimal": 20}, summary["solver_termination_counts"])
        self.assertEqual(0, summary["maximum_solver_violation"])

    def test_25_solver_ledger_is_complete_ordered_and_deduplicated(self) -> None:
        ledger = self.results["solver_ledger"]
        self.assertEqual(list(range(1, 21)), [item["call"] for item in ledger])
        self.assertEqual(20, len({item["tag"] for item in ledger}))
        self.assertTrue(
            all(item["termination_condition"] == "optimal" for item in ledger)
        )
        self.assertTrue(all(item["maximum_violation"] == 0 for item in ledger))
        nested = [
            item
            for exercise_id in self.data["exercise_order"]
            for item in self.results["exercises"][exercise_id]["answer"][
                "solver_checks"
            ]
        ]
        self.assertEqual(ledger, nested)

    def test_26_manual_alignment_statuses_are_not_silently_normalized(self) -> None:
        self.assertEqual(
            {"aligned": 15, "aligned_with_qaflag": 1},
            self.results["manual_alignment"]["manual_status_counts"],
        )
        self.assertEqual(
            "aligned_with_qaflag",
            self.results["exercises"]["15.10"]["manual_mapping"]["status"],
        )

    def test_27_plots_are_exactly_declared_and_accessible(self) -> None:
        self.assertEqual({"ex15-09.svg", "ex15-16.svg"}, set(self.plot_payloads))
        for filename, payload in self.plot_payloads.items():
            text = payload.decode("utf-8")
            self.assertIn('role="img"', text, filename)
            self.assertIn('xml:lang="id-ID"', text, filename)
            self.assertIn("<title", text, filename)
            self.assertIn("<desc", text, filename)
            self.assertIn("<metadata>", text, filename)
        self.assertEqual(
            2,
            sum(
                record["status"] == "generated"
                for record in self.plot_records.values()
            ),
        )
        self.assertEqual(
            14,
            sum(
                record["status"] == "not_required"
                for record in self.plot_records.values()
            ),
        )

    def test_28_plot_records_match_committed_bytes(self) -> None:
        for exercise in self.results["exercises"].values():
            record = exercise["plot"]
            if record["status"] != "generated":
                continue
            payload = (HERE / record["path"]).read_bytes()
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())

    def test_29_code_spdx_and_no_proprietary_or_network_imports(self) -> None:
        code_files = [
            "model.py",
            "plot_svg.py",
            "run_lab.py",
            "test_models.py",
            "verify_receipt.py",
        ]
        forbidden_import = re.compile(
            r"^\s*(?:from|import)\s+(?:gurobi|gurobipy|cplex|mosek|pulp|"
            r"requests|urllib|socket)\b",
            re.MULTILINE,
        )
        for filename in code_files:
            path = HERE / filename
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("SPDX-License-Identifier: MIT", text)
            self.assertIsNone(forbidden_import.search(text), filename)

    def test_30_frozen_runtime_lock_is_visible(self) -> None:
        requirements = (HERE.parent / "requirements.lock").read_text(encoding="utf-8")
        for requirement in (
            "pyomo==6.10.1",
            "highspy==1.15.1",
            "numpy==2.5.2",
            "--require-hashes",
        ):
            self.assertIn(requirement, requirements)

    def test_31_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(
            serialize_results(first_results), serialize_results(second_results)
        )
        self.assertEqual(first_plots, second_plots)

    def test_32_committed_outputs_match_clean_replay(self) -> None:
        payload = serialize_results(self.generated)
        self.assertEqual(
            [],
            compare_outputs(
                HERE / "results.json", HERE / "plots", payload, self.plots
            ),
        )


if __name__ == "__main__":
    unittest.main()
