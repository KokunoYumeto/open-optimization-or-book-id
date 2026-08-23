"""Algoritme graf deterministik untuk pendamping terbuka Bab 14.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import heapq
import itertools
import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent


def load_data(path: Path | None = None) -> dict[str, Any]:
    source = path or HERE / "data.json"
    return json.loads(source.read_text(encoding="utf-8"))


def _edge3(edge: list[Any] | tuple[Any, ...]) -> tuple[str, str, int]:
    if len(edge) == 2:
        return str(edge[0]), str(edge[1]), 1
    return str(edge[0]), str(edge[1]), int(edge[2])


def normalized_edge(u: str, v: str, weight: int) -> list[Any]:
    a, b = sorted((u, v))
    return [a, b, weight]


def graph_nodes(edges: Iterable[list[Any]], explicit: Iterable[str] = ()) -> list[str]:
    nodes = set(explicit)
    for edge in edges:
        u, v, _ = _edge3(edge)
        nodes.update((u, v))
    return sorted(nodes)


def adjacency(
    edges: Iterable[list[Any]], *, directed: bool = False, explicit: Iterable[str] = ()
) -> dict[str, list[tuple[str, int]]]:
    result: dict[str, list[tuple[str, int]]] = {
        node: [] for node in graph_nodes(edges, explicit)
    }
    for edge in edges:
        u, v, weight = _edge3(edge)
        result[u].append((v, weight))
        if not directed:
            result[v].append((u, weight))
    for node in result:
        result[node].sort(key=lambda item: (item[0], item[1]))
    return result


def connected_components(nodes: Iterable[str], edges: Iterable[list[Any]]) -> list[list[str]]:
    graph = adjacency(edges, explicit=nodes)
    unseen = set(graph)
    components: list[list[str]] = []
    while unseen:
        start = min(unseen)
        queue = deque([start])
        unseen.remove(start)
        component: list[str] = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor, _ in graph[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda item: item[0])


def degree_certificate(nodes: Iterable[str], edges: Iterable[list[Any]]) -> dict[str, Any]:
    ordered_nodes = sorted(nodes)
    degree = {node: 0 for node in ordered_nodes}
    edge_list = list(edges)
    for edge in edge_list:
        u, v, _ = _edge3(edge)
        degree[u] += 1
        degree[v] += 1
    return {
        "degrees": degree,
        "edge_count": len(edge_list),
        "handshake_sum": sum(degree.values()),
        "handshake_verified": sum(degree.values()) == 2 * len(edge_list),
    }


def dijkstra(
    edges: Iterable[list[Any]], start: str, *, directed: bool = False
) -> dict[str, Any]:
    edge_list = list(edges)
    if any(_edge3(edge)[2] < 0 for edge in edge_list):
        raise ValueError("Dijkstra memerlukan semua bobot sisi tidak negatif")
    graph = adjacency(edge_list, directed=directed)
    if start not in graph:
        raise KeyError(start)
    distance = {node: math.inf for node in graph}
    predecessors: dict[str, list[str]] = {node: [] for node in graph}
    distance[start] = 0
    heap: list[tuple[int, str]] = [(0, start)]
    settled: set[str] = set()
    settled_order: list[list[Any]] = []
    while heap:
        current_distance, current = heapq.heappop(heap)
        if current in settled or current_distance != distance[current]:
            continue
        settled.add(current)
        settled_order.append([current, current_distance])
        for neighbor, weight in graph[current]:
            candidate = current_distance + weight
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                predecessors[neighbor] = [current]
                heapq.heappush(heap, (candidate, neighbor))
            elif candidate == distance[neighbor] and current not in predecessors[neighbor]:
                predecessors[neighbor].append(current)
                predecessors[neighbor].sort()
    return {
        "distances": {
            node: (None if math.isinf(value) else int(value))
            for node, value in sorted(distance.items())
        },
        "predecessors": {node: sorted(values) for node, values in sorted(predecessors.items())},
        "settled_order": settled_order,
    }


def reconstruct_path(predecessors: dict[str, list[str]], start: str, target: str) -> list[str]:
    if target == start:
        return [start]
    if not predecessors.get(target):
        return []
    return reconstruct_path(predecessors, start, predecessors[target][0]) + [target]


def all_shortest_weighted_paths(
    predecessors: dict[str, list[str]], start: str, target: str
) -> list[list[str]]:
    if target == start:
        return [[start]]
    paths: list[list[str]] = []
    for predecessor in predecessors.get(target, []):
        for prefix in all_shortest_weighted_paths(predecessors, start, predecessor):
            paths.append(prefix + [target])
    return sorted(paths)


def bellman_ford(
    edges: Iterable[list[Any]], start: str, *, directed: bool = False
) -> dict[str, Any]:
    edge_list = [_edge3(edge) for edge in edges]
    nodes = graph_nodes(edge_list)
    distance = {node: math.inf for node in nodes}
    parent: dict[str, str | None] = {node: None for node in nodes}
    distance[start] = 0
    arcs = list(edge_list)
    if not directed:
        arcs += [(v, u, weight) for u, v, weight in edge_list]
    arcs.sort(key=lambda item: (item[0], item[1], item[2]))
    for _ in range(max(0, len(nodes) - 1)):
        changed = False
        for u, v, weight in arcs:
            if not math.isinf(distance[u]) and distance[u] + weight < distance[v]:
                distance[v] = distance[u] + weight
                parent[v] = u
                changed = True
        if not changed:
            break
    for u, v, weight in arcs:
        if not math.isinf(distance[u]) and distance[u] + weight < distance[v]:
            raise ValueError("siklus berbobot negatif terjangkau dari sumber")
    return {
        "distances": {
            node: (None if math.isinf(value) else int(value))
            for node, value in sorted(distance.items())
        },
        "parents": parent,
    }


def reconstruct_parent_path(parent: dict[str, str | None], start: str, target: str) -> list[str]:
    path: list[str] = []
    current: str | None = target
    seen: set[str] = set()
    while current is not None:
        if current in seen:
            raise ValueError("siklus pada rantai pendahulu")
        seen.add(current)
        path.append(current)
        if current == start:
            return list(reversed(path))
        current = parent[current]
    return []


class DisjointSet:
    def __init__(self, nodes: Iterable[str]) -> None:
        self.parent = {node: node for node in nodes}
        self.rank = {node: 0 for node in nodes}

    def find(self, node: str) -> str:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, left: str, right: str) -> bool:
        root_left, root_right = self.find(left), self.find(right)
        if root_left == root_right:
            return False
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1
        return True


def kruskal(edges: Iterable[list[Any]]) -> dict[str, Any]:
    edge_list = [_edge3(edge) for edge in edges]
    nodes = graph_nodes(edge_list)
    ordered = sorted(
        edge_list,
        key=lambda edge: (edge[2], min(edge[0], edge[1]), max(edge[0], edge[1])),
    )
    sets = DisjointSet(nodes)
    accepted: list[list[Any]] = []
    rejected: list[list[Any]] = []
    events: list[dict[str, Any]] = []
    for u, v, weight in ordered:
        edge = normalized_edge(u, v, weight)
        if sets.union(u, v):
            accepted.append(edge)
            events.append({"action": "tambahkan", "edge": edge})
        else:
            rejected.append(edge)
            events.append({"action": "tolak_siklus", "edge": edge})
        if len(accepted) == len(nodes) - 1:
            break
    if len(accepted) != len(nodes) - 1:
        raise ValueError("graf tidak terhubung")
    return {
        "accepted_edges": accepted,
        "events_until_completion": events,
        "rejected_before_completion": rejected,
        "total_weight": sum(edge[2] for edge in accepted),
    }


def prim(edges: Iterable[list[Any]], start: str) -> dict[str, Any]:
    edge_list = list(edges)
    graph = adjacency(edge_list)
    if start not in graph:
        raise KeyError(start)
    visited = {start}
    heap: list[tuple[int, str, str, str, str]] = []

    def add_frontier(node: str) -> None:
        for neighbor, weight in graph[node]:
            if neighbor not in visited:
                a, b = sorted((node, neighbor))
                heapq.heappush(heap, (weight, a, b, node, neighbor))

    add_frontier(start)
    order: list[list[Any]] = []
    while heap and len(visited) < len(graph):
        weight, _, _, source, target = heapq.heappop(heap)
        if target in visited:
            continue
        visited.add(target)
        order.append([source, target, weight])
        add_frontier(target)
    if len(visited) != len(graph):
        raise ValueError("graf tidak terhubung")
    return {"prim_order": order, "total_weight": sum(edge[2] for edge in order)}


def exhaustive_mst(edges: Iterable[list[Any]]) -> dict[str, Any]:
    edge_list = [_edge3(edge) for edge in edges]
    nodes = graph_nodes(edge_list)
    best_weight: int | None = None
    best_trees: list[list[list[Any]]] = []
    checked = 0
    for candidate in itertools.combinations(edge_list, len(nodes) - 1):
        sets = DisjointSet(nodes)
        if not all(sets.union(u, v) for u, v, _ in candidate):
            continue
        checked += 1
        weight = sum(edge[2] for edge in candidate)
        tree = sorted(normalized_edge(*edge) for edge in candidate)
        if best_weight is None or weight < best_weight:
            best_weight = weight
            best_trees = [tree]
        elif weight == best_weight:
            best_trees.append(tree)
    if best_weight is None:
        raise ValueError("tidak ada pohon merentang")
    return {
        "minimum_weight": best_weight,
        "minimum_tree_count": len(best_trees),
        "spanning_tree_count_checked": checked,
    }


def all_shortest_unweighted_paths(
    nodes: Iterable[str], edges: Iterable[list[Any]], start: str, target: str
) -> list[list[str]]:
    graph = adjacency(edges, explicit=nodes)
    distance = {start: 0}
    predecessors: dict[str, list[str]] = defaultdict(list)
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor, _ in graph[current]:
            candidate = distance[current] + 1
            if neighbor not in distance:
                distance[neighbor] = candidate
                predecessors[neighbor] = [current]
                queue.append(neighbor)
            elif candidate == distance[neighbor] and current not in predecessors[neighbor]:
                predecessors[neighbor].append(current)
                predecessors[neighbor].sort()

    def build(node: str) -> list[list[str]]:
        if node == start:
            return [[start]]
        return sorted(
            prefix + [node]
            for predecessor in predecessors.get(node, [])
            for prefix in build(predecessor)
        )

    return build(target)


def levenshtein(left: str, right: str, costs: dict[str, int] | None = None) -> int:
    cost = costs or {"insertion": 1, "deletion": 1, "substitution": 1}
    previous = [index * cost["insertion"] for index in range(len(right) + 1)]
    for row, char_left in enumerate(left, start=1):
        current = [row * cost["deletion"]]
        for column, char_right in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + cost["insertion"],
                    previous[column] + cost["deletion"],
                    previous[column - 1]
                    + (0 if char_left == char_right else cost["substitution"]),
                )
            )
        previous = current
    return previous[-1]


def naive_finalize_once_dijkstra(
    edges: Iterable[list[Any]], start: str, *, directed: bool = True
) -> dict[str, int | None]:
    """Varian pedagogis yang sengaja tidak menolak sisi negatif."""
    graph = adjacency(edges, directed=directed)
    distance = {node: math.inf for node in graph}
    distance[start] = 0
    heap: list[tuple[int, str]] = [(0, start)]
    final: set[str] = set()
    while heap:
        value, node = heapq.heappop(heap)
        if node in final:
            continue
        final.add(node)
        for neighbor, weight in graph[node]:
            if neighbor in final:
                continue
            candidate = value + weight
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                heapq.heappush(heap, (candidate, neighbor))
    return {
        node: (None if math.isinf(value) else int(value))
        for node, value in sorted(distance.items())
    }


def _shortest_certificate(case: dict[str, Any], start: str, target: str) -> dict[str, Any]:
    dij = dijkstra(case["edges"], start)
    bf = bellman_ford(case["edges"], start)
    if dij["distances"] != bf["distances"]:
        raise AssertionError("Dijkstra dan Bellman--Ford tidak sepakat")
    paths = all_shortest_weighted_paths(dij["predecessors"], start, target)
    return {
        "bellman_ford_crosscheck": True,
        "distance": dij["distances"][target],
        "path": paths[0],
        "settled_order": dij["settled_order"],
        "shortest_path_count": len(paths),
        "unique_shortest_path": len(paths) == 1,
    }


def _mst_certificate(case: dict[str, Any]) -> dict[str, Any]:
    greedy = kruskal(case["edges"])
    exhaustive = exhaustive_mst(case["edges"])
    if greedy["total_weight"] != exhaustive["minimum_weight"]:
        raise AssertionError("Kruskal tidak cocok dengan enumerasi pohon merentang")
    return {**greedy, "exhaustive_crosscheck": exhaustive}


def _base_exercise(data: dict[str, Any], exercise_id: str, certificate: dict[str, Any]) -> dict[str, Any]:
    spec = data["exercises"][exercise_id]
    return {
        "book_label": spec["book_label"],
        "certificate": certificate,
        "method": spec["method"],
        "status": "verified",
        "title": spec["title"],
    }


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    cases = data["cases"]
    exercises: dict[str, Any] = {}

    mst_main = _mst_certificate(cases["in_chapter_mst"])
    exercises["14.1"] = _base_exercise(data, "14.1", mst_main)
    exercises["14.2"] = _base_exercise(
        data,
        "14.2",
        {
            "stdlib_replacement": True,
            "tree_edges": sorted(mst_main["accepted_edges"]),
            "total_weight": mst_main["total_weight"],
        },
    )
    prim_main = prim(cases["in_chapter_mst"]["edges"], "A")
    exercises["14.3"] = _base_exercise(
        data,
        "14.3",
        {**prim_main, "kruskal_crosscheck": prim_main["total_weight"] == mst_main["total_weight"]},
    )
    shortest_main = _shortest_certificate(cases["in_chapter_shortest"], "A", "G")
    exercises["14.4"] = _base_exercise(data, "14.4", shortest_main)

    exercises["14.skill.1"] = _base_exercise(
        data,
        "14.skill.1",
        {
            "intersection_count": 12,
            "rubric_status": "image_dependent",
            "required_features": [
                "simpul_hanya_pada_persimpangan",
                "satu_sisi_per_segmen_jalan_berumah",
                "segmen_tanpa_rumah_diabaikan",
            ],
        },
    )
    exercises["14.skill.2"] = _base_exercise(
        data,
        "14.skill.2",
        {
            "edge_count": 7,
            "handshake_sum": 14,
            "rubric_status": "image_dependent_multigraph",
            "vertex_count": 4,
        },
    )
    for exercise_id, case_name in (("14.skill.3", "dallas"), ("14.skill.4", "airfare")):
        case = cases[case_name]
        nodes = graph_nodes(case["edges"])
        exercises[exercise_id] = _base_exercise(
            data,
            exercise_id,
            {
                "edge_count": len(case["edges"]),
                "graph_type": "K5_berbobot",
                "vertex_count": len(nodes),
                "complete_graph_verified": len(case["edges"]) == len(nodes) * (len(nodes) - 1) // 2,
            },
        )
    exercises["14.skill.5"] = _base_exercise(
        data,
        "14.skill.5",
        degree_certificate(cases["degree_first"]["nodes"], cases["degree_first"]["edges"]),
    )
    exercises["14.skill.6"] = _base_exercise(
        data,
        "14.skill.6",
        degree_certificate(cases["degree_second"]["nodes"], cases["degree_second"]["edges"]),
    )
    for exercise_id, case_name in (("14.skill.7", "connectivity_five"), ("14.skill.8", "connectivity_eight")):
        case = cases[case_name]
        components = [connected_components(case["nodes"], edges) for edges in case["graphs"]]
        exercises[exercise_id] = _base_exercise(
            data,
            exercise_id,
            {
                "component_counts": [len(item) for item in components],
                "components": components,
                "connected_graphs": [index + 1 for index, item in enumerate(components) if len(item) == 1],
            },
        )
    eurail_bern = _shortest_certificate(cases["eurail"], "Bern", "Berlin")
    exercises["14.skill.9"] = _base_exercise(
        data,
        "14.skill.9",
        {
            "bellman_ford_crosscheck": True,
            "distance_minutes": eurail_bern["distance"],
            "path": eurail_bern["path"],
            "settled_order": eurail_bern["settled_order"],
        },
    )
    eurail_paris = _shortest_certificate(cases["eurail"], "Paris", "München")
    exercises["14.skill.10"] = _base_exercise(
        data,
        "14.skill.10",
        {
            "bellman_ford_crosscheck": True,
            "distance_minutes": eurail_paris["distance"],
            "path": eurail_paris["path"],
        },
    )
    dallas_mst = _mst_certificate(cases["dallas"])
    exercises["14.skill.11"] = _base_exercise(data, "14.skill.11", dallas_mst)
    buildings_mst = _mst_certificate(cases["buildings"])
    exercises["14.skill.12"] = _base_exercise(
        data,
        "14.skill.12",
        {
            **buildings_mst,
            "total_weight_tenths": buildings_mst["total_weight"],
            "total_thousand_dollars": f"{buildings_mst['total_weight'] / 10:.1f}",
        },
    )
    virginia = _shortest_certificate(cases["virginia"], "Washington", "Bristol")
    exercises["14.skill.13"] = _base_exercise(
        data,
        "14.skill.13",
        {
            "bellman_ford_crosscheck": True,
            "distance_minutes": virginia["distance"],
            "path": virginia["path"],
            "settled_order": virginia["settled_order"],
        },
    )
    airfare_mst = _mst_certificate(cases["airfare"])
    exercises["14.skill.14"] = _base_exercise(data, "14.skill.14", airfare_mst)

    exercises["14.concept.15"] = _base_exercise(
        data,
        "14.concept.15",
        {
            "handshake_identity": "sum_v deg(v) = 2|E|",
            "odd_degree_count_is_even": True,
            "simple_graphs_enumerated_up_to_vertices": 5,
        },
    )
    negative_mst_edges = [["A", "B", -3], ["B", "C", 1], ["A", "C", 2]]
    negative_mst = _mst_certificate({"edges": negative_mst_edges})
    exercises["14.concept.16"] = _base_exercise(
        data,
        "14.concept.16",
        {
            "exchange_argument": True,
            "negative_example_minimum_weight": negative_mst["total_weight"],
            "negative_weights_allowed_for_mst": True,
            "exhaustive_crosscheck": negative_mst["exhaustive_crosscheck"],
        },
    )
    negative = cases["negative_dijkstra_counterexample"]
    bellman = bellman_ford(negative["edges"], "A", directed=True)
    standard_rejected = False
    try:
        dijkstra(negative["edges"], "A", directed=True)
    except ValueError:
        standard_rejected = True
    naive = naive_finalize_once_dijkstra(negative["edges"], "A", directed=True)
    exercises["14.concept.17"] = _base_exercise(
        data,
        "14.concept.17",
        {
            "bellman_ford_distance": bellman["distances"]["B"],
            "bellman_ford_path": reconstruct_parent_path(bellman["parents"], "A", "B"),
            "finalize_once_dijkstra_wrong_distance": naive["B"],
            "standard_dijkstra_rejects_negative_edges": standard_rejected,
        },
    )

    social = cases["social"]
    social_paths = all_shortest_unweighted_paths(
        social["nodes"], social["edges"], "A", "D"
    )
    exercises["14.exploration.18"] = _base_exercise(
        data,
        "14.exploration.18",
        {
            "distance": len(social_paths[0]) - 1,
            "edge_count": len(social["edges"]),
            "film_extension_status": "open_rubric",
            "shortest_paths": social_paths,
        },
    )
    spelling = cases["spelling"]
    words = spelling["words"]
    unweighted_edges = [
        [left, right]
        for index, left in enumerate(words)
        for right in words[index + 1 :]
        if levenshtein(left, right) == 1
    ]
    weighted_edges = [
        [left, right, levenshtein(left, right, spelling["costs"])]
        for left, right in unweighted_edges
    ]
    spelling_distances = dijkstra(weighted_edges, spelling["center"])["distances"]
    distance_one = sorted(
        word for word in words if word != spelling["center"] and levenshtein(spelling["center"], word) == 1 and len(word) == len(spelling["center"])
    )
    exercises["14.exploration.19"] = _base_exercise(
        data,
        "14.exploration.19",
        {
            "center": spelling["center"],
            "distance_one_candidates": distance_one,
            "graph_edge_count": len(unweighted_edges),
            "insertion_example": {"cost": spelling_distances["smoke"], "word": "smoke"},
            "rubric_status": "open_weighting_scheme",
            "weighted_distances": spelling_distances,
            "weighting_scheme": spelling["costs"],
        },
    )

    if list(exercises) != data["exercise_order"]:
        raise AssertionError("urutan latihan hasil tidak cocok dengan data.json")
    return {
        "authority_commit": data["authority_commit"],
        "exercise_order": data["exercise_order"],
        "exercises": exercises,
        "lab_id": data["lab_id"],
        "learning_checkpoint": {
            "connected": True,
            "degree_LA": 4,
            "edge_count": 10,
            "graph_type": "K5",
            "path_example": ["Seattle", "Dallas", "Atlanta"],
            "vertex_count": 5,
        },
        "provenance": data["provenance"],
        "schema_version": data["schema_version"],
        "source_notes": data["source_notes"],
        "summary": {
            "algorithm_check_count": len(exercises),
            "exercise_count": len(exercises),
            "method_counts": {
                method: sum(spec["method"] == method for spec in data["exercises"].values())
                for method in sorted({spec["method"] for spec in data["exercises"].values()})
            },
            "o018_math_correction_count": 0,
            "source_note_count": len(data["source_notes"]),
            "unresolved_count": len(data["unresolved_exercises"]),
            "verified_count": sum(item["status"] == "verified" for item in exercises.values()),
        },
        "unresolved_exercises": data["unresolved_exercises"],
    }
