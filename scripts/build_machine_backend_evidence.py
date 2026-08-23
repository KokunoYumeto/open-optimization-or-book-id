#!/usr/bin/env python3
"""Build the bounded machine-backend authority and disposition receipt.

The receipt is deliberately separate from release assembly.  It freezes the
three declared submodule archives and inventories every operational XLSX,
PuLP/Gurobi notebook, and NetworkX instructional notebook in the pinned R017
authority.  Target-tree and current public-source-package presence are recorded
independently so a frozen authority witness is never mistaken for a shipped
file.  The script uses only the Python standard library and supports a strict
byte-for-byte ``--check`` mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_COMMIT = "1745df89b608899f66983834fa4ec8c8910d18ff"
AUTHORITY_TREE = "209d5de696ebac4e5921b73d6b6b2f539fc23d1c"
AUTHORITY_ROOT_RELATIVE = (
    "authority/upstream/open-optimization-or-book-"
    f"{AUTHORITY_COMMIT}"
)
AUTHORITY_ROOT = ROOT / AUTHORITY_ROOT_RELATIVE
OPTIMIZATION_DIRECTORY = (
    "Intro-Math-Programming/baseText/optimization/optimization-examples"
)
PUBLIC_SOURCE_PACKAGE = (
    "release/out/"
    "pemrograman-matematis-dan-riset-operasi-buku-1-source-id-ID.zip"
)
OUTPUT = ROOT / "00_control" / "MACHINE_BACKEND_EVIDENCE.json"


SUBMODULES = (
    {
        "id": "artifact.authority.submodule-archive.open-optimization-bibliography",
        "repository": "open-optimization-bibliography",
        "commit": "f8516c2c252fda30a8d3239da05cd07c55d2631b",
    },
    {
        "id": "artifact.authority.submodule-archive.open-optimization-common",
        "repository": "open-optimization-common",
        "commit": "dee882b717018318689f4b373ea1bfc82ddaed6c",
    },
    {
        "id": "artifact.authority.submodule-archive.open-optimization-or-examples",
        "repository": "open-optimization-or-examples",
        "commit": "dc866da8b04bc89289c87afbea649da2044c7799",
    },
)


# Existing backend IDs are discovered from backend-input.json.  Only genuinely
# missing records need names here; this preserves every admitted ID verbatim.
MISSING_IDS = {
    "bakery-production-excel.xlsx": "asset.r017.ch02.workbook.bakery-production",
    "capital-allocation-excel.xlsx": "asset.r017.ch02.workbook.capital-allocation",
    "diet-problem-next.xlsx": "asset.r017.ch02.workbook.diet-problem-next",
    "diet-problem.xlsx": "asset.r017.ch02.workbook.diet-problem",
    "knapsack-problem-excel.xlsx": "asset.r017.ch02.workbook.knapsack-problem",
    "production-planning-excel.xlsx": "asset.r017.ch02.workbook.production-planning",
    "work_scheduling_excel.xlsx": "asset.r017.ch02.workbook.work-scheduling",
    "work_scheduling_excel_extended.xlsx": "asset.r017.ch02.workbook.work-scheduling-extended",
    "bakery_production_gurobi.ipynb": "asset.r017.ch02.notebook.bakery-production.gurobi",
    "bakery_production_pulp.ipynb": "asset.r017.ch02.notebook.bakery-production.pulp",
    "diet_problem_gurobi.ipynb": "asset.r017.ch02.notebook.diet-problem.gurobi",
    "diet_problem_next_gurobi.ipynb": "asset.r017.ch02.notebook.diet-problem-next.gurobi",
    "diet_problem_next_pulp.ipynb": "asset.r017.ch02.notebook.diet-problem-next.pulp",
    "diet_problem_pulp.ipynb": "asset.r017.ch02.notebook.diet-problem.pulp",
    "knapsack_gurobi.ipynb": "asset.r017.ch02.notebook.knapsack.gurobi",
    "knapsack_pulp.ipynb": "asset.r017.ch02.notebook.knapsack.pulp",
    "knapsack-capital-allocation-gurobi.ipynb": "asset.r017.ch02.notebook.knapsack-capital-allocation.gurobi",
    "knapsack-capital-allocation-pulp.ipynb": "asset.r017.ch02.notebook.knapsack-capital-allocation.pulp",
    "knapsack-three-two-one-gurobi.ipynb": "asset.r017.ch02.notebook.knapsack-three-two-one.gurobi",
    "knapsack-three-two-one-pulp.ipynb": "asset.r017.ch02.notebook.knapsack-three-two-one.pulp",
    "min_coins_gurobi.ipynb": "asset.r017.ch02.notebook.min-coins.gurobi",
    "min_coins_pulp.ipynb": "asset.r017.ch02.notebook.min-coins.pulp",
    "production_planning_gurobi.ipynb": "asset.r017.ch02.notebook.production-planning.gurobi",
    "production_planning_pulp.ipynb": "asset.r017.ch02.notebook.production-planning.pulp",
    "work_scheduling_extended_gurobi.ipynb": "asset.r017.ch02.notebook.work-scheduling-extended.gurobi",
    "work_scheduling_extended_pulp.ipynb": "asset.r017.ch02.notebook.work-scheduling-extended.pulp",
    "work_scheduling_gurobi.ipynb": "asset.r017.ch02.notebook.work-scheduling.gurobi",
    "work_scheduling_pulp.ipynb": "asset.r017.ch02.notebook.work-scheduling.pulp",
}


NETWORKX_NOTEBOOKS = (
    {
        "id": "asset.r017.ch14.notebook.networkx-dijkstra",
        "name": "networkx example - Dijkstra's Algorithm.ipynb",
        "active_source_references": [
            (
                "source/Intro-Math-Programming/baseText/book/"
                "part2-discrete-algorithms/ch10-graph-theory/"
                "graphtheory-dor1.tex:387"
            ),
            (
                "source/Intro-Math-Programming/baseText/book/"
                "part2-discrete-algorithms/ch10-graph-theory/"
                "graphtheory-dor1.tex:726"
            ),
        ],
        "source_linkage": "active_chapter_14_intro_and_dijkstra_witness",
        "o018_unit_ids": [
            "unit.o018.lab.ch14.ex-14-2",
            "unit.o018.lab.ch14.ex-14-4",
        ],
        "o018_note": (
            "O018 supplies a separately authored standard-library Python "
            "companion and shortest-path verification; its locked runtime "
            "does not include NetworkX."
        ),
    },
    {
        "id": "asset.r017.ch14.notebook.networkx-kruskal",
        "name": "networkx example - Kruskal's algorithm.ipynb",
        "active_source_references": [],
        "source_linkage": "instructional_source_witness_not_linked_from_active_translated_build",
        "o018_unit_ids": ["unit.o018.lab.ch14.ex-14-1"],
        "o018_note": (
            "O018 verifies Kruskal with a separately authored standard-library "
            "implementation and exhaustive spanning-tree cross-check; its "
            "locked runtime does not include NetworkX."
        ),
    },
)


VISUALIZATION_RUNTIME_FILES = (
    {
        "asset_id": "asset.r017.ch03.interactive-excel-solver",
        "path": "excel_solver_demo.jsx",
        "asset_type": "localized_interactive_source",
        "existing_backend_record": True,
        "status": "built",
        "closure_role": "demo_entry_module",
    },
    {
        "asset_id": "asset.r017.ch04.interactive-network-flow",
        "path": "network_flow_demo.jsx",
        "asset_type": "localized_jsx_interactive",
        "existing_backend_record": True,
        "status": "verified",
        "closure_role": "demo_entry_module",
    },
    {
        "asset_id": "asset.r017.ch04.interactive-math-import",
        "path": "math.jsx",
        "asset_type": "source_javascript_dependency",
        "existing_backend_record": True,
        "status": "verified",
        "closure_role": "shared_source_dependency",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.package-json",
        "path": "package.json",
        "asset_type": "javascript_package_manifest",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "pinned_runtime_manifest",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.package-lock",
        "path": "package-lock.json",
        "asset_type": "javascript_dependency_lockfile",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "pinned_transitive_dependency_lock",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.vite-config",
        "path": "vite.config.js",
        "asset_type": "javascript_build_configuration",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "build_configuration",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.index-html",
        "path": "index.html",
        "asset_type": "html_application_entrypoint",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "browser_entrypoint",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.app-entry",
        "path": "src/App.jsx",
        "asset_type": "react_application_entrypoint",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "application_router",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.main-entry",
        "path": "src/main.jsx",
        "asset_type": "react_dom_entrypoint",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "react_dom_bootstrap",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.readme",
        "path": "README.md",
        "asset_type": "runtime_build_instructions",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "offline_build_instructions",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.third-party-notices",
        "path": "THIRD_PARTY-NOTICES.md",
        "asset_type": "third_party_notice",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "runtime_rights_notice",
    },
    {
        "asset_id": "asset.r017.visualization-runtime.gitignore",
        "path": ".gitignore",
        "asset_type": "source_exclusion_configuration",
        "existing_backend_record": False,
        "status": "verified",
        "closure_role": "generated_directory_exclusion",
    },
)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def canonical_compact_json(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "sha256": sha256_file(path)}


def directory_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
        if candidate.is_file():
            rows.append(
                {
                    "path": candidate.relative_to(path).as_posix(),
                    **file_identity(candidate),
                }
            )
    return rows


def submodule_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in SUBMODULES:
        stem = f"{spec['repository']}-{spec['commit']}"
        archive_relative = f"authority/archives/{stem}.zip"
        extracted_relative = f"authority/submodules/{stem}"
        archive = ROOT / archive_relative
        extracted = ROOT / extracted_relative
        if not archive.is_file() or not extracted.is_dir():
            raise FileNotFoundError(f"missing frozen submodule evidence for {stem}")
        with zipfile.ZipFile(archive) as handle:
            file_entries = [item for item in handle.infolist() if not item.is_dir()]
            archive_entry_count = len(handle.infolist())
            uncompressed_file_bytes = sum(item.file_size for item in file_entries)
        manifest = directory_manifest(extracted)
        if len(manifest) != len(file_entries):
            raise ValueError(f"archive/extracted file-count mismatch for {stem}")
        extracted_bytes = sum(item["bytes"] for item in manifest)
        if extracted_bytes != uncompressed_file_bytes:
            raise ValueError(f"archive/extracted byte-count mismatch for {stem}")
        rows.append(
            {
                **spec,
                "archive_path": archive_relative,
                "archive_entry_count": archive_entry_count,
                "archive_file_count": len(file_entries),
                "archive_uncompressed_file_bytes": uncompressed_file_bytes,
                "archive_bytes": archive.stat().st_size,
                "archive_sha256": sha256_file(archive),
                "extracted_path": extracted_relative,
                "extracted_file_count": len(manifest),
                "extracted_file_bytes": extracted_bytes,
                "extracted_closure_sha256": sha256_bytes(
                    canonical_compact_json(manifest)
                ),
                "build_admission_disposition": (
                    "frozen_local_gitlink_authority_only; contents remain "
                    "excluded from the admitted Book 1 build unless a bounded "
                    "dependency trace proves use"
                ),
            }
        )
    return rows


def mapped_o018(
    unit_id: str,
    disposition: str,
    role: str,
    note: str,
) -> dict[str, Any]:
    return {
        "pyomo_highs_applicability": "applicable",
        "disposition": disposition,
        "mapping_unit_ids": [unit_id],
        "mapping_role": role,
        "runtime_dependency_ids": ["dependency.pyomo", "dependency.highs"],
        "scope_note": note,
    }


def no_o018_mapping() -> dict[str, Any]:
    return {
        "pyomo_highs_applicability": "not_mapped",
        "disposition": "no_item_level_o018_pyomo_highs_mapping",
        "mapping_unit_ids": [],
        "mapping_role": "r017_authority_witness_only",
        "runtime_dependency_ids": [],
        "scope_note": (
            "The current O018 inventory does not claim a Pyomo+HiGHS "
            "replacement for this exact witness; it remains frozen R017 "
            "authority evidence only."
        ),
    }


O018_BY_FILENAME: dict[str, dict[str, Any]] = {}


def register_o018(
    filenames: tuple[str, ...],
    unit_id: str,
    disposition: str,
    role: str,
    note: str,
) -> None:
    mapping = mapped_o018(unit_id, disposition, role, note)
    for filename in filenames:
        if filename in O018_BY_FILENAME:
            raise ValueError(f"duplicate O018 mapping for {filename}")
        O018_BY_FILENAME[filename] = mapping


register_o018(
    (
        "production-10period-excel.xlsx",
        "production_10period_pulp.ipynb",
        "production_10period_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.production-10period",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The O018 case is executable and verified with maximum violation 0.0.",
)
register_o018(
    ("production-planning-data.xlsx",),
    "unit.o018.lab.ch04.production-10period",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "supporting_parameter_workbook",
    "The workbook is supporting input evidence for the verified ten-period production case.",
)
register_o018(
    (
        "production-overtime-excel.xlsx",
        "production_overtime_pulp.ipynb",
        "production_overtime_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.production-overtime",
    "parameter_required_no_complete_executable_replacement",
    "direct_model_family_witness",
    (
        "O018 preserves the missing regular/overtime capacity parameters and "
        "does not fabricate an executable optimum."
    ),
)
register_o018(
    ("production_costs.xlsx",),
    "unit.o018.lab.ch04.production-overtime",
    "parameter_required_no_complete_executable_replacement",
    "supporting_parameter_workbook",
    (
        "The costs/demand workbook is preserved as support evidence, but the "
        "capacity omission leaves the O018 case parameter_required."
    ),
)
register_o018(
    (
        "machine-assignment-excel.xlsx",
        "machine_assignment_pulp.ipynb",
        "machine_assignment_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.assignment-machine",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The binary assignment adaptation is executable and verified.",
)
register_o018(
    (
        "school-bus-excel.xlsx",
        "school_bus_pulp.ipynb",
        "school_bus_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.assignment-school-bus",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The school-bus assignment adaptation is executable and verified.",
)
register_o018(
    (
        "assignment-problem-excel.xlsx",
        "assignment_problem_pulp.ipynb",
        "assignment_problem_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.assignment-generic",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The generic assignment adaptation is executable and verified.",
)
register_o018(
    (
        "absolute-value-excel.xlsx",
        "absolute_value_pulp.ipynb",
        "absolute_value_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.absolute-deviation",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The absolute-deviation linearization is executable and verified.",
)
register_o018(
    (
        "network-flow-excel.xlsx",
        "network_flow_pulp.ipynb",
        "network_flow_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.min-cost-flow-warehouses",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The warehouse/store minimum-cost-flow adaptation is executable and verified.",
)
register_o018(
    (
        "airline-maxflow-excel.xlsx",
        "airline_maxflow_pulp.ipynb",
        "airline_maxflow_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.airline-max-flow",
    "verified_corrected_adaptation_with_explicit_witness_divergence",
    "direct_model_family_witness",
    (
        "The frozen workbook/notebooks encode d->e and objective 9; O018 "
        "separately implements the printed/corrected d->t network with "
        "objective 12 and records the divergence."
    ),
)
register_o018(
    ("multicommodity_flow_pulp.ipynb", "multicommodity_flow_gurobi.ipynb"),
    "unit.o018.lab.ch04.multicommodity-integer",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The integer multicommodity-flow adaptation is executable and verified.",
)
register_o018(
    (
        "multicommodity_sourcesink_pulp.ipynb",
        "multicommodity_sourcesink_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.multicommodity-fractional",
    "verified_separately_attributed_pyomo_highs_adaptation",
    "direct_model_family_witness",
    "The fractional source/sink multicommodity adaptation is executable and verified.",
)
register_o018(
    (
        "multi-period-investment-excel.xlsx",
        "multi_period_investment_pulp.ipynb",
        "multi_period_investment_gurobi.ipynb",
    ),
    "unit.o018.lab.ch04.investment-multi-period",
    "design_unresolved_no_complete_executable_replacement",
    "direct_model_family_witness",
    (
        "O018 records the unresolved variable-domain, idle-cash, repeat-choice, "
        "and payout-timing questions and does not invent a solver result."
    ),
)


def platform_fields(filename: str) -> dict[str, Any]:
    if filename.endswith(".xlsx"):
        return {
            "witness_kind": "operational_non_macro_xlsx",
            "format_classification": "openxml_non_macro_xlsx",
            "platform_classification": (
                "cross-application OOXML file; the R017 operational "
                "Excel/Excel Solver workflow is proprietary and external"
            ),
            "proprietary_runtime_required_for_r017_workflow": True,
            "runtime_dependencies": ["Microsoft Excel", "Excel Solver where modeled"],
            "runtime_dependency_ids": ["dependency.excel"],
            "runtime_closure_disposition": "external_proprietary_runtime_not_shipped",
        }
    if filename.endswith("_pulp.ipynb") or filename.endswith("-pulp.ipynb"):
        return {
            "witness_kind": "optimization_notebook_pulp",
            "format_classification": "jupyter_notebook_json",
            "platform_classification": "open_source_python_pulp_solver_workflow",
            "proprietary_runtime_required_for_r017_workflow": False,
            "runtime_dependencies": ["Python", "Jupyter", "PuLP", "PuLP solver backend"],
            "runtime_dependency_ids": [],
            "runtime_closure_disposition": "external_runtime_not_frozen_or_shipped_for_this_witness",
        }
    if filename.endswith("_gurobi.ipynb") or filename.endswith("-gurobi.ipynb"):
        return {
            "witness_kind": "optimization_notebook_gurobi",
            "format_classification": "jupyter_notebook_json",
            "platform_classification": "python_notebook_requiring_proprietary_gurobi_runtime_and_license",
            "proprietary_runtime_required_for_r017_workflow": True,
            "runtime_dependencies": ["Python", "Jupyter", "gurobipy/Gurobi"],
            "runtime_dependency_ids": ["dependency.gurobi"],
            "runtime_closure_disposition": "external_proprietary_runtime_not_shipped",
        }
    raise ValueError(f"unclassified optimization witness {filename}")


def presence_record(path: Path, relative: str | None) -> dict[str, Any]:
    if relative is None or not path.is_file():
        return {"present": False, "path": relative, "bytes": None, "sha256": None}
    return {"present": True, "path": relative, **file_identity(path)}


def disposition(
    authority_present: bool,
    localized_present: bool,
    public_authority_present: bool,
    public_localized_present: bool,
) -> str:
    if authority_present != public_authority_present:
        raise ValueError("target/public authority-witness presence mismatch")
    if localized_present != public_localized_present:
        raise ValueError("target/public localized-derivative presence mismatch")
    if authority_present and localized_present:
        return "authority_original_and_localized_derivative_present_in_target_and_current_public_source_package"
    if authority_present:
        return "authority_original_present_in_target_and_current_public_source_package"
    if localized_present:
        return "authority_original_pruned; localized_derivative_present_in_target_and_current_public_source_package"
    return "authority_original_pruned_from_target_and_current_public_source_package; frozen_authority_only"


def witness_rows(public_entries: set[str]) -> list[dict[str, Any]]:
    backend = json.loads((ROOT / "backend/input/backend-input.json").read_text(encoding="utf-8"))
    existing_by_source: dict[str, dict[str, Any]] = {}
    for seed in backend["assets"]:
        source_path = seed.get("source_path")
        if not source_path:
            continue
        if source_path in existing_by_source:
            raise ValueError(f"duplicate existing asset source path {source_path}")
        existing_by_source[source_path] = seed

    directory = AUTHORITY_ROOT / OPTIMIZATION_DIRECTORY
    workbooks = sorted(directory.glob("*.xlsx"), key=lambda path: path.name)
    notebooks = sorted(directory.glob("*.ipynb"), key=lambda path: path.name)
    if len(workbooks) != 19:
        raise ValueError(f"expected 19 XLSX witnesses, found {len(workbooks)}")
    if len(notebooks) != 42:
        raise ValueError(f"expected 42 optimization notebooks, found {len(notebooks)}")
    pulp = [path for path in notebooks if "pulp" in path.stem]
    gurobi = [path for path in notebooks if "gurobi" in path.stem]
    if len(pulp) != 21 or len(gurobi) != 21 or len(pulp) + len(gurobi) != len(notebooks):
        raise ValueError(
            f"expected 21 PuLP/21 Gurobi notebooks, found {len(pulp)}/{len(gurobi)}"
        )

    rows: list[dict[str, Any]] = []
    for source_file in workbooks + notebooks:
        source_relative = f"{OPTIMIZATION_DIRECTORY}/{source_file.name}"
        existing = existing_by_source.get(source_relative)
        identifier = existing["id"] if existing else MISSING_IDS.get(source_file.name)
        if not identifier:
            raise ValueError(f"no stable ID assigned for {source_file.name}")
        if existing:
            expected = existing.get("source_sha256")
            if expected and expected != sha256_file(source_file):
                raise ValueError(f"existing source guard drift for {identifier}")
        target_path = existing.get("target_path") if existing else None
        localized_path = target_path if target_path and target_path != source_relative else None
        authority_target_path = ROOT / "source" / source_relative
        localized_target_path = ROOT / "source" / localized_path if localized_path else Path()
        authority_presence = presence_record(authority_target_path, source_relative)
        localized_presence = presence_record(localized_target_path, localized_path)
        public_authority_path = f"source/{source_relative}"
        public_localized_path = f"source/{localized_path}" if localized_path else None
        public_authority_present = public_authority_path in public_entries
        public_localized_present = bool(
            public_localized_path and public_localized_path in public_entries
        )
        rows.append(
            {
                "id": identifier,
                "source_path": source_relative,
                **file_identity(source_file),
                **platform_fields(source_file.name),
                "rights_component_id": "rights.r017.code",
                "existing_backend_record": existing is not None,
                "target_path": target_path,
                "authority_witness_target_presence": authority_presence,
                "localized_derivative_target_presence": localized_presence,
                "current_public_source_package_presence": {
                    "authority_witness_path": public_authority_path,
                    "authority_witness_present": public_authority_present,
                    "localized_derivative_path": public_localized_path,
                    "localized_derivative_present": public_localized_present,
                },
                "distribution_disposition": disposition(
                    authority_presence["present"],
                    localized_presence["present"],
                    public_authority_present,
                    public_localized_present,
                ),
                "o018_pyomo_highs": O018_BY_FILENAME.get(
                    source_file.name, no_o018_mapping()
                ),
                "status": existing.get("status") if existing else "authority_frozen_target_pruned",
            }
        )

    for spec in NETWORKX_NOTEBOOKS:
        source_relative = f"instructive-code/{spec['name']}"
        source_file = AUTHORITY_ROOT / source_relative
        if not source_file.is_file():
            raise FileNotFoundError(f"missing NetworkX witness {source_relative}")
        authority_target_path = ROOT / "source" / source_relative
        authority_presence = presence_record(authority_target_path, source_relative)
        public_path = f"source/{source_relative}"
        public_present = public_path in public_entries
        rows.append(
            {
                "id": spec["id"],
                "source_path": source_relative,
                **file_identity(source_file),
                "witness_kind": "instructional_notebook_networkx",
                "format_classification": "jupyter_notebook_json",
                "platform_classification": "open_source_python_networkx_workflow",
                "proprietary_runtime_required_for_r017_workflow": False,
                "runtime_dependencies": ["Python", "Jupyter", "NetworkX"],
                "runtime_dependency_ids": [],
                "runtime_closure_disposition": "external_runtime_not_frozen_or_shipped_for_this_witness",
                "rights_component_id": "rights.r017.code",
                "existing_backend_record": False,
                "target_path": None,
                "authority_witness_target_presence": authority_presence,
                "localized_derivative_target_presence": presence_record(Path(), None),
                "current_public_source_package_presence": {
                    "authority_witness_path": public_path,
                    "authority_witness_present": public_present,
                    "localized_derivative_path": None,
                    "localized_derivative_present": False,
                },
                "distribution_disposition": disposition(
                    authority_presence["present"], False, public_present, False
                ),
                "active_source_references": spec["active_source_references"],
                "source_linkage": spec["source_linkage"],
                "o018_pyomo_highs": {
                    "pyomo_highs_applicability": "not_applicable",
                    "disposition": "separately_authored_standard_library_graph_replacement",
                    "mapping_unit_ids": spec["o018_unit_ids"],
                    "mapping_role": "algorithmic_open_runtime_replacement",
                    "runtime_dependency_ids": [],
                    "scope_note": spec["o018_note"],
                },
                "status": "authority_frozen_target_pruned",
            }
        )

    identifiers = [row["id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate stable IDs in machine witness inventory")
    source_paths = [row["source_path"] for row in rows]
    if len(source_paths) != len(set(source_paths)):
        raise ValueError("duplicate paths in machine witness inventory")
    return sorted(rows, key=lambda row: row["id"])


def visualization_runtime_closure() -> dict[str, Any]:
    relative_root = "visualizations/source"
    target_root = ROOT / "source" / relative_root
    backend = json.loads(
        (ROOT / "backend/input/backend-input.json").read_text(encoding="utf-8")
    )
    existing_by_id = {row["id"]: row for row in backend["assets"]}
    files: list[dict[str, Any]] = []
    for spec in VISUALIZATION_RUNTIME_FILES:
        target_relative = f"{relative_root}/{spec['path']}"
        target = ROOT / "source" / target_relative
        if not target.is_file():
            raise FileNotFoundError(f"missing visualization runtime file {target}")
        existing = existing_by_id.get(spec["asset_id"])
        if spec["existing_backend_record"] != (existing is not None):
            raise ValueError(
                f"visualization existing-record drift for {spec['asset_id']}"
            )
        if existing is not None and existing.get("target_path") not in (
            None,
            target_relative,
        ):
            raise ValueError(
                f"visualization target semantics changed for {spec['asset_id']}"
            )
        files.append(
            {
                **spec,
                "target_path": target_relative,
                **file_identity(target),
                "rights_component_id": "rights.r017.code",
            }
        )
    identities = [
        {"path": row["target_path"], "bytes": row["bytes"], "sha256": row["sha256"]}
        for row in sorted(files, key=lambda item: item["target_path"])
    ]
    return {
        "target_root": relative_root,
        "file_count": len(files),
        "closure_bytes": sum(row["bytes"] for row in files),
        "closure_sha256": sha256_bytes(canonical_compact_json(identities)),
        "files": sorted(files, key=lambda row: row["asset_id"]),
        "qa_commands": [
            {
                "command": "npm ci --ignore-scripts --offline",
                "result": "pass",
                "note": (
                    "The offline flag proves the pinned package-lock closure "
                    "was sufficient without network access."
                ),
            },
            {
                "command": "npm run build",
                "result": "pass",
                "note": "Vite 5.4.11 transformed 1,580 modules and completed the production build.",
            },
        ],
        "generated_directories": [
            {
                "path": "visualizations/source/node_modules",
                "disposition": "generated_for_offline_QA_then_removed_not_shipped",
            },
            {
                "path": "visualizations/source/dist",
                "disposition": "generated_for_build_QA_then_removed_not_shipped",
            },
        ],
        "adverse_ledger_event_id": "R017-ADV-0006",
        "status": "verified_runnable_pinned_source_closure",
    }


def build() -> dict[str, Any]:
    package = ROOT / PUBLIC_SOURCE_PACKAGE
    if not package.is_file():
        raise FileNotFoundError(f"missing public source-package probe {package}")
    with zipfile.ZipFile(package) as handle:
        public_entries = {item.filename for item in handle.infolist() if not item.is_dir()}
    witnesses = witness_rows(public_entries)
    counts = {
        "operational_non_macro_xlsx": sum(
            row["witness_kind"] == "operational_non_macro_xlsx" for row in witnesses
        ),
        "optimization_notebook_pulp": sum(
            row["witness_kind"] == "optimization_notebook_pulp" for row in witnesses
        ),
        "optimization_notebook_gurobi": sum(
            row["witness_kind"] == "optimization_notebook_gurobi" for row in witnesses
        ),
        "instructional_notebook_networkx": sum(
            row["witness_kind"] == "instructional_notebook_networkx" for row in witnesses
        ),
    }
    expected_counts = {
        "operational_non_macro_xlsx": 19,
        "optimization_notebook_pulp": 21,
        "optimization_notebook_gurobi": 21,
        "instructional_notebook_networkx": 2,
    }
    if counts != expected_counts:
        raise ValueError(f"machine witness count mismatch: {counts}")
    return {
        "schema_name": "interlanguage.machine-backend-evidence",
        "schema_version": "0.1.0",
        "snapshot_at": "2026-08-23",
        "authority": {
            "commit": AUTHORITY_COMMIT,
            "tree": AUTHORITY_TREE,
            "root": AUTHORITY_ROOT_RELATIVE,
        },
        "public_distribution_probe": {
            "path": PUBLIC_SOURCE_PACKAGE,
            **file_identity(package),
            "scope_note": (
                "Read-only local snapshot probe used only to distinguish "
                "public-package presence from authority and target-tree presence."
            ),
        },
        "inventory_assertions": {
            **counts,
            "total_machine_witnesses": len(witnesses),
            "submodule_archives": len(SUBMODULES),
        },
        "submodule_archives": submodule_rows(),
        "machine_witnesses": witnesses,
        "visualization_runtime_closure": visualization_runtime_closure(),
        "terminal_state": (
            "complete when the deterministic backend exporter validates this "
            "receipt, emits every item, and passes required-target write/check"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="compare deterministic receipt bytes to disk"
    )
    args = parser.parse_args()
    data = canonical_json(build())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            raise ValueError(f"machine-backend evidence byte mismatch: {OUTPUT}")
        action = "checked"
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(data)
        action = "wrote"
    print(f"{action} {OUTPUT}: bytes={len(data)} sha256={sha256_bytes(data)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
