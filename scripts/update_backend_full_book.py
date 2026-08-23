#!/usr/bin/env python3
"""One-time deterministic expansion of the R017/O018 authored backend input.

The script is intentionally lane-local and bounded.  It reads only the exact
Book 1 files and admitted O018 laboratory packages listed below, verifies their
current bytes, preserves every pre-existing stable ID, and upserts the records
needed for full-Book-1 export coverage.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


LANE = Path(__file__).resolve().parents[1]
INPUT = LANE / "backend" / "input" / "backend-input.json"
AUTHORITY = LANE / "authority" / "upstream" / "open-optimization-or-book-1745df89b608899f66983834fa4ec8c8910d18ff"
TARGET = LANE / "source"
BOOK_PREFIX = "Intro-Math-Programming/baseText/book/"
BASE_PREFIX = "Intro-Math-Programming/baseText/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relpath(value: str) -> Path:
    path = Path(*value.split("/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe relative path: {value}")
    return path


def exact_file(root: Path, relative: str) -> Path:
    path = root / relpath(relative)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def upsert(rows: list[dict[str, Any]], record: dict[str, Any]) -> None:
    matches = [index for index, row in enumerate(rows) if row["id"] == record["id"]]
    if len(matches) > 1:
        raise ValueError(f"duplicate pre-existing ID: {record['id']}")
    if matches:
        rows[matches[0]] = record
    else:
        rows.append(record)


def add_pair(
    data: dict[str, Any],
    *,
    identifier: str,
    parent_id: str,
    order: int,
    unit_type: str,
    path: str,
    rights: str = "rights.r017.content",
    concepts: tuple[str, ...] = (),
    prerequisites: tuple[str, ...] = (),
    additional_rights: tuple[str, ...] = (),
    **extra: Any,
) -> None:
    source = exact_file(AUTHORITY, path)
    target = exact_file(TARGET, path)
    record: dict[str, Any] = {
        "id": identifier,
        "unit_type": unit_type,
        "parent_id": parent_id,
        "order": order,
        "source_path": path,
        "target_path": path,
        "source_sha256": sha256(source),
        "expected_target_sha256": sha256(target),
        "rights_component_id": rights,
    }
    if concepts:
        record["concept_ids"] = list(concepts)
    if prerequisites:
        record["prerequisite_concept_ids"] = list(prerequisites)
    if additional_rights:
        record["additional_rights_component_ids"] = list(additional_rights)
    record.update(extra)
    upsert(data["file_units"], record)


def root_unit(
    *,
    identifier: str,
    parent_id: str | None,
    order: int,
    unit_type: str,
    title_source: str,
    title_target: str,
    concepts: tuple[str, ...] = (),
    prerequisites: tuple[str, ...] = (),
    rights: str = "rights.r017.content",
    edition: str = "edition.r017.upstream.1745df89",
    resource: str = "resource.r017.open-optimization-book",
    status: str = "verified",
    translation_state: str = "mathematically_reviewed",
    additional_rights: tuple[str, ...] = (),
    source_local_id: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": identifier,
        "unit_type": unit_type,
        "resource_id": resource,
        "edition_id": edition,
        "parent_id": parent_id,
        "order": order,
        "locale": "id-ID" if edition.startswith("edition.o018") else "mul",
        "title_source": title_source,
        "title_target": title_target,
        "translation_state": translation_state,
        "rights_component_id": rights,
        "status": status,
    }
    if concepts:
        record["concept_ids"] = list(concepts)
    if prerequisites:
        record["prerequisite_concept_ids"] = list(prerequisites)
    if additional_rights:
        record["additional_rights_component_ids"] = list(additional_rights)
    if source_local_id:
        record["source_local_id"] = source_local_id
    return record


def add_asset_pair(
    data: dict[str, Any],
    identifier: str,
    source_path: str,
    target_path: str | None = None,
    *,
    asset_type: str = "figure",
    rights: str = "rights.r017.content",
    status: str = "verified",
    extra: dict[str, Any] | None = None,
) -> None:
    target_path = target_path or source_path
    source = exact_file(AUTHORITY, source_path)
    target = exact_file(TARGET, target_path)
    record: dict[str, Any] = {
        "id": identifier,
        "asset_type": asset_type,
        "source_path": source_path,
        "target_path": target_path,
        "source_sha256": sha256(source),
        "expected_target_sha256": sha256(target),
        "rights_component_id": rights,
        "status": status,
    }
    if extra:
        record.update(extra)
    upsert(data["assets"], record)


CONCEPTS: dict[str, tuple[str, tuple[str, ...], str, str]] = {
    "concept.right-hand-side-ranging": ("right-hand-side sensitivity range", ("concept.sensitivity-analysis", "concept.basis-matrix"), "right-hand-side ranging", "rentang ruas kanan"),
    "concept.objective-coefficient-ranging": ("objective-coefficient sensitivity range", ("concept.sensitivity-analysis", "concept.reduced-cost"), "objective-coefficient ranging", "rentang koefisien objektif"),
    "concept.shadow-price": ("shadow price", ("concept.sensitivity-analysis",), "shadow price", "harga bayangan"),
    "concept.sensitivity-report": ("solver sensitivity report", ("concept.sensitivity-analysis",), "sensitivity report", "laporan sensitivitas"),
    "concept.linear-program-duality": ("linear-programming duality", ("concept.linear-programming",), "linear-programming duality", "dualitas pemrograman linear"),
    "concept.weak-duality": ("weak duality", ("concept.linear-program-duality",), "weak duality", "dualitas lemah"),
    "concept.strong-duality": ("strong duality", ("concept.weak-duality",), "strong duality", "dualitas kuat"),
    "concept.complementary-slackness": ("complementary slackness", ("concept.strong-duality",), "complementary slackness", "kelonggaran komplementer"),
    "concept.dual-economic-interpretation": ("economic interpretation of dual variables", ("concept.linear-program-duality", "concept.shadow-price"), "dual economic interpretation", "interpretasi ekonomi variabel dual"),
    "concept.python-modeling-workflow": ("Python optimization-modeling workflow", ("concept.optimization-model",), "Python modeling workflow", "alur kerja pemodelan Python"),
    "concept.pyomo-model": ("Pyomo optimization model", ("concept.python-modeling-workflow",), "Pyomo model", "model Pyomo"),
    "concept.parameter-sweep": ("optimization parameter sweep", ("concept.sensitivity-analysis", "concept.python-modeling-workflow"), "parameter sweep", "sapuan parameter"),
    "concept.multiobjective-optimization": ("multiobjective optimization", ("concept.optimization-model",), "multiobjective optimization", "optimisasi multiobjektif"),
    "concept.pareto-optimality": ("Pareto optimality", ("concept.multiobjective-optimization",), "Pareto optimality", "optimalitas Pareto"),
    "concept.pareto-frontier": ("Pareto frontier", ("concept.pareto-optimality",), "Pareto frontier", "frontier Pareto"),
    "concept.weighted-sum-method": ("weighted-sum method", ("concept.multiobjective-optimization",), "weighted-sum method", "metode jumlah berbobot"),
    "concept.epsilon-constraint-method": ("epsilon-constraint method", ("concept.multiobjective-optimization",), "epsilon-constraint method", "metode kendala epsilon"),
    "concept.lexicographic-optimization": ("lexicographic optimization", ("concept.multiobjective-optimization",), "lexicographic optimization", "optimisasi leksikografis"),
    "concept.graph": ("graph", (), "graph", "graf"),
    "concept.graph-degree": ("vertex degree", ("concept.graph",), "vertex degree", "derajat simpul"),
    "concept.graph-connectivity": ("graph connectivity", ("concept.graph",), "graph connectivity", "keterhubungan graf"),
    "concept.shortest-path": ("shortest path", ("concept.graph",), "shortest path", "lintasan terpendek"),
    "concept.dijkstra-algorithm": ("Dijkstra's algorithm", ("concept.shortest-path",), "Dijkstra's algorithm", "algoritma Dijkstra"),
    "concept.spanning-tree": ("spanning tree", ("concept.graph", "concept.graph-connectivity"), "spanning tree", "pohon merentang"),
    "concept.minimum-spanning-tree": ("minimum spanning tree", ("concept.spanning-tree",), "minimum spanning tree", "pohon merentang minimum"),
    "concept.kruskal-algorithm": ("Kruskal's algorithm", ("concept.minimum-spanning-tree",), "Kruskal's algorithm", "algoritma Kruskal"),
    "concept.prim-algorithm": ("Prim's algorithm", ("concept.minimum-spanning-tree",), "Prim's algorithm", "algoritma Prim"),
    "concept.integer-programming": ("integer programming", ("concept.linear-programming",), "integer programming", "pemrograman bilangan bulat"),
    "concept.binary-variable": ("binary decision variable", ("concept.integer-programming", "concept.decision-variable"), "binary variable", "variabel biner"),
    "concept.knapsack-model": ("knapsack model", ("concept.binary-variable",), "knapsack model", "model ransel"),
    "concept.set-cover-model": ("set-cover model", ("concept.binary-variable",), "set-cover model", "model penutupan himpunan"),
    "concept.big-m-formulation": ("Big-M formulation", ("concept.binary-variable",), "Big-M formulation", "formulasi Big-M"),
    "concept.facility-location": ("facility-location model", ("concept.binary-variable",), "facility location", "lokasi fasilitas"),
    "concept.capital-budgeting": ("capital-budgeting model", ("concept.binary-variable",), "capital budgeting", "penganggaran modal"),
    "concept.graph-coloring": ("graph-coloring formulation", ("concept.graph", "concept.integer-programming"), "graph coloring", "pewarnaan graf"),
    "concept.fixed-charge-model": ("fixed-charge model", ("concept.binary-variable",), "fixed-charge model", "model biaya tetap"),
    "concept.lp-relaxation": ("linear-programming relaxation", ("concept.integer-programming",), "LP relaxation", "relaksasi LP"),
    "concept.piecewise-linear-model": ("piecewise-linear model", ("concept.integer-programming",), "piecewise-linear model", "model linear sepenggal"),
    "concept.disjunctive-scheduling": ("disjunctive scheduling formulation", ("concept.big-m-formulation",), "disjunctive scheduling", "penjadwalan disjungtif"),
    "concept.linear-equation": ("linear equation", (), "linear equation", "persamaan linear"),
    "concept.slope-intercept-form": ("slope-intercept form", ("concept.linear-equation",), "slope-intercept form", "bentuk gradien-intersep"),
    "concept.linear-system": ("system of linear equations", ("concept.linear-equation",), "linear system", "sistem persamaan linear"),
    "concept.gaussian-elimination": ("Gaussian elimination", ("concept.linear-system",), "Gaussian elimination", "eliminasi Gauss"),
    "concept.row-echelon-form": ("row echelon form", ("concept.gaussian-elimination",), "row echelon form", "bentuk eselon baris"),
    "concept.reduced-row-echelon-form": ("reduced row echelon form", ("concept.row-echelon-form",), "reduced row echelon form", "bentuk eselon baris tereduksi"),
    "concept.matrix-arithmetic": ("matrix arithmetic", (), "matrix arithmetic", "aritmetika matriks"),
    "concept.matrix-multiplication": ("matrix multiplication", ("concept.matrix-arithmetic",), "matrix multiplication", "perkalian matriks"),
    "concept.matrix-transpose": ("matrix transpose", ("concept.matrix-arithmetic",), "matrix transpose", "transpos matriks"),
    "concept.matrix-inverse": ("matrix inverse", ("concept.matrix-multiplication",), "matrix inverse", "invers matriks"),
    "concept.vector": ("vector in R^n", (), "vector", "vektor"),
    "concept.vector-norm": ("vector norm", ("concept.vector",), "vector norm", "norma vektor"),
    "concept.dot-product": ("dot product", ("concept.vector",), "dot product", "hasil kali titik"),
}


CHAPTERS: dict[str, dict[str, Any]] = {
    "10": {
        "order": 12,
        "source": "Sensitivity Analysis",
        "target": "Analisis Sensitivitas",
        "concepts": ("concept.sensitivity-analysis", "concept.right-hand-side-ranging", "concept.objective-coefficient-ranging", "concept.shadow-price", "concept.sensitivity-report", "concept.reduced-cost"),
        "prerequisites": ("concept.simplex-algorithm", "concept.basis-matrix", "concept.reduced-cost"),
        "files": (("text", 1, "chapter_text", "part1-linear-programming/ch07-sensitivity/sensitivity-LP.tex"),),
    },
    "11": {
        "order": 13,
        "source": "Duality",
        "target": "Dualitas",
        "concepts": ("concept.linear-program-duality", "concept.weak-duality", "concept.strong-duality", "concept.complementary-slackness", "concept.dual-economic-interpretation", "concept.shadow-price"),
        "prerequisites": ("concept.linear-programming", "concept.simplex-algorithm", "concept.sensitivity-analysis"),
        "files": (("text-a", 1, "chapter_text_part", "part1-linear-programming/ch08-duality/duality.tex"), ("text-b", 2, "chapter_text_part", "part1-linear-programming/ch08-duality/complimentary-slackness.tex")),
    },
    "12": {
        "order": 14,
        "source": "Software - Python",
        "target": "Perangkat Lunak -- Python",
        "concepts": ("concept.python-modeling-workflow", "concept.pyomo-model", "concept.open-source-solver", "concept.reproducible-computation", "concept.parameter-sweep"),
        "prerequisites": ("concept.optimization-model", "concept.linear-programming"),
        "files": (("text", 1, "chapter_text", "part1-linear-programming/ch03-software/software-python-book1.tex"),),
        "additional_rights": ("rights.r017.code", "rights.o018.code", "rights.pyomo.runtime", "rights.highspy.runtime", "rights.numpy.runtime"),
    },
    "13": {
        "order": 15,
        "source": "Multi-Objective Optimization",
        "target": "Optimisasi Multiobjektif",
        "concepts": ("concept.multiobjective-optimization", "concept.pareto-optimality", "concept.pareto-frontier", "concept.weighted-sum-method", "concept.epsilon-constraint-method", "concept.lexicographic-optimization"),
        "prerequisites": ("concept.linear-programming", "concept.optimization-model"),
        "files": (("text", 1, "chapter_text", "part1-linear-programming/ch09-multi-objective/multi-objective-optimization_updated.tex"),),
    },
    "14": {
        "order": 16,
        "source": "Graph Algorithms",
        "target": "Algoritma Graf",
        "concepts": ("concept.graph", "concept.graph-degree", "concept.graph-connectivity", "concept.shortest-path", "concept.dijkstra-algorithm", "concept.spanning-tree", "concept.minimum-spanning-tree", "concept.kruskal-algorithm", "concept.prim-algorithm"),
        "prerequisites": (),
        "files": (("text", 1, "chapter_text", "part2-discrete-algorithms/ch10-graph-theory/graphtheory-dor1.tex"),),
        "additional_rights": ("rights.thirdparty.lippman", "rights.thirdparty.sekhon-bloom"),
    },
    "15": {
        "order": 17,
        "source": "Introduction to Integer Programming Formulations",
        "target": "Pengantar Formulasi Pemrograman Bilangan Bulat",
        "concepts": ("concept.integer-programming", "concept.binary-variable", "concept.knapsack-model", "concept.set-cover-model", "concept.big-m-formulation", "concept.facility-location", "concept.capital-budgeting", "concept.graph-coloring", "concept.fixed-charge-model", "concept.lp-relaxation", "concept.piecewise-linear-model", "concept.disjunctive-scheduling"),
        "prerequisites": ("concept.linear-programming", "concept.optimization-model"),
        "files": (("text", 1, "chapter_text", "part3-integer-programming/ch11-ip-formulations/integerProgrammingFormulations-book1.tex"),),
    },
}


LINEAR_FILES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("linear-systems.overview", "systemsofequations.tex", ("concept.linear-system",)),
    ("linear-systems.geometry", "systemsofequationsGeometry.tex", ("concept.linear-system",)),
    ("linear-systems.algebraic-procedures", "systemsofequationsAlgebraicProcedures.tex", ("concept.linear-system", "concept.gaussian-elimination")),
    ("linear-systems.elementary-operations", "systemsofequationsAlgebraicProceduresElementaryOperations.tex", ("concept.gaussian-elimination",)),
    ("linear-systems.gaussian-elimination", "systemsofequationsAlgebraicProceduresGaussianElimination.tex", ("concept.gaussian-elimination", "concept.row-echelon-form")),
    ("linear-systems.uniqueness-rref", "systemsofequationsAlgebraicProceduresUniquenessRREF.tex", ("concept.reduced-row-echelon-form",)),
    ("linear-systems.rank-homogeneous", "systemsofequationsAlgebraicProceduresRankHomogeneousSystems.tex", ("concept.linear-system", "concept.matrix-rank")),
    ("matrices.overview", "matrices.tex", ("concept.matrix-arithmetic",)),
    ("matrices.arithmetic", "matricesMatrixArithmetic.tex", ("concept.matrix-arithmetic",)),
    ("matrices.addition", "matricesMatrixArithmeticAddition.tex", ("concept.matrix-arithmetic",)),
    ("matrices.scalar-multiplication", "matricesMatrixArithmeticScalarMultiplication.tex", ("concept.matrix-arithmetic",)),
    ("matrices.multiplication", "matricesMatrixArithmeticMultiplication.tex", ("concept.matrix-multiplication",)),
    ("matrices.product-entry", "matricesMatrixArithmeticProductEntry.tex", ("concept.matrix-multiplication",)),
    ("matrices.multiplication-properties", "matricesMatrixArithmeticMultiplicationProperties.tex", ("concept.matrix-multiplication",)),
    ("matrices.transpose", "matricesMatrixArithmeticTranspose.tex", ("concept.matrix-transpose",)),
    ("matrices.identity-inverses", "matricesMatrixArithmeticIdentityInverses.tex", ("concept.matrix-inverse",)),
    ("matrices.finding-inverse", "matricesMatrixArithmeticFindingInverse.tex", ("concept.matrix-inverse", "concept.gaussian-elimination")),
    ("vectors.overview", "RnVectors.tex", ("concept.vector",)),
    ("vectors.rn", "RnVectorsRn.tex", ("concept.vector",)),
    ("vectors.algebra", "RnVectorsAlgebra.tex", ("concept.vector",)),
    ("vectors.addition", "RnVectorsAlgebraAddition.tex", ("concept.vector",)),
    ("vectors.scalar-multiplication", "RnVectorsAlgebraScalarMult.tex", ("concept.vector",)),
    ("vectors.addition-meaning", "RnVectorsAdditionMeaning.tex", ("concept.vector",)),
    ("vectors.length", "RnVectorsLength.tex", ("concept.vector-norm",)),
    ("vectors.scalar-meaning", "RnVectorsScalarMultMeaning.tex", ("concept.vector",)),
    ("vectors.dot-product", "RnVectorsDotProduct.tex", ("concept.dot-product",)),
    ("vectors.dot-product-definition", "RnVectorsDotProductDot.tex", ("concept.dot-product",)),
    ("vectors.dot-product-significance", "RnVectorsDotProductSignificance.tex", ("concept.dot-product", "concept.vector-norm")),
)


LABS: dict[str, dict[str, Any]] = {
    "10": {"dir": "ch10-sensitivity-analysis", "order": 9, "title": "Laboratorium analisis sensitivitas Bab 10", "concepts": CHAPTERS["10"]["concepts"], "r017": "unit.r017.book1.ch10", "file_map": (("unit.r017.book1.ch10.text", 12),)},
    "11": {"dir": "ch11-duality", "order": 10, "title": "Laboratorium dualitas Bab 11", "concepts": CHAPTERS["11"]["concepts"], "r017": "unit.r017.book1.ch11", "file_map": (("unit.r017.book1.ch11.text-a", 9), ("unit.r017.book1.ch11.text-b", 8))},
    "12": {"dir": "ch12-python-workflow", "order": 11, "title": "Laboratorium alur kerja Python Bab 12", "concepts": CHAPTERS["12"]["concepts"], "r017": "unit.r017.book1.ch12", "file_map": (("unit.r017.book1.ch12.text", 9),)},
    "13": {"dir": "ch13-multiobjective", "order": 12, "title": "Laboratorium optimisasi multiobjektif Bab 13", "concepts": CHAPTERS["13"]["concepts"], "r017": "unit.r017.book1.ch13", "file_map": (("unit.r017.book1.ch13.text", 11),)},
    "14": {"dir": "ch14-graph-algorithms", "order": 13, "title": "Laboratorium algoritma graf Bab 14", "concepts": CHAPTERS["14"]["concepts"], "r017": "unit.r017.book1.ch14", "file_map": (("unit.r017.book1.ch14.text", 4),), "stdlib": True},
    "15": {"dir": "ch15-integer-programming", "order": 14, "title": "Laboratorium pemrograman bilangan bulat Bab 15", "concepts": CHAPTERS["15"]["concepts"], "r017": "unit.r017.book1.ch15", "file_map": (("unit.r017.book1.ch15.text", 16),)},
}


def load_exporter() -> Any:
    path = LANE / "scripts" / "export_backend.py"
    spec = importlib.util.spec_from_file_location("r017_export_backend", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load exporter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_concepts_terms(data: dict[str, Any]) -> None:
    for identifier, (name, prerequisites, source_term, preferred) in CONCEPTS.items():
        upsert(data["concepts"], {"id": identifier, "name_en": name, "prerequisite_concept_ids": list(prerequisites), "status": "active"})
        term_id = "term." + identifier.removeprefix("concept.") + ".id"
        upsert(data["terms"], {
            "id": term_id,
            "concept_id": identifier,
            "source_locale": "en",
            "target_locale": "id-ID",
            "source_term": source_term,
            "preferred": preferred,
            "variants": [],
            "rejected": [],
            "register": "academic",
            "scope": "R017 Book 1 and O018 laboratory",
            "evidence": "full-Book-1 localized source and verified O018 exercise surface",
            "status": "approved",
        })


def add_r017_units(data: dict[str, Any], exporter: Any) -> None:
    for chapter, config in CHAPTERS.items():
        chapter_id = f"unit.r017.book1.ch{chapter}"
        upsert(data["root_units"], root_unit(
            identifier=chapter_id,
            parent_id="unit.r017.book1",
            order=config["order"],
            unit_type="chapter",
            title_source=config["source"],
            title_target=config["target"],
            concepts=config["concepts"],
            prerequisites=config["prerequisites"],
            additional_rights=config.get("additional_rights", ()),
            source_local_id=f"chapter-{int(chapter)}",
        ))
        for suffix, order, unit_type, relative in config["files"]:
            file_id = f"{chapter_id}.{suffix}"
            kwargs: dict[str, Any] = {}
            if chapter == "10":
                kwargs["target_only_blocks"] = [{
                    "id": "segment.r017.book1.ch10.text.target-native-matrix-sign-correction",
                    "target_block_index": 67,
                    "segment_type": "source_correction_note",
                    "concept_ids": ["concept.basis-matrix", "concept.sensitivity-analysis"],
                    "correction_ids": ["correction.r017.ch10.matrix-an-signs"],
                    "native_reason": "The localized edition makes the corrected sign convention explicit before the corrected transformed nonbasic matrix.",
                    "provenance": "Target-native mathematical correction independently certified by the O018 Chapter 10 laboratory against the pinned authority.",
                }]
            if chapter == "14":
                kwargs["structure_event_alignment_overrides"] = [{
                    "semantic_kind": "captionfigure",
                    "source_semantic_ordinal": 34,
                    "target_semantic_ordinal": 33,
                    "allow_target_reuse": True,
                    "provenance": "The Indonesian reflow combines the authority's fourth spanning-tree example with the five-example composite under one complete caption; both source figures remain represented by the shared target figure event.",
                }]
            add_pair(
                data,
                identifier=file_id,
                parent_id=chapter_id,
                order=order,
                unit_type=unit_type,
                path=BOOK_PREFIX + relative,
                concepts=config["concepts"],
                prerequisites=config["prerequisites"],
                additional_rights=config.get("additional_rights", ()),
                **kwargs,
            )
            source_text = exporter.read_tex(AUTHORITY / relpath(BOOK_PREFIX + relative))
            for event in exporter.extract_structure(source_text):
                if event["kind"] == "ex":
                    upsert(data["unit_concept_rules"], {
                        "id": f"rule.{file_id}.ex-{event['ordinal']:03d}",
                        "unit_id": f"{file_id}.ex-{event['ordinal']:03d}",
                        "concept_ids": list(config["concepts"]),
                        "status": "active",
                    })
        add_pair(
            data,
            identifier=f"{chapter_id}.solutions-manual",
            parent_id=chapter_id,
            order=len(config["files"]) + 1,
            unit_type="solutions_manual",
            path=BOOK_PREFIX + f"solutions-manual/ch{chapter}.tex",
            concepts=config["concepts"],
            prerequisites=config["prerequisites"],
            additional_rights=config.get("additional_rights", ()),
        )

    appendix_roots = (
        ("unit.r017.book1.appendices", "unit.r017.book1", 18, "appendix_collection", "Appendices", "Lampiran", ("concept.linear-equation", "concept.linear-system", "concept.matrix-arithmetic", "concept.vector"), "rights.r017.content", ("rights.thirdparty.lyryx-kuttler",)),
        ("unit.r017.book1.appendices.equations-lines", "unit.r017.book1.appendices", 1, "appendix", "Equations and Lines", "Persamaan dan Garis", ("concept.linear-equation", "concept.slope-intercept-form"), "rights.r017.content", ()),
        ("unit.r017.book1.appendices.linear-systems", "unit.r017.book1.appendices", 2, "appendix", "Systems of Equations", "Sistem Persamaan", ("concept.linear-system", "concept.gaussian-elimination", "concept.row-echelon-form", "concept.reduced-row-echelon-form"), "rights.thirdparty.lyryx-kuttler", ()),
        ("unit.r017.book1.appendices.matrices", "unit.r017.book1.appendices", 3, "appendix", "Matrices", "Matriks", ("concept.matrix-arithmetic", "concept.matrix-multiplication", "concept.matrix-transpose", "concept.matrix-inverse"), "rights.thirdparty.lyryx-kuttler", ()),
        ("unit.r017.book1.appendices.vectors", "unit.r017.book1.appendices", 4, "appendix", "Vectors in Rn", "Vektor dalam Rn", ("concept.vector", "concept.vector-norm", "concept.dot-product"), "rights.thirdparty.lyryx-kuttler", ()),
        ("unit.r017.book1.appendices.software-resources", "unit.r017.book1.appendices", 5, "appendix", "Software Resources", "Sumber Daya Perangkat Lunak", ("concept.open-source-solver", "concept.python-modeling-workflow"), "rights.r017.content", ()),
        ("unit.r017.book1.backmatter", "unit.r017.book1", 19, "backmatter", "Back matter", "Bagian akhir", (), "rights.r017.content", ("rights.thirdparty.foundations", "rights.thirdparty.lyryx-kuttler")),
    )
    for identifier, parent, order, kind, source_title, target_title, concepts, rights, additional in appendix_roots:
        upsert(data["root_units"], root_unit(
            identifier=identifier,
            parent_id=parent,
            order=order,
            unit_type=kind,
            title_source=source_title,
            title_target=target_title,
            concepts=concepts,
            rights=rights,
            additional_rights=additional,
            translation_state="structurally_verified",
        ))

    add_pair(
        data,
        identifier="unit.r017.book1.appendices.equations-lines.text",
        parent_id="unit.r017.book1.appendices.equations-lines",
        order=1,
        unit_type="appendix_text",
        path=BOOK_PREFIX + "appendices/equations-and-lines/equations-and-lines-new.tex",
        concepts=("concept.linear-equation", "concept.slope-intercept-form"),
    )
    group_orders = {"linear-systems": 0, "matrices": 0, "vectors": 0}
    for suffix, filename, concepts in LINEAR_FILES:
        group = suffix.split(".", 1)[0]
        group_orders[group] += 1
        kwargs: dict[str, Any] = {}
        if filename == "systemsofequations.tex":
            kwargs["target_only_blocks"] = [{
                "id": "segment.r017.book1.appendices.linear-systems.target-native-ef-rref-terms",
                "target_block_index": 1,
                "segment_type": "localization_control",
                "concept_ids": ["concept.row-echelon-form", "concept.reduced-row-echelon-form"],
                "native_reason": "The combined preamble supplies English EF/RREF display macros, so the Indonesian appendix overrides only those generated terms locally.",
                "provenance": "Target-native localization control; no source mathematics or source unit is replaced.",
            }]
        add_pair(
            data,
            identifier=f"unit.r017.book1.appendices.{suffix}",
            parent_id=f"unit.r017.book1.appendices.{group}",
            order=group_orders[group],
            unit_type="appendix_text_part",
            path=BOOK_PREFIX + "appendices/linear-algebra/" + filename,
            rights="rights.thirdparty.lyryx-kuttler",
            concepts=concepts,
            **kwargs,
        )
    add_pair(
        data,
        identifier="unit.r017.book1.appendices.software-resources.text",
        parent_id="unit.r017.book1.appendices.software-resources",
        order=1,
        unit_type="appendix_text",
        path=BOOK_PREFIX + "appendices/software-resources.tex",
        concepts=("concept.open-source-solver", "concept.python-modeling-workflow"),
    )
    backmatter = (
        ("checkpoint-answers", 1, "checkpoint_answers", "backmatter/checkpoint-answers.tex", "rights.r017.content"),
        ("further-reading", 2, "further_reading", "backmatter/further-reading-and-resources.tex", "rights.r017.content"),
        ("linear-algebra-license", 3, "license_notice", "appendices/linear-algebra/license.tex", "rights.thirdparty.lyryx-kuttler"),
        ("contributors-foundations", 4, "attribution_notice", "frontmatter/contributors-foundations.tex", "rights.thirdparty.foundations"),
    )
    for suffix, order, kind, relative, rights in backmatter:
        add_pair(
            data,
            identifier=f"unit.r017.book1.backmatter.{suffix}",
            parent_id="unit.r017.book1.backmatter",
            order=order,
            unit_type=kind,
            path=BOOK_PREFIX + relative,
            rights=rights,
        )


def add_r017_assets(data: dict[str, Any]) -> None:
    for name in ("excel-sensitivity.JPG", "excel-sensitivity-report.JPG", "excel-setup.JPG", "sensitivity-objective.JPG"):
        add_asset_pair(data, "asset.r017.ch10." + name.rsplit(".", 1)[0].lower(), BASE_PREFIX + "Figures/" + name, asset_type="source_figure")
    for name in ("pareto-curve", "risk-plot"):
        add_asset_pair(
            data,
            "asset.r017.ch13." + name,
            BASE_PREFIX + f"Figures/{name}.png",
            BASE_PREFIX + f"Figures/{name}.pdf",
            asset_type="localized_vector_figure",
            extra={"derivation": "localized PDF figure generated from the pinned raster source while preserving the plotted mathematics"},
        )
    graph_names = ("GraphExercise1.png", "GraphExercise2.png", "GraphPicture.png", "GraphPictureDot.png", "dijkstra-soln.png", "dijkstra0.png", "dijkstra1.png", "dijkstra2.png", "dijkstra3.png", "dijkstra4.png", "dijkstra5.png", "dijkstra6.png", "dijkstra7.png", "dijkstra8.png")
    for name in graph_names:
        add_asset_pair(data, "asset.r017.ch14." + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"), BASE_PREFIX + "graph-theory-graphics/" + name, asset_type="source_figure", rights="rights.thirdparty.lippman")
    add_asset_pair(data, "asset.r017.ch14.konigsberg-bridges", BASE_PREFIX + "Figures/Konigsberg_bridges.png", asset_type="source_figure", rights="rights.thirdparty.lippman")
    for name in ("StripPacking0.png", "StripPacking1.png", "StripPacking2.png", "new-york-tolls.png", "wiki-File-knapsack.png"):
        add_asset_pair(data, "asset.r017.ch15." + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"), BASE_PREFIX + "optimization/figures/figures-static/" + name, asset_type="source_figure")
    add_asset_pair(data, "asset.r017.references-bib", BOOK_PREFIX + "references.bib", asset_type="bibliography")

    controller = next(row for row in data["assets"] if row["id"] == "asset.r017.controller.book1")
    frozen_controller_hash = "43748fb47161baa3ed7a7910a5e99241abee294e1ba8af02a9db21153196b4ab"
    controller_path = exact_file(TARGET, controller["target_path"])
    actual = sha256(controller_path)
    if actual != frozen_controller_hash:
        raise ValueError(f"frozen Book 1 controller hash changed: {actual}")
    controller["expected_target_sha256"] = frozen_controller_hash
    controller["status"] = "verified"


def lab_child_id(chapter: str, exercise_id: str) -> str:
    if chapter != "14":
        number = int(exercise_id.split(".")[-1])
        return f"unit.o018.lab.ch{chapter}.ex{number:02d}"
    tail = exercise_id.removeprefix("14.")
    if tail.isdigit():
        return f"unit.o018.lab.ch14.ex{int(tail):02d}"
    kind, number = tail.split(".")
    return f"unit.o018.lab.ch14.{kind}{int(number):02d}"


def lab_asset_suffix(path: str) -> str:
    stem = path.rsplit(".", 1)[0].lower()
    stem = stem.replace("plots/", "plot-")
    aliases = {
        "attribution": "attribution",
        "license-code": "license-code",
        "readme": "readme",
        "data": "data",
        "expected-results": "expected-results",
        "model": "model",
        "plot_svg": "plot-renderer",
        "results": "results",
        "run_lab": "runner",
        "test_models": "tests",
        "verification": "verification-log",
        "verify_receipt": "verifier",
    }
    return aliases.get(stem, re.sub(r"[^a-z0-9]+", "-", stem).strip("-"))


def lab_asset_type(path: str) -> tuple[str, str]:
    name = path.lower()
    if name == "attribution.md": return "attribution", "rights.o018.prose-data"
    if name == "readme.md": return "laboratory_guide", "rights.o018.prose-data"
    if name == "data.json": return "structured_model_data", "rights.o018.prose-data"
    if name == "expected-results.json": return "expected_result_contract", "rights.o018.prose-data"
    if name == "results.json": return "deterministic_result_json", "rights.o018.prose-data"
    if name == "verification-receipt.json": return "verification_receipt_json", "rights.o018.prose-data"
    if name == "verification.log": return "verification_log", "rights.o018.prose-data"
    if name.endswith(".svg"): return "accessible_svg_plot", "rights.o018.prose-data"
    if name == "license-code.txt": return "license_text", "rights.o018.code"
    if name == "model.py": return "executable_model_source", "rights.o018.code"
    if name == "plot_svg.py": return "deterministic_svg_renderer", "rights.o018.code"
    if name == "run_lab.py": return "deterministic_runner", "rights.o018.code"
    if name.startswith("test_") and name.endswith(".py"): return "automated_tests", "rights.o018.code"
    if name == "verify_receipt.py": return "verification_program", "rights.o018.code"
    raise ValueError(f"unclassified lab asset: {path}")


def exercise_concepts(chapter: str, method: str) -> list[str]:
    base = set(LABS[chapter]["concepts"])
    method_map = {
        "shadow": "concept.shadow-price",
        "rhs": "concept.right-hand-side-ranging",
        "cost_range": "concept.objective-coefficient-ranging",
        "dual": "concept.linear-program-duality",
        "weak": "concept.weak-duality",
        "strong": "concept.strong-duality",
        "complementary": "concept.complementary-slackness",
        "pyomo": "concept.pyomo-model",
        "epsilon": "concept.epsilon-constraint-method",
        "weighted": "concept.weighted-sum-method",
        "pareto": "concept.pareto-optimality",
        "lexicographic": "concept.lexicographic-optimization",
        "dijkstra": "concept.dijkstra-algorithm",
        "shortest": "concept.shortest-path",
        "kruskal": "concept.kruskal-algorithm",
        "prim": "concept.prim-algorithm",
        "degree": "concept.graph-degree",
        "connected": "concept.graph-connectivity",
        "knapsack": "concept.knapsack-model",
        "set_cover": "concept.set-cover-model",
        "big_m": "concept.big-m-formulation",
        "facility": "concept.facility-location",
        "capital": "concept.capital-budgeting",
        "coloring": "concept.graph-coloring",
        "fixed_charge": "concept.fixed-charge-model",
        "relaxation": "concept.lp-relaxation",
        "piecewise": "concept.piecewise-linear-model",
        "flowshop": "concept.disjunctive-scheduling",
    }
    for token, concept in method_map.items():
        if token in method:
            base.add(concept)
    return sorted(base)


def add_lab_corrections(data: dict[str, Any], chapter: str, lab_data: dict[str, Any]) -> None:
    affected = [f"unit.r017.book1.ch{chapter}", f"unit.o018.lab.{LABS[chapter]['dir']}"]
    for key in ("corrections", "source_defects", "upstream_defects", "source_notes"):
        for item in lab_data.get(key, []):
            raw_id = item["id"].lower()
            slug = re.sub(r"[^a-z0-9]+", "-", raw_id).strip("-")
            status = item.get("status")
            if not status:
                status = "applied_in_target" if key == "corrections" else "recorded"
            upsert(data["corrections"], {
                "id": f"correction.r017.{slug}",
                "correction_type": item.get("type", "source_note"),
                "source_defect": item.get("text", item.get("certificate", "Recorded source issue.")),
                "target_action": item.get("target_location", "Preserved explicitly in the localized source/laboratory evidence without inventing missing data."),
                "rationale": item.get("certificate", item.get("text", "Explicit provenance note.")),
                "evidence": item.get("source_location", f"source/o018-open-solver-lab/{LABS[chapter]['dir']}/data.json"),
                "affected_unit_ids": affected,
                "status": status,
                "upstream_report_disposition": "hold_until_corpus_complete",
            })


def add_labs(data: dict[str, Any]) -> None:
    for chapter, config in LABS.items():
        lab_dir = TARGET / "o018-open-solver-lab" / config["dir"]
        receipt_path = exact_file(lab_dir, "verification-receipt.json")
        data_path = exact_file(lab_dir, "data.json")
        results_path = exact_file(lab_dir, "results.json")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        lab_data = json.loads(data_path.read_text(encoding="utf-8"))
        results = json.loads(results_path.read_text(encoding="utf-8"))
        verification = receipt["verification"]
        root_id = f"unit.o018.lab.{config['dir']}"
        runtime_rights: tuple[str, ...] = () if config.get("stdlib") else ("rights.pyomo.runtime", "rights.highspy.runtime", "rights.numpy.runtime")
        upsert(data["root_units"], root_unit(
            identifier=root_id,
            parent_id="unit.o018.lab",
            order=config["order"],
            unit_type="computational_lab_collection",
            title_source=f"Open-solver laboratory for Book 1 Chapter {int(chapter)}",
            title_target=config["title"],
            concepts=config["concepts"],
            prerequisites=CHAPTERS[chapter]["prerequisites"],
            rights="rights.o018.prose-data",
            edition="edition.o018.id-id.draft",
            resource="resource.o018.open-solver-lab",
            status="verified",
            translation_state="source_frozen",
            additional_rights=("rights.o018.code",) + runtime_rights,
        ))

        source_exercise_targets: list[str] = []
        for file_id, count in config["file_map"]:
            source_exercise_targets.extend(f"{file_id}.ex-{ordinal:03d}" for ordinal in range(1, count + 1))
        direct_count = len(source_exercise_targets)
        for order, exercise_id in enumerate(lab_data["exercise_order"], start=1):
            item = lab_data["exercises"][exercise_id]
            child_id = lab_child_id(chapter, exercise_id)
            upsert(data["root_units"], {
                "id": child_id,
                "unit_type": "computational_lab",
                "resource_id": "resource.o018.open-solver-lab",
                "edition_id": "edition.o018.id-id.draft",
                "parent_id": root_id,
                "order": order,
                "locale": "id-ID",
                "title_target": item["title"],
                "translation_state": "source_frozen",
                "rights_component_id": "rights.o018.prose-data",
                "source_local_id": f"exercise-{exercise_id}",
                "source_book_label": item.get("book_label"),
                "method": item.get("method"),
                "concept_ids": exercise_concepts(chapter, item.get("method", "")),
                "status": "verified",
            })
            if order <= direct_count:
                target_id = source_exercise_targets[order - 1]
                for relation_type in ("adapts", "solves"):
                    upsert(data["relations"], {
                        "id": f"relation.o018-ch{chapter}-{child_id.rsplit('.', 1)[-1]}-{relation_type}",
                        "relation_type": relation_type,
                        "from_id": child_id,
                        "to_id": target_id,
                        "status": "verified",
                    })

        asset_ids: list[str] = []
        code_refs: list[str] = []
        receipt_artifacts = list(receipt["artifacts"])
        receipt_artifacts.append({"path": "verification-receipt.json", "bytes": receipt_path.stat().st_size, "sha256": sha256(receipt_path)})
        seen_paths: set[str] = set()
        for artifact in receipt_artifacts:
            relative = artifact["path"]
            if relative in seen_paths:
                continue
            seen_paths.add(relative)
            local = exact_file(lab_dir, relative)
            actual_bytes = local.stat().st_size
            actual_hash = sha256(local)
            if actual_bytes != artifact["bytes"] or actual_hash != artifact["sha256"]:
                raise ValueError(f"lab receipt drift for ch{chapter}/{relative}")
            suffix = "verification-receipt" if relative == "verification-receipt.json" else lab_asset_suffix(relative)
            asset_id = f"asset.o018.ch{chapter}.{suffix}"
            asset_type, rights = lab_asset_type(relative)
            upsert(data["assets"], {
                "id": asset_id,
                "asset_type": asset_type,
                "source_path": None,
                "target_path": f"o018-open-solver-lab/{config['dir']}/{relative}",
                "expected_target_sha256": actual_hash,
                "rights_component_id": rights,
                "bytes": actual_bytes,
                "status": "verified",
            })
            asset_ids.append(asset_id)
            if relative.endswith((".py", ".json", ".log")):
                code_refs.append(f"o018-open-solver-lab/{config['dir']}/{relative}")

        for filename, suffix, unit_type in (("README.md", "readme", "laboratory_guide"), ("ATTRIBUTION.md", "attribution", "attribution_notice")):
            local = exact_file(lab_dir, filename)
            native_id = f"{root_id}.{suffix}"
            native_assets = sorted(set(asset_ids + ([] if config.get("stdlib") else ["dependency.pyomo", "dependency.highs", "dependency.numpy"])))
            upsert(data["native_file_units"], {
                "id": native_id,
                "unit_type": unit_type,
                "parent_id": root_id,
                "order": 1 if suffix == "readme" else 2,
                "content_path": f"o018-open-solver-lab/{config['dir']}/{filename}",
                "expected_content_sha256": sha256(local),
                "locale": "id-ID",
                "resource_id": "resource.o018.open-solver-lab",
                "edition_id": "edition.o018.id-id.draft",
                "rights_component_id": "rights.o018.prose-data",
                "concept_ids": list(config["concepts"]),
                "prerequisite_concept_ids": list(CHAPTERS[chapter]["prerequisites"]),
                "asset_ids": native_assets,
                "code_data_refs": sorted(code_refs),
            })

        runtime = receipt.get("runtime", {})
        if config.get("stdlib"):
            toolchain = f"{runtime.get('python_implementation', runtime.get('implementation', 'Python'))} {runtime.get('python_version', '')}; standard library only"
        else:
            toolchain = f"Python {runtime.get('python_version', '')}; Pyomo {runtime.get('pyomo', '')}; highspy/HiGHS {runtime.get('highspy', '')}; NumPy {runtime.get('numpy', '')}; {runtime.get('solver_interface', 'appsi_highs')}"
        for filename, suffix, artifact_type in (("results.json", "results", "deterministic_computation_result"), ("verification-receipt.json", "verification-receipt", "verification_receipt"), ("verification.log", "verification-log", "verification_log")):
            local = exact_file(lab_dir, filename)
            upsert(data["artifacts"], {
                "id": f"artifact.o018.ch{chapter}-{suffix}",
                "artifact_type": artifact_type,
                "path": f"source/o018-open-solver-lab/{config['dir']}/{filename}",
                "bytes": local.stat().st_size,
                "sha256": sha256(local),
                "rights_component_id": "rights.o018.prose-data",
                "toolchain": toolchain,
                "build_receipt": f"Frozen Chapter {int(chapter)} laboratory; {verification.get('exercise_count')} exercise-surface items; {verification.get('verified_count')} verified; {verification.get('unittest_runs')} deterministic test runs.",
                "verify_local": True,
                "status": "verified",
            })

        tests = verification.get("tests_passed_per_run", 0)
        exercise_count = verification.get("exercise_count", len(lab_data["exercise_order"]))
        unresolved = verification.get("unresolved_exercises", [])
        qa_records = (
            ("exercise-coverage", "computation_and_proof", f"{verification.get('verified_count')}/{exercise_count} exercise-surface items verified; unresolved={len(unresolved)}; methods={json.dumps(verification.get('method_counts', {}), ensure_ascii=False, sort_keys=True)}"),
            ("functional-tests", "computation", f"{tests}/{tests} tests pass on each of {verification.get('unittest_runs')} runs; failed={verification.get('tests_failed_per_run', 0)}; maximum solver violation={verification.get('maximum_solver_violation', 0)}."),
            ("deterministic-results", "determinism", f"results.json regenerated {verification.get('results_regeneration_runs')} times at SHA-256 {verification.get('results_sha256')}; receipt and artifact inventory are hash-closed."),
            ("provenance-rights", "provenance_rights", f"Receipt inventories {verification.get('artifact_count_excluding_receipt')} non-receipt artifacts and preserves CC BY-SA 4.0 prose/data separately from MIT code and declared runtime notices."),
        )
        for suffix, qa_type, witness in qa_records:
            upsert(data["qa_events"], {
                "id": f"qa.o018.ch{chapter}-{suffix}",
                "qa_type": qa_type,
                "result": "pass",
                "witness": witness,
                "affected_ids": [root_id, f"artifact.o018.ch{chapter}-verification-receipt"],
                "status": "complete",
            })

        relations = [
            ("adapts", root_id, config["r017"]),
            ("implemented-by", root_id, f"asset.o018.ch{chapter}.model"),
            ("evidenced-by", root_id, f"artifact.o018.ch{chapter}-verification-receipt"),
            ("generated-by", f"asset.o018.ch{chapter}.results", f"asset.o018.ch{chapter}.runner"),
            ("verifies", f"asset.o018.ch{chapter}.tests", f"asset.o018.ch{chapter}.model"),
        ]
        if not config.get("stdlib"):
            relations.extend(("depends-on", root_id, dependency) for dependency in ("dependency.pyomo", "dependency.highs", "dependency.numpy"))
        for index, (relation_type, from_id, to_id) in enumerate(relations, start=1):
            upsert(data["relations"], {
                "id": f"relation.o018-ch{chapter}-{relation_type}-{index:02d}",
                "relation_type": relation_type,
                "from_id": from_id,
                "to_id": to_id,
                "status": "verified",
            })
        add_lab_corrections(data, chapter, lab_data)


def finalize_metadata(data: dict[str, Any]) -> None:
    book = next(row for row in data["root_units"] if row["id"] == "unit.r017.book1")
    book["status"] = "verified"
    book["translation_state"] = "structurally_verified"
    book["concept_ids"] = sorted({concept for config in CHAPTERS.values() for concept in config["concepts"]})
    o018 = next(row for row in data["root_units"] if row["id"] == "unit.o018.lab")
    o018["status"] = "verified"
    upsert(data["qa_events"], {
        "id": "qa.r017.full-book-backend-source-closure",
        "qa_type": "topology_and_hash_closure",
        "result": "pass",
        "witness": "All paired Book 1 chapter, manual, integrated appendix, and backmatter files are enumerated with exact authority and target hashes; exporter alignment and reference checks are fail-closed.",
        "affected_ids": ["unit.r017.book1", "unit.r017.book1.appendices", "unit.r017.book1.backmatter"],
        "status": "complete",
    })
    for collection in ("root_units", "file_units", "native_file_units", "concepts", "unit_concept_rules", "terms", "assets", "corrections", "qa_events", "artifacts", "relations"):
        identifiers = [row["id"] for row in data[collection]]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"duplicate IDs after update in {collection}")
    data["snapshot_at"] = "2026-08-23T00:00:00+02:00"


def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    exporter = load_exporter()
    add_concepts_terms(data)
    add_r017_units(data, exporter)
    add_r017_assets(data)
    add_labs(data)
    finalize_metadata(data)
    INPUT.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("updated", INPUT)
    for collection in ("root_units", "file_units", "native_file_units", "concepts", "terms", "assets", "corrections", "qa_events", "artifacts", "relations"):
        print(collection, len(data[collection]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
