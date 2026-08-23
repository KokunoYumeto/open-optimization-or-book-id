"""Uji regresi laboratorium algoritme graf Bab 14.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from model import (
    all_shortest_weighted_paths,
    bellman_ford,
    connected_components,
    dijkstra,
    evaluate_all,
    exhaustive_mst,
    graph_nodes,
    kruskal,
    levenshtein,
    load_data,
    prim,
)
from plot_svg import generate_plot_payloads
from run_lab import assemble_results, compare_outputs, serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]


class GraphAlgorithmsLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data()
        cls.expected = json.loads((HERE / "expected-results.json").read_text(encoding="utf-8"))
        cls.results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
        cls.plots = {path.name: path.read_bytes() for path in sorted((HERE / "plots").glob("*.svg"))}

    def assert_subset(self, expected, actual, location="root") -> None:
        if isinstance(expected, dict):
            self.assertIsInstance(actual, dict, location)
            for key, value in expected.items():
                self.assertIn(key, actual, f"{location}.{key}")
                self.assert_subset(value, actual[key], f"{location}.{key}")
        elif isinstance(expected, list):
            self.assertEqual(len(expected), len(actual), location)
            for index, value in enumerate(expected):
                self.assert_subset(value, actual[index], f"{location}[{index}]")
        else:
            self.assertEqual(expected, actual, location)

    def certificate(self, exercise_id: str) -> dict:
        return self.results["exercises"][exercise_id]["certificate"]

    def test_01_schema_identity_authority_and_scope(self) -> None:
        self.assertEqual("1.0.0", self.data["schema_version"])
        self.assertEqual("o018.ch14.graph-algorithms", self.data["lab_id"])
        self.assertEqual(self.data["lab_id"], self.results["lab_id"])
        self.assertEqual(self.data["authority_commit"], self.results["authority_commit"])
        self.assertEqual(23, len(self.data["exercise_order"]))
        self.assertEqual(self.data["exercise_order"], self.results["exercise_order"])
        self.assertEqual(set(self.data["exercise_order"]), set(self.results["exercises"]))

    def test_02_all_four_frozen_source_witnesses_match_live_bytes(self) -> None:
        for record in self.data["provenance"]["source_files"]:
            path = LANE_ROOT / record["path"]
            payload = path.read_bytes()
            self.assertEqual(record["bytes"], len(payload), path)
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest(), path)

    def test_03_labels_and_layered_numbering_are_preserved(self) -> None:
        self.assertEqual(
            {
                "14.1": "ex:kruskal_exercise",
                "14.3": "ex:prim_exercise",
                "14.4": "ex:shortest-path",
                "14.skill.9": "ex:dijkstra-eurail",
                "14.skill.12": "ex:mst-sonet-ring",
                "14.skill.13": "ex:dijkstra-warmup-rail",
                "14.skill.14": "ex:kruskal-airfare",
                "14.concept.16": "ex:mst-greedy",
                "14.concept.17": "ex:dijkstra-nonneg",
            },
            {
                exercise_id: spec["book_label"]
                for exercise_id, spec in self.data["exercises"].items()
                if spec["book_label"] is not None
            },
        )

    def test_04_independent_expected_oracle_covers_every_exercise(self) -> None:
        self.assertEqual(set(self.data["exercise_order"]) | {"summary"}, set(self.expected))
        for exercise_id in self.data["exercise_order"]:
            self.assert_subset(self.expected[exercise_id], self.certificate(exercise_id), exercise_id)
        self.assert_subset(self.expected["summary"], self.results["summary"], "summary")

    def test_05_exercise_14_1_kruskal_and_exhaustive_certificate(self) -> None:
        certificate = self.certificate("14.1")
        self.assertEqual(71, certificate["total_weight"])
        self.assertEqual(71, certificate["exhaustive_crosscheck"]["minimum_weight"])
        self.assertEqual(1, certificate["exhaustive_crosscheck"]["minimum_tree_count"])

    def test_06_exercise_14_2_is_open_stdlib_replacement(self) -> None:
        certificate = self.certificate("14.2")
        self.assertTrue(certificate["stdlib_replacement"])
        self.assertEqual(5, len(certificate["tree_edges"]))
        self.assertEqual(71, certificate["total_weight"])

    def test_07_exercise_14_3_prim_matches_kruskal(self) -> None:
        certificate = self.certificate("14.3")
        self.assertTrue(certificate["kruskal_crosscheck"])
        self.assertEqual(71, certificate["total_weight"])
        self.assertEqual(["A", "B", 11], certificate["prim_order"][0])

    def test_08_exercise_14_4_dijkstra_path_distance_and_uniqueness(self) -> None:
        certificate = self.certificate("14.4")
        self.assertTrue(certificate["bellman_ford_crosscheck"])
        self.assertEqual(["A", "B", "D", "E", "G"], certificate["path"])
        self.assertEqual(13, certificate["distance"])
        self.assertEqual(1, certificate["shortest_path_count"])

    def test_09_image_dependent_skills_remain_explicit_rubrics(self) -> None:
        self.assertEqual("image_dependent", self.certificate("14.skill.1")["rubric_status"])
        self.assertEqual("image_dependent_multigraph", self.certificate("14.skill.2")["rubric_status"])
        self.assertEqual(14, self.certificate("14.skill.2")["handshake_sum"])

    def test_10_weighted_k5_constructions_preserve_all_ten_edges(self) -> None:
        for exercise_id in ("14.skill.3", "14.skill.4"):
            certificate = self.certificate(exercise_id)
            self.assertTrue(certificate["complete_graph_verified"])
            self.assertEqual((5, 10), (certificate["vertex_count"], certificate["edge_count"]))

    def test_11_degree_exercises_satisfy_handshake_identity(self) -> None:
        for exercise_id in ("14.skill.5", "14.skill.6"):
            certificate = self.certificate(exercise_id)
            self.assertTrue(certificate["handshake_verified"])
            self.assertEqual(2 * certificate["edge_count"], certificate["handshake_sum"])

    def test_12_connectivity_exercises_have_exact_components(self) -> None:
        self.assertEqual([1, 2, 1], self.certificate("14.skill.7")["component_counts"])
        self.assertEqual([3, 1, 2], self.certificate("14.skill.8")["component_counts"])

    def test_13_eurail_shortest_paths_and_minute_conversion(self) -> None:
        bern = self.certificate("14.skill.9")
        paris = self.certificate("14.skill.10")
        self.assertEqual((770, ["Bern", "Frankfurt", "München", "Berlin"]), (bern["distance_minutes"], bern["path"]))
        self.assertEqual((515, ["Paris", "Amsterdam", "Frankfurt", "München"]), (paris["distance_minutes"], paris["path"]))

    def test_14_dallas_mst_is_exhaustively_minimal(self) -> None:
        certificate = self.certificate("14.skill.11")
        self.assertEqual(140, certificate["total_weight"])
        self.assertEqual(140, certificate["exhaustive_crosscheck"]["minimum_weight"])

    def test_15_building_mst_preserves_decimal_scale(self) -> None:
        certificate = self.certificate("14.skill.12")
        self.assertEqual(174, certificate["total_weight_tenths"])
        self.assertEqual("17.4", certificate["total_thousand_dollars"])

    def test_16_virginia_route_and_settled_order(self) -> None:
        certificate = self.certificate("14.skill.13")
        self.assertEqual(405, certificate["distance_minutes"])
        self.assertEqual(["Washington", "Charlottesville", "Roanoke", "Bristol"], certificate["path"])
        self.assertEqual(["Bristol", 405], certificate["settled_order"][-1])

    def test_17_airfare_mst_records_cycle_rejection(self) -> None:
        certificate = self.certificate("14.skill.14")
        self.assertEqual(1097, certificate["total_weight"])
        self.assertEqual([["Cairo", "Moscow", 329]], certificate["rejected_before_completion"])

    def test_18_handshake_lemma_holds_for_every_simple_graph_through_five_nodes(self) -> None:
        for size in range(1, 6):
            nodes = [str(index) for index in range(size)]
            possible = list(itertools.combinations(nodes, 2))
            for mask in range(1 << len(possible)):
                degrees = {node: 0 for node in nodes}
                for index, (u, v) in enumerate(possible):
                    if mask & (1 << index):
                        degrees[u] += 1
                        degrees[v] += 1
                self.assertEqual(0, sum(value % 2 for value in degrees.values()) % 2)

    def test_19_kruskal_remains_valid_with_negative_edges(self) -> None:
        certificate = self.certificate("14.concept.16")
        self.assertTrue(certificate["negative_weights_allowed_for_mst"])
        self.assertEqual(-2, certificate["negative_example_minimum_weight"])
        self.assertEqual(-2, certificate["exhaustive_crosscheck"]["minimum_weight"])

    def test_20_negative_edge_counterexample_is_explicit(self) -> None:
        certificate = self.certificate("14.concept.17")
        self.assertEqual(2, certificate["finalize_once_dijkstra_wrong_distance"])
        self.assertEqual(1, certificate["bellman_ford_distance"])
        self.assertEqual(["A", "C", "B"], certificate["bellman_ford_path"])
        self.assertTrue(certificate["standard_dijkstra_rejects_negative_edges"])

    def test_21_social_graph_has_four_shortest_paths_of_length_three(self) -> None:
        certificate = self.certificate("14.exploration.18")
        self.assertEqual(3, certificate["distance"])
        self.assertEqual(4, len(certificate["shortest_paths"]))
        self.assertEqual(15, certificate["edge_count"])

    def test_22_levenshtein_graph_and_weighted_example(self) -> None:
        certificate = self.certificate("14.exploration.19")
        self.assertEqual(13, len(certificate["distance_one_candidates"]))
        self.assertNotIn("smoke", certificate["distance_one_candidates"])
        self.assertEqual({"cost": 2, "word": "smoke"}, certificate["insertion_example"])
        self.assertEqual(1, levenshtein("moke", "move"))
        self.assertEqual(1, levenshtein("moke", "smoke"))

    def test_23_learning_checkpoint_is_preserved_separately(self) -> None:
        checkpoint = self.results["learning_checkpoint"]
        self.assertEqual((5, 10, 4), (checkpoint["vertex_count"], checkpoint["edge_count"], checkpoint["degree_LA"]))
        self.assertTrue(checkpoint["connected"])

    def test_24_source_notes_are_visible_and_not_math_corrections(self) -> None:
        self.assertEqual(4, len(self.results["source_notes"]))
        self.assertEqual(0, self.results["summary"]["o018_math_correction_count"])
        self.assertEqual(
            ["NOTE-CH14-BERN-TIME", "NOTE-CH14-LOWRES-EXERCISES", "NOTE-CH14-PRIM-FLOAT", "NOTE-CH14-HARDCODED-REFS"],
            [item["id"] for item in self.results["source_notes"]],
        )

    def test_25_every_item_has_method_verified_status_and_no_unresolved(self) -> None:
        self.assertTrue(all(item["method"] for item in self.results["exercises"].values()))
        self.assertTrue(all(item["status"] == "verified" for item in self.results["exercises"].values()))
        self.assertEqual([], self.results["unresolved_exercises"])
        self.assertEqual(23, self.results["summary"]["verified_count"])

    def test_26_svg_inventory_accessibility_metadata_and_hashes(self) -> None:
        self.assertEqual({"ex14-01-mst.svg", "ex14-04-shortest.svg"}, set(self.plots))
        namespace = "{http://www.w3.org/2000/svg}"
        for filename, payload in self.plots.items():
            root = ET.fromstring(payload)
            self.assertEqual("img", root.attrib["role"])
            self.assertEqual("id-ID", root.attrib["{http://www.w3.org/XML/1998/namespace}lang"])
            self.assertTrue((root.find(f"{namespace}title").text or "").strip())
            self.assertTrue((root.find(f"{namespace}desc").text or "").strip())
            machine = json.loads(root.find(f"{namespace}metadata").text or "{}")
            self.assertEqual("id-ID", machine["language"])
            self.assertTrue(machine["alternative_text"])
            record = next(
                item["plot"]
                for item in self.results["exercises"].values()
                if item["plot"].get("path") == f"plots/{filename}"
            )
            self.assertEqual(len(payload), record["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])

    def test_27_plot_generation_is_limited_to_declared_exercises(self) -> None:
        payloads, records = generate_plot_payloads(self.data, evaluate_all(self.data))
        self.assertEqual(self.plots, payloads)
        self.assertEqual(2, sum(record["status"] == "generated" for record in records.values()))
        self.assertEqual(21, sum(record["status"] == "not_required" for record in records.values()))

    def test_28_code_spdx_and_no_network_or_proprietary_imports(self) -> None:
        code_files = ["model.py", "plot_svg.py", "run_lab.py", "test_models.py", "verify_receipt.py"]
        forbidden = re.compile(r"^\s*(?:from|import)\s+(?:networkx|gurobi|gurobipy|cplex|mosek|requests|urllib|socket)\b", re.MULTILINE)
        for filename in code_files:
            text = (HERE / filename).read_text(encoding="utf-8")
            self.assertIn("SPDX-License-Identifier: MIT", text)
            self.assertIsNone(forbidden.search(text), filename)

    def test_29_graph_algorithms_crosscheck_all_numeric_cases(self) -> None:
        cases = self.data["cases"]
        for case_name, start in (("in_chapter_shortest", "A"), ("eurail", "Bern"), ("virginia", "Washington")):
            dij = dijkstra(cases[case_name]["edges"], start)
            bf = bellman_ford(cases[case_name]["edges"], start)
            self.assertEqual(dij["distances"], bf["distances"], case_name)
        for case_name in ("in_chapter_mst", "dallas", "buildings", "airfare"):
            greedy = kruskal(cases[case_name]["edges"])
            exhaustive = exhaustive_mst(cases[case_name]["edges"])
            self.assertEqual(greedy["total_weight"], exhaustive["minimum_weight"], case_name)

    def test_30_prim_and_kruskal_agree_on_main_graph(self) -> None:
        edges = self.data["cases"]["in_chapter_mst"]["edges"]
        self.assertEqual(kruskal(edges)["total_weight"], prim(edges, "A")["total_weight"])

    def test_31_graph_helpers_preserve_isolated_nodes(self) -> None:
        self.assertEqual([["a", "b"], ["c"]], connected_components(["a", "b", "c"], [["a", "b"]]))
        self.assertEqual(["a", "b"], graph_nodes([["a", "b"]]))

    def test_32_generation_is_byte_deterministic_in_memory(self) -> None:
        first_results, first_plots = assemble_results(self.data)
        second_results, second_plots = assemble_results(self.data)
        self.assertEqual(serialize_results(first_results), serialize_results(second_results))
        self.assertEqual(first_plots, second_plots)

    def test_33_committed_outputs_match_clean_replay(self) -> None:
        results, plots = assemble_results(self.data)
        self.assertEqual(
            [],
            compare_outputs(HERE / "results.json", HERE / "plots", serialize_results(results), plots),
        )


if __name__ == "__main__":
    unittest.main()
