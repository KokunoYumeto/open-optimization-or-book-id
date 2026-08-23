#!/usr/bin/env python3
"""Build deterministic modular-backend exports for the R017/O018 lane.

The canonical authored inputs are backend/input/backend-input.json and its
schema-versioned additive full-corpus supplement.  This script uses only the
Python standard library.  It refuses source-hash drift, supports explicit
target-hash guards, segments TeX without changing it, closure-inventories the
bounded O018 lab trees, emits JSON/JSONL/CSV projections, validates every
schema and reference, and compares a second run byte-for-byte with disk.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_VERSION = "0.1.0"
OUTPUT_SCHEMA_NAME = "interlanguage.modular-backend"
COLLECTIONS = (
    "programs",
    "courses",
    "resources",
    "editions",
    "units",
    "concepts",
    "segments",
    "terms",
    "assets",
    "relations",
    "rights",
    "corrections",
    "qa_events",
    "artifacts",
)
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEADING_RE = re.compile(
    r"\\(chapter|section|subsection|subsubsection)(\*)?(?:\[[^\]\n]*\])?\{"
)
BEGIN_RE = re.compile(
    r"\\begin\{(outcome|general|definition|example|examplewithallcode|casestudybox|"
    r"learningcheckpoint|tryit|table|figure|wrapfigure|equation|ex|solution)\}"
)
EXSOL_RE = re.compile(r"\\exsol\{")
CAPTION_FIGURE_RE = re.compile(r"\\captionof\{figure\}\{")
ITEM_EXERCISE_RE = re.compile(
    r"\\item(?:\s*\[[^\]]*\])?\s*\\label\{(ex:[^}]+)\}"
)
CHECKPOINT_ANSWER_RE = re.compile(
    r"\\noindent\s*\\textbf\{\\Cref\{([^}]+)\}\}"
)
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\ref\{([^}]+)\}")
ASSET_REF_RE = re.compile(
    r"\\(?:altincludegraphics|includegraphics|includegraphictikz|"
    r"includefigurestatic|includefiguretikz|refincludefiguretikz)"
    r"(?:\[[^\]]*\])*\{([^}]+)\}"
)
LINK_RE = re.compile(r"\\(?:href|url)\{([^}]+)\}")


def canonical_json(value: Any, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (text + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_manifest(path: Path) -> list[dict[str, Any]]:
    """Return a deterministic, cache-free manifest for one bounded lab tree."""
    rows: list[dict[str, Any]] = []
    for candidate in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(path)
        if "__pycache__" in relative.parts or candidate.suffix == ".pyc":
            continue
        rows.append(
            {
                "path": relative.as_posix(),
                "bytes": candidate.stat().st_size,
                "sha256": sha256_file(candidate),
            }
        )
    return rows


def stable_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def natural_identifier_key(value: str) -> tuple[Any, ...]:
    return tuple(int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value))


def merge_machine_backend_evidence(
    result: dict[str, Any],
    supplement: dict[str, Any],
    evidence: dict[str, Any],
    lane_root: Path,
) -> None:
    """Verify and merge the bounded machine/backend evidence receipt.

    Existing asset IDs, hashes, target guards, statuses, and meanings are
    preserved.  The receipt enriches those records with explicit platform and
    distribution facts, adds only the missing authority witnesses, and binds
    the three separately frozen gitlink archives as first-class artifacts.
    """
    binding = supplement.get("machine_backend_evidence")
    if not isinstance(binding, dict):
        raise ValueError("full-corpus supplement lacks machine_backend_evidence binding")
    if evidence.get("schema_name") != "interlanguage.machine-backend-evidence":
        raise ValueError("unexpected machine-backend evidence schema name")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected machine-backend evidence schema version")
    if evidence.get("authority", {}).get("root") != result["path_roots"]["authority"]:
        raise ValueError("machine-backend evidence authority root does not match backend input")

    assertions = evidence.get("inventory_assertions", {})
    expected_assertions = {
        "operational_non_macro_xlsx": 19,
        "optimization_notebook_pulp": 21,
        "optimization_notebook_gurobi": 21,
        "instructional_notebook_networkx": 2,
        "total_machine_witnesses": 63,
        "submodule_archives": 3,
    }
    if assertions != expected_assertions:
        raise ValueError(f"machine-backend inventory assertion drift: {assertions}")

    evidence_artifact_id = "artifact.backend.machine-backend-evidence"
    result["artifacts"].append(
        {
            "id": evidence_artifact_id,
            "artifact_type": "machine_backend_evidence_receipt",
            "path": binding["path"],
            "bytes": binding["bytes"],
            "sha256": binding["sha256"],
            "verify_local": True,
            "toolchain": (
                "scripts/build_machine_backend_evidence.py; Python standard library"
            ),
            "build_receipt": (
                "Schema-validated authority, platform, target/public distribution, "
                "and O018 mapping evidence."
            ),
            "status": "verified",
        }
    )

    visualization = evidence["visualization_runtime_closure"]
    visualization_target_root = safe_join(lane_root, result["path_roots"]["target"])
    visualization_existing = {row["id"]: row for row in result["assets"]}
    visualization_ids: list[str] = []
    visualization_identities: list[dict[str, Any]] = []
    for row in visualization["files"]:
        identifier = row["asset_id"]
        target_path = safe_join(visualization_target_root, row["target_path"])
        if not target_path.is_file():
            raise FileNotFoundError(f"missing visualization runtime file: {target_path}")
        actual_identity = {
            "path": row["target_path"],
            "bytes": target_path.stat().st_size,
            "sha256": sha256_file(target_path),
        }
        if actual_identity["bytes"] != row["bytes"] or actual_identity["sha256"] != row["sha256"]:
            raise ValueError(f"visualization runtime identity drift for {identifier}")
        visualization_identities.append(actual_identity)
        existing = visualization_existing.get(identifier)
        if row["existing_backend_record"] != (existing is not None):
            raise ValueError(f"visualization existing-record drift for {identifier}")
        if existing is not None:
            if existing.get("target_path") != row["target_path"]:
                raise ValueError(f"visualization target path drift for {identifier}")
            if existing.get("expected_target_sha256") != row["sha256"]:
                raise ValueError(f"visualization target guard drift for {identifier}")
            if existing.get("asset_type") != row["asset_type"]:
                raise ValueError(f"visualization asset semantics drift for {identifier}")
            if existing.get("rights_component_id") != row["rights_component_id"]:
                raise ValueError(f"visualization rights semantics drift for {identifier}")
            if existing.get("status") != row["status"]:
                raise ValueError(f"visualization status drift for {identifier}")
            seed = existing
        else:
            seed = {
                "id": identifier,
                "asset_type": row["asset_type"],
                "source_path": None,
                "target_path": row["target_path"],
                "expected_target_sha256": row["sha256"],
                "rights_component_id": row["rights_component_id"],
                "status": row["status"],
            }
            result["assets"].append(seed)
            visualization_existing[identifier] = seed
        seed["visualization_runtime_closure_role"] = row["closure_role"]
        seed["runtime_closure_evidence_artifact_id"] = evidence_artifact_id
        seed["distribution_disposition"] = (
            "present_in_target_tree; public shipment not asserted until release rebuild"
        )
        visualization_ids.append(identifier)
    visualization_identities.sort(key=lambda row: row["path"])
    actual_visualization_closure = (
        len(visualization_identities),
        sum(row["bytes"] for row in visualization_identities),
        sha256_bytes(canonical_json(visualization_identities)),
    )
    declared_visualization_closure = (
        visualization["file_count"],
        visualization["closure_bytes"],
        visualization["closure_sha256"],
    )
    if actual_visualization_closure != declared_visualization_closure:
        raise ValueError(
            "visualization runtime closure drift: "
            f"{actual_visualization_closure} != {declared_visualization_closure}"
        )
    for generated in visualization["generated_directories"]:
        generated_path = safe_join(visualization_target_root, generated["path"])
        if generated_path.exists():
            raise ValueError(
                f"generated visualization directory must remain absent: {generated_path}"
            )
    result["qa_events"].append(
        {
            "id": "qa.r017.visualization-runtime-closure",
            "qa_type": "offline_javascript_runtime_closure",
            "result": "pass",
            "witness": {
                "file_count": visualization["file_count"],
                "closure_bytes": visualization["closure_bytes"],
                "closure_sha256": visualization["closure_sha256"],
                "commands": visualization["qa_commands"],
                "generated_directories": visualization["generated_directories"],
                "adverse_ledger_event_id": visualization["adverse_ledger_event_id"],
                "public_distribution_disposition": (
                    "target closure verified; public shipment deferred to release rebuild"
                ),
            },
            "affected_ids": sorted(visualization_ids) + [evidence_artifact_id],
            "status": "complete",
        }
    )

    archive_ids: list[str] = []
    archive_witness: list[dict[str, Any]] = []
    for row in evidence["submodule_archives"]:
        archive = safe_join(lane_root, row["archive_path"])
        extracted = safe_join(lane_root, row["extracted_path"])
        if not archive.is_file() or not extracted.is_dir():
            raise FileNotFoundError(
                f"missing submodule archive/extraction evidence for {row['repository']}"
            )
        if archive.stat().st_size != row["archive_bytes"]:
            raise ValueError(f"submodule archive byte drift for {row['repository']}")
        if sha256_file(archive) != row["archive_sha256"]:
            raise ValueError(f"submodule archive hash drift for {row['repository']}")
        with zipfile.ZipFile(archive) as handle:
            entries = handle.infolist()
            file_entries = [item for item in entries if not item.is_dir()]
            actual_archive_values = (
                len(entries),
                len(file_entries),
                sum(item.file_size for item in file_entries),
            )
        declared_archive_values = (
            row["archive_entry_count"],
            row["archive_file_count"],
            row["archive_uncompressed_file_bytes"],
        )
        if actual_archive_values != declared_archive_values:
            raise ValueError(
                f"submodule archive member drift for {row['repository']}: "
                f"{actual_archive_values} != {declared_archive_values}"
            )
        extracted_manifest = directory_manifest(extracted)
        actual_extracted_values = (
            len(extracted_manifest),
            sum(item["bytes"] for item in extracted_manifest),
            sha256_bytes(canonical_json(extracted_manifest)),
        )
        declared_extracted_values = (
            row["extracted_file_count"],
            row["extracted_file_bytes"],
            row["extracted_closure_sha256"],
        )
        if actual_extracted_values != declared_extracted_values:
            raise ValueError(
                f"submodule extracted closure drift for {row['repository']}: "
                f"{actual_extracted_values} != {declared_extracted_values}"
            )
        artifact = {
            "id": row["id"],
            "artifact_type": "frozen_gitlink_source_archive",
            "path": row["archive_path"],
            "bytes": row["archive_bytes"],
            "sha256": row["archive_sha256"],
            "verify_local": True,
            "toolchain": "ZIP archive; independently extracted local authority closure",
            "build_receipt": binding["path"],
            "repository": row["repository"],
            "commit": row["commit"],
            "archive_entry_count": row["archive_entry_count"],
            "archive_file_count": row["archive_file_count"],
            "archive_uncompressed_file_bytes": row[
                "archive_uncompressed_file_bytes"
            ],
            "extracted_path": row["extracted_path"],
            "extracted_file_count": row["extracted_file_count"],
            "extracted_file_bytes": row["extracted_file_bytes"],
            "extracted_closure_sha256": row["extracted_closure_sha256"],
            "build_admission_disposition": row["build_admission_disposition"],
            "status": "frozen_authority_only",
        }
        result["artifacts"].append(artifact)
        archive_ids.append(row["id"])
        archive_witness.append(
            {
                "id": row["id"],
                "repository": row["repository"],
                "commit": row["commit"],
                "archive_file_count": row["archive_file_count"],
                "archive_bytes": row["archive_bytes"],
                "archive_sha256": row["archive_sha256"],
                "archive_uncompressed_file_bytes": row[
                    "archive_uncompressed_file_bytes"
                ],
                "extracted_closure_sha256": row["extracted_closure_sha256"],
                "build_admission_disposition": row["build_admission_disposition"],
            }
        )
        result["relations"].append(
            {
                "id": f"relation.evidenced-by.{row['id']}.{evidence_artifact_id}",
                "relation_type": "evidenced-by",
                "from_id": row["id"],
                "to_id": evidence_artifact_id,
                "status": "active",
            }
        )
    result["qa_events"].append(
        {
            "id": "qa.backend.submodule-archive-evidence",
            "qa_type": "authority_closure",
            "result": "pass",
            "witness": archive_witness,
            "affected_ids": archive_ids + [evidence_artifact_id],
            "status": "complete",
        }
    )

    authority_root = safe_join(lane_root, result["path_roots"]["authority"])
    target_root = safe_join(lane_root, result["path_roots"]["target"])
    existing_by_id = {row["id"]: row for row in result["assets"]}
    existing_by_source = {
        row["source_path"]: row["id"]
        for row in result["assets"]
        if row.get("source_path")
    }
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    kind_counts: defaultdict[str, int] = defaultdict(int)
    distribution_counts: defaultdict[str, int] = defaultdict(int)
    o018_counts: defaultdict[str, int] = defaultdict(int)
    machine_ids: list[str] = []
    metadata_omit = {
        "id",
        "source_path",
        "bytes",
        "sha256",
        "target_path",
        "rights_component_id",
        "status",
    }

    def check_presence(
        owner_id: str, presence: dict[str, Any], root: Path, label: str
    ) -> None:
        relative = presence.get("path")
        candidate = safe_join(root, relative) if relative else None
        actual_present = bool(candidate and candidate.is_file())
        if actual_present != presence["present"]:
            raise ValueError(f"{owner_id} {label} presence drift")
        if actual_present and candidate is not None:
            if candidate.stat().st_size != presence["bytes"]:
                raise ValueError(f"{owner_id} {label} byte drift")
            if sha256_file(candidate) != presence["sha256"]:
                raise ValueError(f"{owner_id} {label} hash drift")

    for row in evidence["machine_witnesses"]:
        identifier = row["id"]
        source_relative = row["source_path"]
        if identifier in seen_ids or source_relative in seen_paths:
            raise ValueError(f"duplicate machine witness {identifier}/{source_relative}")
        seen_ids.add(identifier)
        seen_paths.add(source_relative)
        source_path = safe_join(authority_root, source_relative)
        if not source_path.is_file():
            raise FileNotFoundError(f"missing machine authority witness: {source_path}")
        if source_path.stat().st_size != row["bytes"]:
            raise ValueError(f"machine witness byte drift for {identifier}")
        if sha256_file(source_path) != row["sha256"]:
            raise ValueError(f"machine witness hash drift for {identifier}")
        check_presence(
            identifier,
            row["authority_witness_target_presence"],
            target_root,
            "authority-target",
        )
        check_presence(
            identifier,
            row["localized_derivative_target_presence"],
            target_root,
            "localized-target",
        )

        existing = existing_by_id.get(identifier)
        if row["existing_backend_record"] != (existing is not None):
            raise ValueError(f"machine witness existing-record drift for {identifier}")
        if existing is not None:
            if existing.get("source_path") != source_relative:
                raise ValueError(f"existing source path changed for {identifier}")
            if existing.get("source_sha256") != row["sha256"]:
                raise ValueError(f"existing source hash changed for {identifier}")
            if existing.get("target_path") != row["target_path"]:
                raise ValueError(f"existing target semantics changed for {identifier}")
            if existing.get("rights_component_id") != row["rights_component_id"]:
                raise ValueError(f"existing rights semantics changed for {identifier}")
            if existing.get("status") != row["status"]:
                raise ValueError(f"existing status semantics changed for {identifier}")
            seed = existing
        else:
            if source_relative in existing_by_source:
                raise ValueError(
                    f"machine witness path already belongs to {existing_by_source[source_relative]}"
                )
            asset_type = (
                "source_xlsx_workbook"
                if row["witness_kind"] == "operational_non_macro_xlsx"
                else "source_notebook"
            )
            seed = {
                "id": identifier,
                "asset_type": asset_type,
                "source_path": source_relative,
                "target_path": None,
                "source_sha256": row["sha256"],
                "rights_component_id": row["rights_component_id"],
                "status": row["status"],
            }
            result["assets"].append(seed)
            existing_by_id[identifier] = seed
            existing_by_source[source_relative] = identifier

        for key, value in row.items():
            if key not in metadata_omit:
                if key in seed and seed[key] != value:
                    raise ValueError(f"machine witness metadata conflict {identifier}.{key}")
                seed[key] = value
        seed["authority_inventory_bytes"] = row["bytes"]
        seed["authority_inventory_sha256"] = row["sha256"]
        seed["machine_backend_evidence_artifact_id"] = evidence_artifact_id

        kind_counts[row["witness_kind"]] += 1
        distribution_counts[row["distribution_disposition"]] += 1
        o018_counts[row["o018_pyomo_highs"]["disposition"]] += 1
        machine_ids.append(identifier)

    if dict(kind_counts) != {
        "operational_non_macro_xlsx": 19,
        "optimization_notebook_gurobi": 21,
        "optimization_notebook_pulp": 21,
        "instructional_notebook_networkx": 2,
    }:
        raise ValueError(f"machine witness kind-count drift: {dict(kind_counts)}")
    result["qa_events"].append(
        {
            "id": "qa.backend.machine-witness-inventory",
            "qa_type": "machine_dependency_inventory",
            "result": "pass",
            "witness": {
                "control_artifact_id": evidence_artifact_id,
                "kind_counts": dict(sorted(kind_counts.items())),
                "distribution_disposition_counts": dict(
                    sorted(distribution_counts.items())
                ),
                "o018_disposition_counts": dict(sorted(o018_counts.items())),
                "classification_contract": (
                    "Authority, target-tree, and current public-source-package "
                    "presence are distinct; target-pruned witnesses remain "
                    "authority-only and are never described as shipped."
                ),
            },
            "affected_ids": sorted(machine_ids) + [evidence_artifact_id],
            "status": "complete",
        }
    )


def merge_full_corpus_supplement(
    source: dict[str, Any],
    supplement: dict[str, Any],
    machine_evidence: dict[str, Any],
    lane_root: Path,
) -> dict[str, Any]:
    """Merge the additive full-corpus inventory into the v0 canonical input.

    The original input remains a valid interoperability-envelope document.
    This compact supplement makes the later R017 closure and the six complete
    O018 lab trees reviewable without duplicating generated per-file metadata.
    The returned document is validated against the unchanged v0 input schema.
    """
    if supplement.get("schema_name") != "interlanguage.modular-backend-supplement":
        raise ValueError("unexpected backend supplement schema name")
    if supplement.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected backend supplement schema version")
    result = json.loads(json.dumps(source))
    result["snapshot_at"] = supplement["snapshot_at"]
    final_bindings = supplement.get("binding_state") == "final"

    merge_machine_backend_evidence(result, supplement, machine_evidence, lane_root)

    supplement_updates = supplement.get("updates", {})
    result["concepts"].extend(supplement_updates.get("concept_additions", []))
    result["terms"].extend(supplement_updates.get("term_additions", []))
    for declared_collection, patches in supplement_updates.items():
        if declared_collection in {"concept_additions", "term_additions"}:
            continue
        collection = "terms" if declared_collection == "term_status_updates" else declared_collection
        if collection not in result or not isinstance(result[collection], list):
            raise ValueError(f"supplement updates unknown collection {declared_collection!r}")
        by_id = {record["id"]: record for record in result[collection]}
        for patch in patches:
            identifier = patch.get("id")
            if identifier not in by_id:
                raise ValueError(f"supplement update references missing {collection} id {identifier!r}")
            effective_patch = dict(patch)
            if not final_bindings and "expected_target_sha256" in effective_patch:
                effective_patch["expected_target_sha256"] = None
            by_id[identifier].update(effective_patch)

    for collection, additions in supplement.get("append", {}).items():
        if collection not in result or not isinstance(result[collection], list):
            raise ValueError(f"supplement appends to unknown collection {collection!r}")
        result[collection].extend(additions)

    if not final_bindings:
        # Production may still be changing target bytes while this structural
        # supplement is developed.  Provisional runs expose every current hash
        # as unbound; the release gate switches to ``final`` and requires every
        # exact value.  Source-authority guards are never relaxed.
        for seed in result["file_units"] + result["assets"]:
            if seed.get("target_path"):
                seed["expected_target_sha256"] = None

    for item in supplement.get("concept_terms", []):
        concept_id = f"concept.{item['slug']}"
        result["concepts"].append(
            {
                "id": concept_id,
                "name_en": item["name_en"],
                "prerequisite_concept_ids": item.get("prerequisite_concept_ids", []),
                "status": "active",
            }
        )
        result["terms"].append(
            {
                "id": f"term.{item['slug']}.id",
                "concept_id": concept_id,
                "source_locale": "en",
                "source_term": item["name_en"],
                "target_locale": "id-ID",
                "preferred": item["preferred"],
                "variants": item.get("variants", []),
                "rejected": item.get("rejected", []),
                "scope": item.get("scope", "R017/O018 Book 1 full-corpus edition"),
                "register": "academic",
                "evidence": item.get("evidence", "Full-corpus id-ID terminology audit"),
                "status": "approved",
            }
        )

    for item in supplement.get("r017_file_units", []):
        result["file_units"].append(
            {
                "id": item["id"],
                "unit_type": item["unit_type"],
                "parent_id": item["parent_id"],
                "order": item["order"],
                "source_path": item["path"],
                "target_path": item["path"],
                "source_sha256": item["source_sha256"],
                "expected_target_sha256": (
                    item.get("expected_target_sha256") if final_bindings else None
                ),
                "alignment_mode": item.get("alignment_mode", "target_projection"),
                "concept_ids": item.get("concept_ids", []),
                "prerequisite_concept_ids": item.get("prerequisite_concept_ids", []),
                "rights_component_id": item.get("rights_component_id", "rights.r017.content"),
            }
        )

    authority_root = safe_join(lane_root, result["path_roots"]["authority"])
    target_root = safe_join(lane_root, result["path_roots"]["target"])
    for bundle in supplement.get("r017_asset_directories", []):
        source_base = safe_join(authority_root, bundle["path"])
        target_base = safe_join(target_root, bundle["path"])
        source_rows = directory_manifest(source_base)
        target_rows = directory_manifest(target_base)
        source_closure_hash = sha256_bytes(canonical_json(source_rows))
        target_closure_hash = sha256_bytes(canonical_json(target_rows))
        if (
            len(source_rows) != bundle["source_file_count"]
            or sum(row["bytes"] for row in source_rows) != bundle["source_closure_bytes"]
            or source_closure_hash != bundle["source_closure_sha256"]
        ):
            raise ValueError(f"R017 source asset closure drift for {bundle['key']}")
        if final_bindings and (
            len(target_rows) != bundle["target_file_count"]
            or sum(row["bytes"] for row in target_rows) != bundle["target_closure_bytes"]
            or target_closure_hash != bundle["target_closure_sha256"]
        ):
            raise ValueError(
                f"R017 target asset closure drift for {bundle['key']}: "
                f"{len(target_rows)}/{sum(row['bytes'] for row in target_rows)}/{target_closure_hash}"
            )
        source_by_path = {row["path"]: row for row in source_rows}
        existing_target_paths = {
            seed.get("target_path") for seed in result["assets"] if seed.get("target_path")
        }
        affected_ids: list[str] = []
        for row in target_rows:
            target_path = f"{bundle['path'].rstrip('/')}/{row['path']}"
            if target_path in existing_target_paths:
                continue
            identifier = f"asset.r017.full.{bundle['key']}.{stable_slug(row['path'])}"
            source_row = source_by_path.get(row["path"])
            suffix = PurePosixPath(row["path"]).suffix.lower()
            asset_type = {
                ".png": "figure_png",
                ".jpg": "figure_jpeg",
                ".jpeg": "figure_jpeg",
                ".pdf": "figure_pdf",
                ".svg": "figure_svg",
                ".tex": "figure_source_tex",
                ".csv": "structured_data_csv",
                ".json": "structured_data_json",
            }.get(suffix, "book_asset")
            seed: dict[str, Any] = {
                "id": identifier,
                "asset_type": asset_type,
                "target_path": target_path,
                "expected_target_sha256": row["sha256"] if final_bindings else None,
                "rights_component_id": bundle.get("rights_overrides", {}).get(
                    row["path"], bundle["rights_component_id"]
                ),
                "redistribution_status": "included",
                "status": "verified" if final_bindings else "target_hash_unbound",
            }
            if source_row is not None:
                seed["source_path"] = target_path
                seed["source_sha256"] = source_row["sha256"]
            result["assets"].append(seed)
            existing_target_paths.add(target_path)
            affected_ids.append(identifier)
        result["qa_events"].append(
            {
                "id": f"qa.r017.asset-closure.{bundle['key']}",
                "qa_type": "asset_closure",
                "result": "pass" if final_bindings else "unbound",
                "witness": {
                    "path": bundle["path"],
                    "source_file_count": len(source_rows),
                    "source_closure_bytes": sum(row["bytes"] for row in source_rows),
                    "source_closure_sha256": source_closure_hash,
                    "target_file_count": len(target_rows),
                    "target_closure_bytes": sum(row["bytes"] for row in target_rows),
                    "target_closure_sha256": target_closure_hash,
                },
                "affected_ids": affected_ids,
                "status": "complete" if final_bindings else "open",
            }
        )

    if final_bindings:
        final_pdf = supplement.get("final_pdf")
        if not isinstance(final_pdf, dict):
            raise ValueError("final binding state requires final_pdf evidence")
        result["artifacts"].extend(
            [
                {
                    "id": "artifact.r017.book1.id-id.final-pdf",
                    "artifact_type": "reader_pdf",
                    "path": final_pdf["path"],
                    "bytes": final_pdf["bytes"],
                    "sha256": final_pdf["sha256"],
                    "toolchain": final_pdf["toolchain"],
                    "build_receipt": final_pdf["qa_report_path"],
                    "verify_local": True,
                    "rights_component_ids": [
                        "rights.r017.content",
                        "rights.thirdparty.lyryx-kuttler",
                        "rights.thirdparty.lippman",
                        "rights.thirdparty.lippman-sam-beebe",
                        "rights.thirdparty.knapsack-wikimedia",
                        "rights.thirdparty.konigsberg-wikimedia",
                        "rights.thirdparty.petersen-public-domain"
                    ],
                    "status": "visually_checked"
                },
                {
                    "id": "artifact.r017.book1.id-id.clean-replay-pdf",
                    "artifact_type": "clean_replay_reader_pdf",
                    "path": final_pdf["replay_path"],
                    "bytes": final_pdf["replay_bytes"],
                    "sha256": final_pdf["replay_sha256"],
                    "toolchain": final_pdf["toolchain"],
                    "build_receipt": final_pdf["qa_report_path"],
                    "verify_local": True,
                    "rights_component_ids": ["rights.r017.content"],
                    "status": "byte_identical_replay"
                },
                {
                    "id": "artifact.r017.book1.id-id.final-pdf-qa",
                    "artifact_type": "pdf_qa_report",
                    "path": final_pdf["qa_report_path"],
                    "bytes": final_pdf["qa_report_bytes"],
                    "sha256": final_pdf["qa_report_sha256"],
                    "toolchain": "qa/book1-final-verify.py; pypdf; Poppler",
                    "build_receipt": final_pdf["qa_report_path"],
                    "verify_local": True,
                    "rights_component_ids": ["rights.r017.code"],
                    "status": "verified"
                },
                {
                    "id": "artifact.r017.book1.id-id.build-entrypoint",
                    "artifact_type": "deterministic_build_script",
                    "path": final_pdf["build_entrypoint_path"],
                    "bytes": final_pdf["build_entrypoint_bytes"],
                    "sha256": final_pdf["build_entrypoint_sha256"],
                    "toolchain": "PowerShell",
                    "build_receipt": final_pdf["qa_report_path"],
                    "verify_local": True,
                    "rights_component_ids": ["rights.r017.code"],
                    "status": "verified"
                }
            ]
        )
        for build_artifact in final_pdf.get("build_artifacts", []):
            result["artifacts"].append(
                {
                    "id": build_artifact["id"],
                    "artifact_type": build_artifact["artifact_type"],
                    "path": build_artifact["path"],
                    "bytes": build_artifact["bytes"],
                    "sha256": build_artifact["sha256"],
                    "toolchain": build_artifact["toolchain"],
                    "build_receipt": final_pdf["qa_report_path"],
                    "verify_local": True,
                    "rights_component_ids": build_artifact["rights_component_ids"],
                    "status": "verified",
                }
            )
        result["relations"].extend(
            [
                {
                    "id": "relation.generated-by.artifact.r017.book1.id-id.final-pdf.artifact.r017.book1.id-id.build-entrypoint",
                    "relation_type": "generated-by",
                    "from_id": "artifact.r017.book1.id-id.final-pdf",
                    "to_id": "artifact.r017.book1.id-id.build-entrypoint",
                    "status": "active",
                },
                {
                    "id": "relation.reproduces.artifact.r017.book1.id-id.clean-replay-pdf.artifact.r017.book1.id-id.final-pdf",
                    "relation_type": "reproduces",
                    "from_id": "artifact.r017.book1.id-id.clean-replay-pdf",
                    "to_id": "artifact.r017.book1.id-id.final-pdf",
                    "status": "active",
                },
                {
                    "id": "relation.evidenced-by.artifact.r017.book1.id-id.final-pdf.artifact.r017.book1.id-id.final-pdf-qa",
                    "relation_type": "evidenced-by",
                    "from_id": "artifact.r017.book1.id-id.final-pdf",
                    "to_id": "artifact.r017.book1.id-id.final-pdf-qa",
                    "status": "active",
                },
            ]
        )
        for build_artifact in final_pdf.get("build_artifacts", []):
            owner_id = build_artifact.get("owner_unit_id")
            if owner_id:
                result["relations"].append(
                    {
                        "id": f"relation.generated-as.{owner_id}.{build_artifact['id']}",
                        "relation_type": "generated-as",
                        "from_id": owner_id,
                        "to_id": build_artifact["id"],
                        "status": "active",
                    }
                )
            result["relations"].append(
                {
                    "id": f"relation.depends-on.artifact.r017.book1.id-id.final-pdf.{build_artifact['id']}",
                    "relation_type": "depends-on",
                    "from_id": "artifact.r017.book1.id-id.final-pdf",
                    "to_id": build_artifact["id"],
                    "status": "active",
                }
            )
        result["qa_events"].append(
            {
                "id": "qa.r017.book1.final-pdf",
                "qa_type": "build_accessibility_visual",
                "result": "pass",
                "witness": final_pdf,
                "affected_ids": [
                    "unit.r017.book1",
                    "artifact.r017.book1.id-id.final-pdf",
                    "artifact.r017.book1.id-id.clean-replay-pdf",
                    "artifact.r017.book1.id-id.build-entrypoint",
                    "artifact.r017.book1.id-id.final-pdf-qa"
                ] + [item["id"] for item in final_pdf.get("build_artifacts", [])],
                "status": "complete"
            }
        )

    for lab in supplement.get("o018_labs", []):
        lab_key = lab["key"]
        lab_id = f"unit.o018.lab.{lab_key}"
        directory = f"o018-open-solver-lab/{lab['directory']}"
        lab_root = safe_join(target_root, directory)
        if not lab_root.is_dir():
            raise FileNotFoundError(f"missing O018 lab directory: {lab_root}")
        manifest_rows = directory_manifest(lab_root)
        closure_hash = sha256_bytes(canonical_json(manifest_rows))
        if len(manifest_rows) != lab["file_count"]:
            raise ValueError(
                f"O018 {lab_key} closure count drift: expected {lab['file_count']}, "
                f"actual {len(manifest_rows)}"
            )
        if sum(row["bytes"] for row in manifest_rows) != lab["closure_bytes"]:
            raise ValueError(f"O018 {lab_key} closure byte-count drift")
        if closure_hash != lab["closure_sha256"]:
            raise ValueError(
                f"O018 {lab_key} closure hash drift: expected {lab['closure_sha256']}, "
                f"actual {closure_hash}"
            )
        rows_by_path = {row["path"]: row for row in manifest_rows}
        result["root_units"].append(
            {
                "id": lab_id,
                "unit_type": "computational_lab_collection",
                "resource_id": "resource.o018.open-solver-lab",
                "edition_id": "edition.o018.id-id.draft",
                "parent_id": "unit.o018.lab",
                "order": lab["order"],
                "title_target": lab["title_target"],
                "locale": "id-ID",
                "translation_state": "mathematically_reviewed",
                "concept_ids": lab["concept_ids"],
                "prerequisite_concept_ids": lab.get("prerequisite_concept_ids", []),
                "rights_component_id": "rights.o018.prose-data",
                "additional_rights_component_ids": ["rights.o018.code"],
                "status": "verified",
            }
        )

        asset_ids: list[str] = []
        for row in manifest_rows:
            relative = row["path"]
            asset_id = f"asset.o018.{lab_key}.{stable_slug(relative)}"
            asset_ids.append(asset_id)
            is_code = relative.endswith(".py") or relative == "LICENSE-CODE.txt"
            name = PurePosixPath(relative).name
            if name == "results.json":
                asset_type = "deterministic_result_json"
            elif name == "verification-receipt.json":
                asset_type = "verification_receipt_json"
            elif name == "expected-results.json":
                asset_type = "expected_result_contract"
            elif name == "data.json":
                asset_type = "structured_model_data"
            elif relative.startswith("plots/") and relative.endswith(".svg"):
                asset_type = "accessible_svg_plot"
            elif relative.endswith(".py"):
                asset_type = "python_source"
            elif relative.endswith(".md"):
                asset_type = "markdown_content"
            elif name == "LICENSE-CODE.txt":
                asset_type = "license_text"
            else:
                asset_type = "lab_component"
            result["assets"].append(
                {
                    "id": asset_id,
                    "asset_type": asset_type,
                    "target_path": f"{directory}/{relative}",
                    "expected_target_sha256": row["sha256"],
                    "rights_component_id": "rights.o018.code" if is_code else "rights.o018.prose-data",
                    "redistribution_status": "included",
                    "status": "verified",
                }
            )

        for order, name in enumerate(("README.md", "ATTRIBUTION.md"), start=1):
            row = rows_by_path.get(name)
            if row is None:
                raise ValueError(f"O018 {lab_key} lacks required {name}")
            result["native_file_units"].append(
                {
                    "id": f"unit.o018.lab.{lab_key}.{'readme' if name == 'README.md' else 'attribution'}",
                    "unit_type": "laboratory_guide" if name == "README.md" else "attribution",
                    "resource_id": "resource.o018.open-solver-lab",
                    "edition_id": "edition.o018.id-id.draft",
                    "parent_id": lab_id,
                    "order": order,
                    "content_path": f"{directory}/{name}",
                    "expected_content_sha256": row["sha256"],
                    "locale": "id-ID",
                    "concept_ids": lab["concept_ids"],
                    "asset_ids": asset_ids,
                    "code_data_refs": [f"{directory}/{item['path']}" for item in manifest_rows],
                    "rights_component_id": "rights.o018.prose-data",
                }
            )

        results_path = lab_root / "results.json"
        receipt_path = lab_root / "verification-receipt.json"
        results_document = load_json(results_path)
        receipt_document = load_json(receipt_path)
        exercise_order = results_document.get("exercise_order") or sorted(
            results_document["exercises"], key=natural_identifier_key
        )
        lab_exercise_ids: list[str] = []
        for order, exercise_identifier in enumerate(exercise_order, start=1):
            exercise = results_document["exercises"][exercise_identifier]
            exercise_id = f"unit.o018.lab.{lab_key}.ex-{stable_slug(exercise_identifier)}"
            lab_exercise_ids.append(exercise_id)
            result["root_units"].append(
                {
                    "id": exercise_id,
                    "unit_type": "computational_lab",
                    "resource_id": "resource.o018.open-solver-lab",
                    "edition_id": "edition.o018.id-id.draft",
                    "parent_id": lab_id,
                    "order": order + 2,
                    "source_local_id": f"exercise-{exercise_identifier}",
                    "source_book_label": exercise.get("book_label"),
                    "title_target": exercise.get("title", exercise_identifier),
                    "locale": "id-ID",
                    "translation_state": "mathematically_reviewed",
                    "concept_ids": lab["concept_ids"],
                    "prerequisite_concept_ids": lab.get("prerequisite_concept_ids", []),
                    "rights_component_id": "rights.o018.prose-data",
                    "status": exercise.get("status", "verified"),
                }
            )

        for name, artifact_type in (
            ("results.json", "deterministic_computation_result"),
            ("verification-receipt.json", "verification_receipt"),
        ):
            row = rows_by_path[name]
            suffix = "results" if name == "results.json" else "verification-receipt"
            result["artifacts"].append(
                {
                    "id": f"artifact.o018.{lab_key}.{suffix}",
                    "artifact_type": artifact_type,
                    "path": f"source/{directory}/{name}",
                    "bytes": row["bytes"],
                    "sha256": row["sha256"],
                    "toolchain": "Python standard library; Pyomo; HiGHS where applicable",
                    "build_receipt": f"source/{directory}/verification-receipt.json",
                    "verify_local": True,
                    "rights_component_ids": ["rights.o018.prose-data", "rights.o018.code"],
                    "status": "verified",
                }
            )
        result["qa_events"].append(
            {
                "id": f"qa.o018.{lab_key}.verified-closure",
                "qa_type": "computation_math_determinism_accessibility",
                "result": "pass",
                "witness": {
                    "directory_manifest": manifest_rows,
                    "directory_closure_sha256": closure_hash,
                    "receipt_verification": receipt_document.get("verification"),
                },
                "affected_ids": [
                    lab_id,
                    f"artifact.o018.{lab_key}.results",
                    f"artifact.o018.{lab_key}.verification-receipt",
                ],
                "status": "complete",
            }
        )

        correction_sources = (
            results_document.get("corrections", [])
            + results_document.get("source_defects", [])
            + results_document.get("upstream_defects", [])
            + results_document.get("source_notes", [])
        )
        for correction in correction_sources:
            correction_identifier = correction["id"]
            recorded_action = correction.get(
                "status", "preserved explicitly in the Indonesian edition or lab evidence"
            )
            if recorded_action == "reported_not_modified":
                recorded_action = (
                    "preserved without source modification and recorded in local evidence only; "
                    "not communicated upstream"
                )
            result["corrections"].append(
                {
                    "id": f"correction.o018.{lab_key}.{stable_slug(correction_identifier)}",
                    "correction_type": correction.get("type", "source_note"),
                    "affected_unit_ids": [lab_id],
                    "source_defect": correction.get("text", correction.get("certificate", correction_identifier)),
                    "target_action": recorded_action,
                    "rationale": correction.get("certificate", correction.get("text", "Explicit source-backed record")),
                    "evidence": correction,
                    "upstream_report_disposition": "not_opened; no author contact during production",
                    "status": "recorded",
                }
            )

        # Preserve executable/evidence topology, not merely an inventory of
        # files.  These relations make a lab or one exercise dependency-closed
        # for later language adaptation.
        for dependency_id in ("dependency.pyomo", "dependency.highs", "dependency.numpy"):
            result["relations"].append(
                {
                    "id": f"relation.depends-on.{lab_id}.{dependency_id}",
                    "relation_type": "depends-on",
                    "from_id": lab_id,
                    "to_id": dependency_id,
                    "status": "active",
                }
            )
        python_asset_ids = [
            f"asset.o018.{lab_key}.{stable_slug(row['path'])}"
            for row in manifest_rows
            if PurePosixPath(row["path"]).suffix.lower() == ".py"
        ]
        for asset_id in python_asset_ids:
            result["relations"].append(
                {
                    "id": f"relation.implemented-by.{lab_id}.{asset_id}",
                    "relation_type": "implemented-by",
                    "from_id": lab_id,
                    "to_id": asset_id,
                    "status": "active",
                }
            )
        results_artifact_id = f"artifact.o018.{lab_key}.results"
        receipt_artifact_id = f"artifact.o018.{lab_key}.verification-receipt"
        for artifact_id in (results_artifact_id, receipt_artifact_id):
            result["relations"].append(
                {
                    "id": f"relation.evidenced-by.{lab_id}.{artifact_id}",
                    "relation_type": "evidenced-by",
                    "from_id": lab_id,
                    "to_id": artifact_id,
                    "status": "active",
                }
            )
        model_asset_id = (
            f"asset.o018.{lab_key}.{stable_slug('model.py')}"
            if "model.py" in rows_by_path
            else None
        )
        runner_asset_id = (
            f"asset.o018.{lab_key}.{stable_slug('run_lab.py')}"
            if "run_lab.py" in rows_by_path
            else None
        )
        tests_asset_id = (
            f"asset.o018.{lab_key}.{stable_slug('test_models.py')}"
            if "test_models.py" in rows_by_path
            else None
        )
        verifier_asset_id = (
            f"asset.o018.{lab_key}.{stable_slug('verify_receipt.py')}"
            if "verify_receipt.py" in rows_by_path
            else None
        )
        if runner_asset_id:
            result["relations"].append(
                {
                    "id": f"relation.generated-by.{results_artifact_id}.{runner_asset_id}",
                    "relation_type": "generated-by",
                    "from_id": results_artifact_id,
                    "to_id": runner_asset_id,
                    "status": "active",
                }
            )
        if tests_asset_id and model_asset_id:
            result["relations"].append(
                {
                    "id": f"relation.verifies.{tests_asset_id}.{model_asset_id}",
                    "relation_type": "verifies",
                    "from_id": tests_asset_id,
                    "to_id": model_asset_id,
                    "status": "active",
                }
            )
        if verifier_asset_id:
            result["relations"].append(
                {
                    "id": f"relation.verifies.{verifier_asset_id}.{receipt_artifact_id}",
                    "relation_type": "verifies",
                    "from_id": verifier_asset_id,
                    "to_id": receipt_artifact_id,
                    "status": "active",
                }
            )
        for exercise_id in lab_exercise_ids:
            result["relations"].append(
                {
                    "id": f"relation.evidenced-by.{exercise_id}.{results_artifact_id}",
                    "relation_type": "evidenced-by",
                    "from_id": exercise_id,
                    "to_id": results_artifact_id,
                    "status": "active",
                }
            )
            if model_asset_id:
                result["relations"].append(
                    {
                        "id": f"relation.implemented-by.{exercise_id}.{model_asset_id}",
                        "relation_type": "implemented-by",
                        "from_id": exercise_id,
                        "to_id": model_asset_id,
                        "status": "active",
                    }
                )

    if final_bindings:
        for correction in result["corrections"]:
            disposition = correction.get("upstream_report_disposition", "")
            if disposition.startswith("hold_until_corpus_complete"):
                correction["prior_upstream_report_disposition"] = disposition
                correction["upstream_report_disposition"] = (
                    "not_opened; user instructed no author contact; retained for local provenance only"
                )

    collections_with_ids = (
        "programs", "courses", "resources", "editions", "root_units", "file_units",
        "native_file_units", "concepts", "terms", "assets", "rights", "corrections",
        "qa_events", "artifacts", "relations",
    )
    for collection in collections_with_ids:
        identifiers = [record["id"] for record in result[collection]]
        duplicate_ids = sorted({identifier for identifier in identifiers if identifiers.count(identifier) > 1})
        if duplicate_ids:
            raise ValueError(f"supplement produced duplicate {collection} IDs: {duplicate_ids}")
    return result


def safe_join(root: Path, relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts:
        raise ValueError(f"unsafe relative path: {relative!r}")
    candidate = root.joinpath(*posix.parts).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"path escapes root: {relative!r}")
    return candidate


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_pointer(root_schema: dict[str, Any], pointer: str) -> Any:
    if not pointer.startswith("#/"):
        raise ValueError(f"only local JSON Schema references are supported: {pointer}")
    node: Any = root_schema
    for part in pointer[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        node = node[key]
    return node


def validate_against_schema(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str = "$",
) -> list[str]:
    """Validate the deliberately small JSON-Schema subset used by this lane."""
    errors: list[str] = []
    if "$ref" in schema:
        return validate_against_schema(value, resolve_pointer(root_schema, schema["$ref"]), root_schema, path)
    if "allOf" in schema:
        for branch in schema["allOf"]:
            errors.extend(validate_against_schema(value, branch, root_schema, path))
        return errors
    if "anyOf" in schema:
        branches = [validate_against_schema(value, branch, root_schema, path) for branch in schema["anyOf"]]
        if all(branch for branch in branches):
            errors.append(f"{path}: value does not match anyOf")
        return errors
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    expected_type = schema.get("type")
    type_ok = True
    if expected_type == "object":
        type_ok = isinstance(value, dict)
    elif expected_type == "array":
        type_ok = isinstance(value, list)
    elif expected_type == "string":
        type_ok = isinstance(value, str)
    elif expected_type == "integer":
        type_ok = isinstance(value, int) and not isinstance(value, bool)
    elif expected_type == "number":
        type_ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected_type == "boolean":
        type_ok = isinstance(value, bool)
    elif expected_type == "null":
        type_ok = value is None
    if expected_type and not type_ok:
        return [f"{path}: expected {expected_type}, got {type(value).__name__}"]
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected property {key!r}")
        for key, child in properties.items():
            if key in value:
                errors.extend(validate_against_schema(value[key], child, root_schema, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate_against_schema(item, schema["items"], root_schema, f"{path}[{index}]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string shorter than {schema['minLength']}")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{path}: value does not match {schema['pattern']!r}")
    return errors


def validate_schema_document(schema: dict[str, Any], name: str) -> None:
    required = {"$schema", "$id", "type", "required", "properties"}
    missing = sorted(required - schema.keys())
    if missing:
        raise ValueError(f"{name}: schema document missing {missing}")
    if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError(f"{name}: unexpected JSON Schema dialect")
    if schema["type"] != "object" or not isinstance(schema["properties"], dict):
        raise ValueError(f"{name}: root schema must describe an object")


def read_tex(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def nonempty_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    cursor = 0
    for raw in re.split(r"\n[ \t]*\n+", text):
        stripped = raw.strip()
        if not stripped:
            cursor += len(raw)
            continue
        start = text.find(raw, cursor)
        if start < 0:
            start = cursor
        end = start + len(raw)
        start_line = text.count("\n", 0, start) + 1
        end_line = text.count("\n", 0, end) + 1
        blocks.append({"text": stripped, "line_start": start_line, "line_end": end_line})
        cursor = end
    return blocks


def brace_content(text: str, opening_brace: int) -> tuple[str, int]:
    depth = 0
    escaped = False
    for index in range(opening_brace, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[opening_brace + 1 : index], index + 1
    raise ValueError(f"unclosed brace at character {opening_brace}")


def mask_tex_comments(text: str) -> str:
    """Replace unescaped TeX comments with spaces while preserving offsets."""
    chars = list(text)
    index = 0
    while index < len(text):
        if text[index] == "%":
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and text[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                line_end = text.find("\n", index)
                if line_end < 0:
                    line_end = len(text)
                chars[index:line_end] = " " * (line_end - index)
                index = line_end
                continue
        index += 1
    return "".join(chars)


def strip_tex_for_slug(value: str) -> str:
    value = re.sub(r"\\[A-Za-z@]+\*?", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:48] or "untitled"


def extract_structure(text: str) -> list[dict[str, Any]]:
    scan_text = mask_tex_comments(text)
    events: list[dict[str, Any]] = []
    per_kind: defaultdict[str, int] = defaultdict(int)
    for match in HEADING_RE.finditer(scan_text):
        kind = match.group(1)
        title, end = brace_content(text, match.end() - 1)
        per_kind[kind] += 1
        nearby = scan_text[end : min(len(scan_text), end + 320)]
        label_match = LABEL_RE.search(nearby)
        events.append(
            {
                "position": match.start(),
                "end": end,
                "kind": kind,
                "starred": bool(match.group(2)),
                "ordinal": per_kind[kind],
                "title": title,
                "source_local_id": label_match.group(1) if label_match else None,
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    environment_ordinals: defaultdict[str, int] = defaultdict(int)
    for match in BEGIN_RE.finditer(scan_text):
        env = match.group(1)
        environment_ordinals[env] += 1
        end_marker = f"\\end{{{env}}}"
        env_end = scan_text.find(end_marker, match.end())
        if env_end < 0:
            env_end = min(len(text), match.end() + 2000)
        else:
            env_end += len(end_marker)
        body = text[match.start() : env_end]
        scan_body = scan_text[match.start() : env_end]
        label_match = (
            re.search(r"label=\{([^}]+)\}", scan_body[: min(len(scan_body), 400)])
            if env == "learningcheckpoint"
            else None
        )
        if not label_match:
            label_match = LABEL_RE.search(scan_body)
        title = ""
        if env in {"ex", "general", "definition", "example", "examplewithallcode", "casestudybox"}:
            brace_at = scan_text.find("{", match.end())
            if brace_at >= 0:
                title, _ = brace_content(text, brace_at)
        elif env == "solution":
            ref_match = REF_RE.search(scan_body)
            title = f"solution for {ref_match.group(1)}" if ref_match else "selected solution"
        events.append(
            {
                "position": match.start(),
                "end": env_end,
                "kind": env,
                "starred": False,
                "ordinal": environment_ordinals[env],
                "title": title,
                "source_local_id": label_match.group(1) if label_match else None,
                "solves_source_local_id": (REF_RE.search(scan_body).group(1) if env == "solution" and REF_RE.search(scan_body) else None),
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    manual_solution_ordinal = 0
    for match in EXSOL_RE.finditer(scan_text):
        number, end_number = brace_content(text, match.end() - 1)
        title_open = scan_text.find("{", end_number)
        title, end_title = brace_content(text, title_open)
        stars_open = scan_text.find("{", end_title)
        stars, end_stars = brace_content(text, stars_open)
        manual_solution_ordinal += 1
        exercise_ordinal_match = re.search(r"(\d+)$", number.strip())
        events.append(
            {
                "position": match.start(),
                "end": end_stars,
                "kind": "manualsolution",
                "starred": False,
                "ordinal": manual_solution_ordinal,
                "title": title,
                "source_local_id": f"exsol:{number.strip()}",
                "solves_exercise_ordinal": (
                    int(exercise_ordinal_match.group(1)) if exercise_ordinal_match else None
                ),
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    item_exercise_ordinal = 0
    for match in ITEM_EXERCISE_RE.finditer(scan_text):
        # Some inherited graph-theory exercises are labelled enumerate items
        # rather than ``ex`` environments.  They are still stable exercises
        # and selected solutions/O018 records refer to their labels.  Stop at
        # the next item (or the enclosing enumerate terminator) so the unit
        # hash covers the item without swallowing its siblings.
        next_item_match = re.search(r"\\item\b", scan_text[match.end() :])
        next_item = (
            match.end() + next_item_match.start() if next_item_match else len(text)
        )
        enumerate_end = scan_text.find(r"\end{enumerate}", match.end())
        candidates = [next_item]
        if enumerate_end >= 0:
            candidates.append(enumerate_end)
        item_end = min(candidates)
        item_exercise_ordinal += 1
        body = re.sub(r"\s+", " ", text[match.end() : item_end].strip())
        events.append(
            {
                "position": match.start(),
                "end": item_end,
                "kind": "itemexercise",
                "starred": False,
                "ordinal": item_exercise_ordinal,
                "title": body[:240] or match.group(1),
                "source_local_id": match.group(1),
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    checkpoint_answer_matches = list(CHECKPOINT_ANSWER_RE.finditer(scan_text))
    for ordinal, match in enumerate(checkpoint_answer_matches, start=1):
        answer_end = (
            checkpoint_answer_matches[ordinal].start()
            if ordinal < len(checkpoint_answer_matches)
            else len(text)
        )
        events.append(
            {
                "position": match.start(),
                "end": answer_end,
                "kind": "checkpointanswer",
                "starred": False,
                "ordinal": ordinal,
                "title": f"answer for {match.group(1)}",
                "source_local_id": match.group(1),
                "answers_source_local_id": match.group(1),
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    caption_ordinal = 0
    for match in CAPTION_FIGURE_RE.finditer(scan_text):
        # A captionof figure is a semantic figure even when it is wrapped only
        # in a center environment rather than a LaTeX figure float.
        caption_ordinal += 1
        title, end = brace_content(text, match.end() - 1)
        nearby = scan_text[end : min(len(scan_text), end + 240)]
        label_match = LABEL_RE.search(nearby)
        events.append(
            {
                "position": match.start(),
                "end": end,
                "kind": "captionfigure",
                "starred": False,
                "ordinal": caption_ordinal,
                "title": title,
                "source_local_id": label_match.group(1) if label_match else None,
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    return sorted(events, key=lambda event: (event["position"], event["kind"], event["ordinal"]))


def extract_markdown_headings(text: str) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for match in re.finditer(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$", text):
        headings.append(
            {
                "position": match.start(),
                "end": match.end(),
                "depth": len(match.group(1)),
                "title": match.group(2).strip(),
                "ordinal": len(headings) + 1,
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    return headings


def classify_block(text: str) -> str:
    scan_text = mask_tex_comments(text)
    if "\\begin{ex}" in scan_text or ITEM_EXERCISE_RE.search(scan_text):
        return "exercise"
    if "\\begin{solution}" in scan_text:
        return "solution"
    if "\\begin{figure}" in scan_text or "\\begin{wrapfigure}" in scan_text or "\\captionof{figure}" in scan_text:
        return "figure"
    if HEADING_RE.search(scan_text):
        return "heading_or_structured_prose"
    if "\\begin{equation}" in scan_text or "\\begin{general}" in scan_text or "\\[" in scan_text:
        return "formula_or_model"
    if "\\begin{outcome}" in scan_text:
        return "learning_outcomes"
    return "prose"


def unit_type_for_event(kind: str) -> str:
    if kind in {"ex", "itemexercise"}:
        return "exercise"
    if kind in {"solution", "manualsolution"}:
        return "solution"
    if kind == "checkpointanswer":
        return "answer"
    if kind in {"figure", "wrapfigure", "captionfigure"}:
        return "figure"
    if kind in {"example", "examplewithallcode"}:
        return "example"
    return kind


def enrich(kind: str, seed: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    record = dict(seed)
    record.setdefault("status", "draft")
    record.setdefault("recorded_at", source["snapshot_at"])
    record.setdefault("responsible_workflow", source["responsible_workflow"])
    record.setdefault("supersedes_id", None)
    record["schema_name"] = f"interlanguage.{kind[:-1] if kind.endswith('s') else kind}"
    record["schema_version"] = SCHEMA_VERSION
    return {key: record[key] for key in sorted(record)}


def relation(
    relation_id: str,
    relation_type: str,
    from_id: str,
    to_id: str,
    source: dict[str, Any],
    status: str = "active",
) -> dict[str, Any]:
    return enrich(
        "relations",
        {
            "id": relation_id,
            "relation_type": relation_type,
            "from_id": from_id,
            "to_id": to_id,
            "status": status,
        },
        source,
    )


def make_output(source: dict[str, Any], lane_root: Path, require_bound: bool) -> dict[str, Any]:
    authority_root = safe_join(lane_root, source["path_roots"]["authority"])
    target_root = safe_join(lane_root, source["path_roots"]["target"])
    output: dict[str, Any] = {
        "schema_name": OUTPUT_SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "snapshot_at": source["snapshot_at"],
    }
    for collection in COLLECTIONS:
        output[collection] = []
    for rights_seed in source["rights"]:
        for path_key, hash_key in (
            ("license_file", "license_file_sha256"),
            ("additional_notice_file", "additional_notice_sha256"),
        ):
            relative = rights_seed.get(path_key)
            expected_hash = rights_seed.get(hash_key)
            if (relative is None) != (expected_hash is None):
                raise ValueError(
                    f"{rights_seed['id']} must declare {path_key} and {hash_key} together"
                )
            if relative is not None:
                evidence_path = safe_join(lane_root, relative)
                if not evidence_path.is_file():
                    raise FileNotFoundError(
                        f"missing rights evidence for {rights_seed['id']}: {evidence_path}"
                    )
                actual_hash = sha256_file(evidence_path)
                if actual_hash != expected_hash:
                    raise ValueError(
                        f"rights evidence drift for {rights_seed['id']} field {path_key}: "
                        f"expected {expected_hash}, actual {actual_hash}"
                    )
    for collection in ("programs", "courses", "resources", "editions", "concepts", "terms", "rights", "corrections", "qa_events"):
        output[collection] = [enrich(collection, seed, source) for seed in source[collection]]
    for artifact_seed in source["artifacts"]:
        record = dict(artifact_seed)
        if record.pop("verify_local", False):
            artifact_path = safe_join(lane_root, record["path"])
            if not artifact_path.is_file():
                raise FileNotFoundError(f"missing declared artifact: {artifact_path}")
            actual_bytes = artifact_path.stat().st_size
            actual_hash = sha256_file(artifact_path)
            if record.get("bytes") != actual_bytes or record.get("sha256") != actual_hash:
                raise ValueError(
                    f"artifact drift for {record['id']}: declared {record.get('bytes')}/{record.get('sha256')}, "
                    f"actual {actual_bytes}/{actual_hash}"
                )
            record["local_verification"] = "pass"
        output["artifacts"].append(enrich("artifacts", record, source))
    output["relations"] = [enrich("relations", seed, source) for seed in source["relations"]]
    output["units"] = [enrich("units", seed, source) for seed in source["root_units"]]

    concept_rules = {
        rule["source_local_id"]: list(rule["concept_ids"])
        for rule in source["unit_concept_rules"]
        if rule.get("source_local_id")
    }
    unit_concept_rules = {
        rule["unit_id"]: list(rule["concept_ids"])
        for rule in source["unit_concept_rules"]
        if rule.get("unit_id")
    }
    asset_lookup: defaultdict[str, set[str]] = defaultdict(set)
    for asset_seed in source["assets"]:
        for relative in (asset_seed.get("source_path"), asset_seed.get("target_path")):
            if not relative:
                continue
            posix = PurePosixPath(relative)
            without_suffix = str(posix.with_suffix("")) if posix.suffix else str(posix)
            for key in {str(posix), without_suffix, posix.name, posix.stem}:
                asset_lookup[key.replace("\\", "/")].add(asset_seed["id"])
    source_guard_rows: list[dict[str, Any]] = []
    target_guard_rows: list[dict[str, Any]] = []
    alignment_rows: list[dict[str, Any]] = []
    generated_units: list[dict[str, Any]] = []
    generated_segments: list[dict[str, Any]] = []
    generated_relations: list[dict[str, Any]] = []
    exercise_by_label: dict[str, str] = {}
    event_kinds_by_label: defaultdict[str, set[str]] = defaultdict(set)
    exercise_by_parent_ordinal: dict[tuple[str, int], str] = {}
    projected_exercise_count_by_parent: defaultdict[str, int] = defaultdict(int)
    checkpoint_by_label: dict[str, str] = {}
    pending_solution_links: list[tuple[str, str]] = []
    pending_ordinal_solution_links: list[tuple[str, str, int]] = []
    pending_checkpoint_answer_links: list[tuple[str, str]] = []

    root_siblings: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for root_unit in source["root_units"]:
        if root_unit.get("parent_id"):
            generated_relations.append(
                relation(
                    f"relation.contains.{root_unit['parent_id']}.{root_unit['id']}",
                    "contains",
                    root_unit["parent_id"],
                    root_unit["id"],
                    source,
                )
            )
            root_siblings[root_unit["parent_id"]].append(root_unit)
    for siblings in root_siblings.values():
        ordered = sorted(siblings, key=lambda item: (item["order"], item["id"]))
        for left, right in zip(ordered, ordered[1:]):
            generated_relations.append(
                relation(f"relation.precedes.{left['id']}.{right['id']}", "precedes", left["id"], right["id"], source)
            )
    for correction_seed in source["corrections"]:
        for affected_id in correction_seed.get("affected_unit_ids", []):
            generated_relations.append(
                relation(
                    f"relation.corrects.{correction_seed['id']}.{affected_id}",
                    "corrects",
                    correction_seed["id"],
                    affected_id,
                    source,
                    status=correction_seed.get("status", "open"),
                )
            )

    for file_seed in sorted(source["file_units"], key=lambda row: (row["parent_id"], row["order"], row["id"])):
        source_path = safe_join(authority_root, file_seed["source_path"])
        target_path = safe_join(target_root, file_seed["target_path"])
        if not source_path.is_file():
            raise FileNotFoundError(f"missing authority file: {source_path}")
        if not target_path.is_file():
            raise FileNotFoundError(f"missing target file: {target_path}")
        actual_source_hash = sha256_file(source_path)
        if actual_source_hash != file_seed["source_sha256"]:
            raise ValueError(
                f"source hash drift for {file_seed['id']}: expected {file_seed['source_sha256']}, got {actual_source_hash}"
            )
        source_guard_rows.append({"id": file_seed["id"], "state": "pass", "sha256": actual_source_hash})
        target_hash = sha256_file(target_path)
        expected_target_hash = file_seed.get("expected_target_sha256")
        guard_state = "unbound" if expected_target_hash is None else "pass"
        if expected_target_hash is not None and target_hash != expected_target_hash:
            raise ValueError(
                f"target hash drift for {file_seed['id']}: expected {expected_target_hash}, got {target_hash}"
            )
        if require_bound and expected_target_hash is None:
            raise ValueError(f"target hash guard is unbound for {file_seed['id']}: current {target_hash}")
        target_guard_rows.append({"id": file_seed["id"], "state": guard_state, "sha256": target_hash})
        source_text = read_tex(source_path)
        target_text = read_tex(target_path)
        source_blocks = nonempty_blocks(source_text)
        target_blocks = nonempty_blocks(target_text)
        target_only_specs = file_seed.get("target_only_blocks", [])
        target_only_by_index: dict[int, dict[str, Any]] = {}
        for spec in target_only_specs:
            target_block_index = spec.get("target_block_index")
            if not isinstance(target_block_index, int) or not 1 <= target_block_index <= len(target_blocks):
                raise ValueError(
                    f"invalid target-only block index for {file_seed['id']}: {target_block_index!r}"
                )
            if target_block_index in target_only_by_index:
                raise ValueError(
                    f"duplicate target-only block index for {file_seed['id']}: {target_block_index}"
                )
            if not spec.get("id"):
                raise ValueError(f"target-only block lacks an id for {file_seed['id']}")
            target_only_by_index[target_block_index] = spec
        override_by_source: dict[int, dict[str, Any]] = {}
        for override in file_seed.get("target_block_alignment_overrides", []):
            source_block_index = override.get("source_block_index")
            if not isinstance(source_block_index, int) or not 1 <= source_block_index <= len(source_blocks):
                raise ValueError(
                    f"invalid source alignment block index for {file_seed['id']}: {source_block_index!r}"
                )
            if source_block_index in override_by_source:
                raise ValueError(
                    f"duplicate source alignment override for {file_seed['id']}: {source_block_index}"
                )
            if not override.get("target_parts"):
                raise ValueError(
                    f"alignment override has no target parts for {file_seed['id']} source block {source_block_index}"
                )
            override_by_source[source_block_index] = override

        paired_target_blocks: list[tuple[int, dict[str, Any]]] = []
        covered_target_indices: set[int] = set()
        target_cursor = 1
        target_lines = target_text.splitlines()
        for source_block_index in range(1, len(source_blocks) + 1):
            override = override_by_source.get(source_block_index)
            if override is None:
                while target_cursor in target_only_by_index or target_cursor in covered_target_indices:
                    target_cursor += 1
                if target_cursor > len(target_blocks):
                    break
                target_block = dict(target_blocks[target_cursor - 1])
                target_block["target_block_indices"] = [target_cursor]
                paired_target_blocks.append((target_cursor, target_block))
                covered_target_indices.add(target_cursor)
                target_cursor += 1
                continue

            part_texts: list[str] = []
            part_line_starts: list[int] = []
            part_line_ends: list[int] = []
            part_indices: list[int] = []
            for part in override["target_parts"]:
                target_block_index = part.get("target_block_index")
                if not isinstance(target_block_index, int) or not 1 <= target_block_index <= len(target_blocks):
                    raise ValueError(
                        f"invalid target alignment block index for {file_seed['id']}: {target_block_index!r}"
                    )
                if target_block_index in target_only_by_index:
                    raise ValueError(
                        f"alignment override reuses target-only block for {file_seed['id']}: {target_block_index}"
                    )
                target_block = target_blocks[target_block_index - 1]
                line_start = part.get("line_start", target_block["line_start"])
                line_end = part.get("line_end", target_block["line_end"])
                if (
                    not isinstance(line_start, int)
                    or not isinstance(line_end, int)
                    or line_start < target_block["line_start"]
                    or line_end > target_block["line_end"]
                    or line_start > line_end
                ):
                    raise ValueError(
                        f"invalid target alignment line slice for {file_seed['id']} block {target_block_index}: "
                        f"{line_start!r}-{line_end!r}"
                    )
                part_texts.append("\n".join(target_lines[line_start - 1 : line_end]).strip())
                part_line_starts.append(line_start)
                part_line_ends.append(line_end)
                part_indices.append(target_block_index)
                covered_target_indices.add(target_block_index)
            virtual_target_block = {
                "text": "\n\n".join(part_texts),
                "line_start": min(part_line_starts),
                "line_end": max(part_line_ends),
                "target_block_indices": part_indices,
            }
            paired_target_blocks.append((part_indices[0], virtual_target_block))
            target_cursor = max(target_cursor, max(part_indices) + 1)

        uncovered_target_indices = sorted(
            set(range(1, len(target_blocks) + 1)) - covered_target_indices - set(target_only_by_index)
        )
        projection_mode = file_seed.get("alignment_mode") == "target_projection"
        alignment_state = (
            "pass"
            if projection_mode
            or (len(source_blocks) == len(paired_target_blocks) and not uncovered_target_indices)
            else "fail"
        )
        alignment_rows.append(
            {
                "id": file_seed["id"],
                "state": alignment_state,
                "alignment_mode": (
                    "target_projection_with_file_level_source_binding"
                    if projection_mode
                    else "explicit_source_target_block_pairing"
                ),
                "source_blocks": len(source_blocks),
                "target_blocks": len(target_blocks),
                "paired_target_blocks": len(paired_target_blocks),
                "paired_target_physical_blocks": len(covered_target_indices),
                "target_only_block_indices": sorted(target_only_by_index),
                "alignment_override_source_indices": sorted(override_by_source),
                "uncovered_target_block_indices": uncovered_target_indices,
            }
        )
        if alignment_state != "pass":
            raise ValueError(
                f"segment alignment mismatch for {file_seed['id']}: {len(source_blocks)} source blocks vs "
                f"{len(paired_target_blocks)} paired target blocks ({len(target_blocks)} total target blocks); "
                f"uncovered target blocks={uncovered_target_indices}"
            )
        file_unit = dict(file_seed)
        file_unit.update(
            {
                "resource_id": "resource.r017.open-optimization-book",
                "edition_id": "edition.r017.upstream.1745df89",
                "source_content_sha256": actual_source_hash,
                "target_content_sha256": target_hash,
                "source_locale": "en",
                "target_locale": "id-ID",
                "locale": "mul",
                "translation_state": "draft" if expected_target_hash is None else "translated",
                "target_hash_guard": guard_state,
                "concept_ids": sorted(set(file_seed.get("concept_ids", []))),
                "prerequisite_concept_ids": sorted(
                    set(file_seed.get("prerequisite_concept_ids", []))
                ),
            }
        )
        file_unit.pop("source_sha256", None)
        file_unit.pop("expected_target_sha256", None)
        generated_units.append(enrich("units", file_unit, source))
        generated_relations.append(
            relation(f"relation.contains.{file_seed['parent_id']}.{file_seed['id']}", "contains", file_seed["parent_id"], file_seed["id"], source)
        )
        for concept_id in sorted(set(file_seed.get("concept_ids", []))):
            generated_relations.append(
                relation(
                    f"relation.illustrates.{file_seed['id']}.{concept_id}",
                    "illustrates",
                    file_seed["id"],
                    concept_id,
                    source,
                )
            )

        if projection_mode:
            # Later full-book files preserve their exact frozen English and
            # Indonesian file identities, but Indonesian reflow can merge or
            # split paragraph blocks without a defensible one-to-one English
            # pairing.  Emit independently selectable target blocks and
            # structural nodes while carrying the exact upstream file hash as
            # the honest source locator.  This avoids invented alignments and
            # remains lossless for subsequent language pipelines.
            target_events = extract_structure(target_text)
            for target_event in target_events:
                if target_event.get("source_local_id"):
                    event_kinds_by_label[target_event["source_local_id"]].add(target_event["kind"])
            heading_stack: list[tuple[int, str]] = []
            event_unit_ids: list[str] = []
            kind_depth = {"chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4}
            for event in target_events:
                kind = event["kind"]
                unit_id = f"{file_seed['id']}.{kind}-{event['ordinal']:03d}"
                if kind in kind_depth:
                    depth = kind_depth[kind]
                    while heading_stack and heading_stack[-1][0] >= depth:
                        heading_stack.pop()
                    parent_id = heading_stack[-1][1] if heading_stack else file_seed["id"]
                    heading_stack.append((depth, unit_id))
                else:
                    parent_id = heading_stack[-1][1] if heading_stack else file_seed["id"]
                concepts = sorted(set(file_seed.get("concept_ids", [])))
                target_event_text = target_text[event["position"] : event["end"]]
                generated_units.append(
                    enrich(
                        "units",
                        {
                            "id": unit_id,
                            "unit_type": unit_type_for_event(kind),
                            "target_environment": kind,
                            "resource_id": "resource.r017.open-optimization-book",
                            "edition_id": "edition.r017.id-id.draft",
                            "parent_id": parent_id,
                            "order": event["ordinal"],
                            "source_path": file_seed["source_path"],
                            "source_file_sha256": actual_source_hash,
                            "target_path": file_seed["target_path"],
                            "target_line": event["line"],
                            "target_line_end": target_text.count("\n", 0, event["end"]) + 1,
                            "target_content_sha256": sha256_bytes(target_event_text.encode("utf-8")),
                            "target_hash_guard": guard_state,
                            "source_local_id": event.get("source_local_id"),
                            "target_local_id": event.get("source_local_id"),
                            "title_source": None,
                            "title_target": event["title"],
                            "source_locale": "en",
                            "target_locale": "id-ID",
                            "locale": "id-ID",
                            "translation_state": "structurally_verified",
                            "source_target_relationship": "translation_target_projection",
                            "provenance": "target structural node under an exact hash-bound upstream/target file pair; no invented paragraph-level alignment",
                            "rights_component_id": file_seed["rights_component_id"],
                            "concept_ids": concepts,
                            "starred": event["starred"],
                            "status": "verified",
                        },
                        source,
                    )
                )
                event_unit_ids.append(unit_id)
                generated_relations.append(
                    relation(f"relation.contains.{parent_id}.{unit_id}", "contains", parent_id, unit_id, source)
                )
                if kind in {"ex", "itemexercise"}:
                    projected_exercise_count_by_parent[file_seed["parent_id"]] += 1
                    exercise_by_parent_ordinal[
                        (
                            file_seed["parent_id"],
                            projected_exercise_count_by_parent[file_seed["parent_id"]],
                        )
                    ] = unit_id
                    if event.get("source_local_id"):
                        exercise_by_label[event["source_local_id"]] = unit_id
                if kind == "learningcheckpoint" and event.get("source_local_id"):
                    checkpoint_by_label[event["source_local_id"]] = unit_id
                if kind == "checkpointanswer" and event.get("answers_source_local_id"):
                    pending_checkpoint_answer_links.append(
                        (unit_id, event["answers_source_local_id"])
                    )
                if (
                    kind == "solution"
                    and event.get("solves_source_local_id")
                    and event["solves_source_local_id"] in exercise_by_label
                ):
                    pending_solution_links.append((unit_id, event["solves_source_local_id"]))
                if kind == "manualsolution" and event.get("solves_exercise_ordinal") is not None:
                    pending_ordinal_solution_links.append(
                        (unit_id, file_seed["parent_id"], event["solves_exercise_ordinal"])
                    )
                for concept_id in concepts:
                    relation_type = (
                        "exercises" if kind in {"ex", "itemexercise"} else "illustrates"
                    )
                    generated_relations.append(
                        relation(
                            f"relation.{relation_type}.{unit_id}.{concept_id}",
                            relation_type,
                            unit_id,
                            concept_id,
                            source,
                        )
                    )
            for left, right in zip(event_unit_ids, event_unit_ids[1:]):
                generated_relations.append(
                    relation(f"relation.precedes.{left}.{right}", "precedes", left, right, source)
                )

            for index, block in enumerate(target_blocks, start=1):
                target_block_text = block["text"]
                asset_refs = sorted(
                    set(ASSET_REF_RE.findall(mask_tex_comments(target_block_text)))
                )
                asset_ids = sorted(
                    {
                        asset_id
                        for ref in asset_refs
                        for key in {
                            ref.replace("\\", "/"),
                            PurePosixPath(ref).name,
                            PurePosixPath(ref).stem,
                        }
                        for asset_id in asset_lookup.get(key, set())
                    }
                )
                external_refs = sorted(set(LINK_RE.findall(target_block_text)))
                segment_id = f"segment.{file_seed['id'][5:]}.block-{index:03d}"
                generated_segments.append(
                    enrich(
                        "segments",
                        {
                            "id": segment_id,
                            "unit_id": file_seed["id"],
                            "parent_id": file_seed["id"],
                            "order": index,
                            "segment_type": classify_block(target_block_text),
                            "source_local_id": None,
                            "target_local_id": f"block-{index:03d}",
                            "resource_id": "resource.r017.open-optimization-book",
                            "source_edition_id": "edition.r017.upstream.1745df89",
                            "target_edition_id": "edition.r017.id-id.draft",
                            "source_path": file_seed["source_path"],
                            "source_file_sha256": actual_source_hash,
                            "target_path": file_seed["target_path"],
                            "target_line_start": block["line_start"],
                            "target_line_end": block["line_end"],
                            "source_locale": "en",
                            "target_locale": "id-ID",
                            "locale": "id-ID",
                            "source_text": None,
                            "target_text": target_block_text,
                            "source_content_sha256": None,
                            "target_content_sha256": sha256_bytes(target_block_text.encode("utf-8")),
                            "translation_state": "structurally_verified",
                            "target_hash_guard": guard_state,
                            "source_target_relationship": "translation_target_projection",
                            "provenance": "localized block projected from an exact hash-bound upstream/target file pair; source span is intentionally file-level because reflow changed block boundaries",
                            "concept_ids": sorted(set(file_seed.get("concept_ids", []))),
                            "prerequisite_concept_ids": sorted(
                                set(file_seed.get("prerequisite_concept_ids", []))
                            ),
                            "rights_component_id": file_seed["rights_component_id"],
                            "asset_refs": asset_refs,
                            "asset_ids": asset_ids,
                            "code_data_refs": [
                                ref
                                for ref in external_refs
                                if re.search(r"\.(?:py|ipynb|xlsx?|csv)(?:$|[?#])", ref, re.I)
                            ],
                            "external_refs": external_refs,
                            "status": "verified",
                        },
                        source,
                    )
                )
                for asset_id in asset_ids:
                    generated_relations.append(
                        relation(
                            f"relation.depends-on.{segment_id}.{asset_id}",
                            "depends-on",
                            segment_id,
                            asset_id,
                            source,
                        )
                    )
            alignment_rows[-1]["projected_target_blocks"] = len(target_blocks)
            alignment_rows[-1]["structure_events"] = [
                {
                    "state": "pass",
                    "mode": "target_projection_with_file_level_source_binding",
                    "target_events": len(target_events),
                }
            ]
            continue

        source_events = extract_structure(source_text)
        target_events = extract_structure(target_text)
        source_by_kind: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        target_by_kind: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        semantic_kind = lambda event: (
            "figure"
            if event["kind"] in {"figure", "wrapfigure"}
            else ("example" if event["kind"] in {"example", "examplewithallcode"} else event["kind"])
        )
        for event in source_events:
            source_by_kind[semantic_kind(event)].append(event)
        for event in target_events:
            target_by_kind[semantic_kind(event)].append(event)
        for event in source_events:
            if event.get("source_local_id"):
                event_kinds_by_label[event["source_local_id"]].add(event["kind"])

        event_target_lookup: dict[tuple[str, int], dict[str, Any]] = {}
        source_semantic_ordinals: dict[int, int] = {}
        for kind, events in source_by_kind.items():
            for semantic_ordinal, event in enumerate(events, start=1):
                source_semantic_ordinals[id(event)] = semantic_ordinal
        structure_overrides_by_kind: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for override in file_seed.get("structure_event_alignment_overrides", []):
            kind = override.get("semantic_kind")
            source_ordinal = override.get("source_semantic_ordinal")
            target_ordinal = override.get("target_semantic_ordinal")
            if not isinstance(kind, str) or not kind:
                raise ValueError(
                    f"invalid semantic kind in structural alignment override for {file_seed['id']}"
                )
            if not isinstance(source_ordinal, int) or source_ordinal < 1:
                raise ValueError(
                    f"invalid source semantic ordinal in structural alignment override for {file_seed['id']}"
                )
            if not isinstance(target_ordinal, int) or target_ordinal < 1:
                raise ValueError(
                    f"invalid target semantic ordinal in structural alignment override for {file_seed['id']}"
                )
            structure_overrides_by_kind[kind].append(override)

        structure_alignment_witness: list[dict[str, Any]] = []
        for kind in sorted(set(source_by_kind) | set(target_by_kind) | set(structure_overrides_by_kind)):
            source_kind_events = source_by_kind[kind]
            target_kind_events = target_by_kind[kind]
            override_source_ordinals: set[int] = set()
            reserved_target_ordinals: set[int] = set()
            for override in structure_overrides_by_kind[kind]:
                source_ordinal = override["source_semantic_ordinal"]
                target_ordinal = override["target_semantic_ordinal"]
                if source_ordinal > len(source_kind_events):
                    raise ValueError(
                        f"structural override source ordinal out of range for {file_seed['id']} "
                        f"{kind}: {source_ordinal}"
                    )
                if target_ordinal > len(target_kind_events):
                    raise ValueError(
                        f"structural override target ordinal out of range for {file_seed['id']} "
                        f"{kind}: {target_ordinal}"
                    )
                if source_ordinal in override_source_ordinals:
                    raise ValueError(
                        f"duplicate structural override source ordinal for {file_seed['id']} "
                        f"{kind}: {source_ordinal}"
                    )
                override_source_ordinals.add(source_ordinal)
                if not override.get("allow_target_reuse", False):
                    if target_ordinal in reserved_target_ordinals:
                        raise ValueError(
                            f"duplicate reserved structural target ordinal for {file_seed['id']} "
                            f"{kind}: {target_ordinal}"
                        )
                    reserved_target_ordinals.add(target_ordinal)
                event_target_lookup[(kind, source_ordinal)] = target_kind_events[target_ordinal - 1]

            default_source = [
                (ordinal, event)
                for ordinal, event in enumerate(source_kind_events, start=1)
                if ordinal not in override_source_ordinals
            ]
            default_target = [
                (ordinal, event)
                for ordinal, event in enumerate(target_kind_events, start=1)
                if ordinal not in reserved_target_ordinals
            ]
            if len(default_source) != len(default_target):
                raise ValueError(
                    f"structural mismatch for {file_seed['id']} {kind}: "
                    f"{len(source_kind_events)} source vs {len(target_kind_events)} target; "
                    f"overridden source ordinals={sorted(override_source_ordinals)}, "
                    f"reserved target ordinals={sorted(reserved_target_ordinals)}"
                )
            for (source_ordinal, _), (_, target_event) in zip(default_source, default_target):
                event_target_lookup[(kind, source_ordinal)] = target_event
            structure_alignment_witness.append(
                {
                    "semantic_kind": kind,
                    "source_events": len(source_kind_events),
                    "target_events": len(target_kind_events),
                    "override_source_ordinals": sorted(override_source_ordinals),
                    "reserved_target_ordinals": sorted(reserved_target_ordinals),
                    "state": "pass",
                }
            )
        alignment_rows[-1]["structure_events"] = structure_alignment_witness
        heading_stack: list[tuple[int, str]] = []
        event_unit_ids: list[str] = []
        kind_depth = {"chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4}
        for event in source_events:
            kind = event["kind"]
            unit_id = f"{file_seed['id']}.{kind}-{event['ordinal']:03d}"
            target_event = event_target_lookup[(semantic_kind(event), source_semantic_ordinals[id(event)])]
            source_event_text = source_text[event["position"] : event["end"]]
            target_event_text = target_text[target_event["position"] : target_event["end"]]
            if kind in kind_depth:
                depth = kind_depth[kind]
                while heading_stack and heading_stack[-1][0] >= depth:
                    heading_stack.pop()
                parent_id = heading_stack[-1][1] if heading_stack else file_seed["id"]
                heading_stack.append((depth, unit_id))
            else:
                parent_id = heading_stack[-1][1] if heading_stack else file_seed["id"]
            concepts = sorted(
                set(concept_rules.get(event.get("source_local_id"), []))
                | set(unit_concept_rules.get(unit_id, []))
            )
            unit = enrich(
                "units",
                {
                    "id": unit_id,
                    "unit_type": unit_type_for_event(kind),
                    "source_environment": kind,
                    "target_environment": target_event["kind"],
                    "resource_id": "resource.r017.open-optimization-book",
                    "edition_id": "edition.r017.upstream.1745df89",
                    "parent_id": parent_id,
                    "order": event["ordinal"],
                    "source_path": file_seed["source_path"],
                    "target_path": file_seed["target_path"],
                    "source_line": event["line"],
                    "source_line_end": source_text.count("\n", 0, event["end"]) + 1,
                    "target_line": target_event["line"],
                    "target_line_end": target_text.count("\n", 0, target_event["end"]) + 1,
                    "source_content_sha256": sha256_bytes(source_event_text.encode("utf-8")),
                    "target_content_sha256": sha256_bytes(target_event_text.encode("utf-8")),
                    "target_hash_guard": guard_state,
                    "source_local_id": event.get("source_local_id"),
                    "title_source": event["title"],
                    "title_target": target_event["title"],
                    "source_locale": "en",
                    "target_locale": "id-ID",
                    "locale": "mul",
                    "translation_state": "draft" if expected_target_hash is None else "translated",
                    "rights_component_id": file_seed["rights_component_id"],
                    "concept_ids": concepts,
                    "starred": event["starred"],
                    "status": "draft" if expected_target_hash is None else "translated",
                },
                source,
            )
            generated_units.append(unit)
            event_unit_ids.append(unit_id)
            generated_relations.append(
                relation(f"relation.contains.{parent_id}.{unit_id}", "contains", parent_id, unit_id, source)
            )
            if kind in {"ex", "itemexercise"} and event.get("source_local_id"):
                exercise_by_label[event["source_local_id"]] = unit_id
            if kind in {"ex", "itemexercise"}:
                exercise_by_parent_ordinal[(file_seed["parent_id"], event["ordinal"])] = unit_id
            if kind == "learningcheckpoint" and event.get("source_local_id"):
                checkpoint_by_label[event["source_local_id"]] = unit_id
            if kind == "checkpointanswer" and event.get("answers_source_local_id"):
                pending_checkpoint_answer_links.append(
                    (unit_id, event["answers_source_local_id"])
                )
            if kind == "solution" and event.get("solves_source_local_id"):
                pending_solution_links.append((unit_id, event["solves_source_local_id"]))
            if kind == "manualsolution" and event.get("solves_exercise_ordinal") is not None:
                pending_ordinal_solution_links.append(
                    (unit_id, file_seed["parent_id"], event["solves_exercise_ordinal"])
                )
            for concept_id in concepts:
                relation_type = (
                    "exercises" if kind in {"ex", "itemexercise"} else "illustrates"
                )
                generated_relations.append(
                    relation(f"relation.{relation_type}.{unit_id}.{concept_id}", relation_type, unit_id, concept_id, source)
                )
        for left, right in zip(event_unit_ids, event_unit_ids[1:]):
            generated_relations.append(
                relation(f"relation.precedes.{left}.{right}", "precedes", left, right, source)
            )

        for index, (source_block, target_pair) in enumerate(zip(source_blocks, paired_target_blocks), start=1):
            target_block_index, target_block = target_pair
            source_block_text = source_block["text"]
            target_block_text = target_block["text"]
            labels = LABEL_RE.findall(source_block_text)
            concept_ids = sorted({concept for label in labels for concept in concept_rules.get(label, [])})
            asset_refs = sorted(
                set(ASSET_REF_RE.findall(mask_tex_comments(source_block_text)))
            )
            asset_ids = sorted(
                {
                    asset_id
                    for ref in asset_refs
                    for key in {ref.replace("\\", "/"), PurePosixPath(ref).name, PurePosixPath(ref).stem}
                    for asset_id in asset_lookup.get(key, set())
                }
            )
            external_refs = sorted(set(LINK_RE.findall(source_block_text)))
            segment_id = f"segment.{file_seed['id'][5:]}.block-{index:03d}"
            generated_segments.append(
                enrich(
                    "segments",
                    {
                        "id": segment_id,
                        "unit_id": file_seed["id"],
                        "parent_id": file_seed["id"],
                        "order": target_block_index,
                        "segment_type": classify_block(source_block_text),
                        "source_local_id": f"block-{index:03d}",
                        "source_block_index": index,
                        "target_block_index": target_block_index,
                        "resource_id": "resource.r017.open-optimization-book",
                        "source_edition_id": "edition.r017.upstream.1745df89",
                        "target_edition_id": "edition.r017.id-id.draft",
                        "source_path": file_seed["source_path"],
                        "target_path": file_seed["target_path"],
                        "source_line_start": source_block["line_start"],
                        "source_line_end": source_block["line_end"],
                        "target_line_start": target_block["line_start"],
                        "target_line_end": target_block["line_end"],
                        "source_locale": "en",
                        "target_locale": "id-ID",
                        "locale": "mul",
                        "source_text": source_block_text,
                        "target_text": target_block_text,
                        "source_content_sha256": sha256_bytes(source_block_text.encode("utf-8")),
                        "target_content_sha256": sha256_bytes(target_block_text.encode("utf-8")),
                        "translation_state": "draft" if expected_target_hash is None else "translated",
                        "target_hash_guard": guard_state,
                        "source_target_relationship": "translation",
                        "provenance": "source block at pinned upstream commit paired to the explicit target block order after excluding declared target-native additions",
                        "concept_ids": concept_ids,
                        "prerequisite_concept_ids": sorted(
                            {
                                prerequisite
                                for concept in source["concepts"]
                                if concept["id"] in concept_ids
                                for prerequisite in concept.get("prerequisite_concept_ids", [])
                            }
                        ),
                        "rights_component_id": file_seed["rights_component_id"],
                        "asset_refs": asset_refs,
                        "asset_ids": asset_ids,
                        "code_data_refs": [ref for ref in external_refs if re.search(r"\.(?:py|ipynb|xlsx?|csv)(?:$|[?#])", ref, re.I)],
                        "external_refs": external_refs,
                        "status": "draft" if expected_target_hash is None else "translated",
                    },
                    source,
                )
            )
            for asset_id in asset_ids:
                generated_relations.append(
                    relation(f"relation.depends-on.{segment_id}.{asset_id}", "depends-on", segment_id, asset_id, source)
                )

        for target_block_index, spec in sorted(target_only_by_index.items()):
            target_block = target_blocks[target_block_index - 1]
            target_block_text = target_block["text"]
            concept_ids = sorted(set(spec.get("concept_ids", [])))
            asset_refs = sorted(
                set(ASSET_REF_RE.findall(mask_tex_comments(target_block_text)))
            )
            asset_ids = sorted(
                {
                    asset_id
                    for ref in asset_refs
                    for key in {ref.replace("\\", "/"), PurePosixPath(ref).name, PurePosixPath(ref).stem}
                    for asset_id in asset_lookup.get(key, set())
                }
            )
            external_refs = sorted(set(LINK_RE.findall(target_block_text)))
            segment_id = spec["id"]
            generated_segments.append(
                enrich(
                    "segments",
                    {
                        "id": segment_id,
                        "unit_id": file_seed["id"],
                        "parent_id": file_seed["id"],
                        "order": target_block_index,
                        "segment_type": spec.get("segment_type", classify_block(target_block_text)),
                        "source_local_id": None,
                        "target_block_index": target_block_index,
                        "resource_id": "resource.r017.open-optimization-book",
                        "source_edition_id": None,
                        "target_edition_id": "edition.r017.id-id.draft",
                        "source_path": None,
                        "target_path": file_seed["target_path"],
                        "target_line_start": target_block["line_start"],
                        "target_line_end": target_block["line_end"],
                        "source_locale": None,
                        "target_locale": "id-ID",
                        "locale": "id-ID",
                        "target_text": target_block_text,
                        "target_content_sha256": sha256_bytes(target_block_text.encode("utf-8")),
                        # `target_native` is a provenance relationship, not one
                        # of the interoperability envelope's translation
                        # states.  The explicit relationship below preserves
                        # that distinction while this reviewed addition maps
                        # losslessly to the common state machine.
                        "translation_state": "structurally_verified",
                        "target_hash_guard": guard_state,
                        "source_target_relationship": "target_native_correction",
                        "provenance": spec["provenance"],
                        "native_reason": spec.get("native_reason"),
                        "correction_ids": sorted(set(spec.get("correction_ids", []))),
                        "concept_ids": concept_ids,
                        "prerequisite_concept_ids": sorted(
                            {
                                prerequisite
                                for concept in source["concepts"]
                                if concept["id"] in concept_ids
                                for prerequisite in concept.get("prerequisite_concept_ids", [])
                            }
                        ),
                        "rights_component_id": spec.get("rights_component_id", file_seed["rights_component_id"]),
                        "asset_refs": asset_refs,
                        "asset_ids": asset_ids,
                        "code_data_refs": [ref for ref in external_refs if re.search(r"\.(?:py|ipynb|xlsx?|csv)(?:$|[?#])", ref, re.I)],
                        "external_refs": external_refs,
                        "status": "verified",
                    },
                    source,
                )
            )
            for asset_id in asset_ids:
                generated_relations.append(
                    relation(f"relation.depends-on.{segment_id}.{asset_id}", "depends-on", segment_id, asset_id, source)
                )

    for native_seed in sorted(source["native_file_units"], key=lambda row: (row["parent_id"], row["order"], row["id"])):
        content_path = safe_join(target_root, native_seed["content_path"])
        if not content_path.is_file():
            raise FileNotFoundError(f"missing native content file: {content_path}")
        content_hash = sha256_file(content_path)
        if content_hash != native_seed["expected_content_sha256"]:
            raise ValueError(
                f"native content hash drift for {native_seed['id']}: "
                f"expected {native_seed['expected_content_sha256']}, got {content_hash}"
            )
        source_guard_rows.append({"id": native_seed["id"], "state": "pass", "sha256": content_hash})
        target_guard_rows.append({"id": native_seed["id"], "state": "pass", "sha256": content_hash})
        content_text = read_tex(content_path)
        unit = dict(native_seed)
        unit.update(
            {
                "source_path": native_seed["content_path"],
                "source_content_sha256": content_hash,
                "source_bytes": content_path.stat().st_size,
                "source_locale": native_seed["locale"],
                "target_locale": None,
                "translation_state": "source_frozen",
                "content_hash_guard": "pass",
                "provenance": "locally authored primary derivative content with explicit source-adaptation relation",
                "status": "source_frozen",
            }
        )
        unit.pop("content_path", None)
        unit.pop("expected_content_sha256", None)
        generated_units.append(enrich("units", unit, source))
        generated_relations.append(
            relation(f"relation.contains.{native_seed['parent_id']}.{native_seed['id']}", "contains", native_seed["parent_id"], native_seed["id"], source)
        )
        for asset_id in sorted(set(native_seed.get("asset_ids", []))):
            generated_relations.append(
                relation(
                    f"relation.depends-on.{native_seed['id']}.{asset_id}",
                    "depends-on",
                    native_seed["id"],
                    asset_id,
                    source,
                )
            )
        for concept_id in sorted(set(native_seed.get("concept_ids", []))):
            generated_relations.append(
                relation(
                    f"relation.illustrates.{native_seed['id']}.{concept_id}",
                    "illustrates",
                    native_seed["id"],
                    concept_id,
                    source,
                )
            )
        heading_stack: list[tuple[int, str]] = []
        heading_ids: list[str] = []
        for heading in extract_markdown_headings(content_text):
            heading_id = f"{native_seed['id']}.heading-{heading['ordinal']:03d}"
            while heading_stack and heading_stack[-1][0] >= heading["depth"]:
                heading_stack.pop()
            parent_id = heading_stack[-1][1] if heading_stack else native_seed["id"]
            heading_stack.append((heading["depth"], heading_id))
            heading_text = content_text[heading["position"] : heading["end"]]
            generated_units.append(
                enrich(
                    "units",
                    {
                        "id": heading_id,
                        "unit_type": "section",
                        "resource_id": native_seed["resource_id"],
                        "edition_id": native_seed["edition_id"],
                        "parent_id": parent_id,
                        "order": heading["ordinal"],
                        "source_path": native_seed["content_path"],
                        "source_line": heading["line"],
                        "source_line_end": heading["line"],
                        "source_content_sha256": sha256_bytes(heading_text.encode("utf-8")),
                        "source_locale": native_seed["locale"],
                        "target_locale": None,
                        "locale": native_seed["locale"],
                        "title_source": heading["title"],
                        "title_target": None,
                        "translation_state": "source_frozen",
                        "rights_component_id": native_seed["rights_component_id"],
                        "concept_ids": native_seed.get("concept_ids", []),
                        "status": "source_frozen",
                    },
                    source,
                )
            )
            generated_relations.append(
                relation(f"relation.contains.{parent_id}.{heading_id}", "contains", parent_id, heading_id, source)
            )
            heading_ids.append(heading_id)
        for left, right in zip(heading_ids, heading_ids[1:]):
            generated_relations.append(relation(f"relation.precedes.{left}.{right}", "precedes", left, right, source))
        for index, block in enumerate(nonempty_blocks(content_text), start=1):
            segment_id = f"segment.{native_seed['id'][5:]}.block-{index:03d}"
            block_text = block["text"]
            generated_segments.append(
                enrich(
                    "segments",
                    {
                        "id": segment_id,
                        "unit_id": native_seed["id"],
                        "parent_id": native_seed["id"],
                        "order": index,
                        "segment_type": "heading_or_structured_prose" if block_text.startswith("#") else "prose",
                        "source_local_id": f"block-{index:03d}",
                        "resource_id": native_seed["resource_id"],
                        "source_edition_id": native_seed["edition_id"],
                        "target_edition_id": None,
                        "source_path": native_seed["content_path"],
                        "source_line_start": block["line_start"],
                        "source_line_end": block["line_end"],
                        "source_locale": native_seed["locale"],
                        "target_locale": None,
                        "locale": native_seed["locale"],
                        "source_text": block_text,
                        "target_text": None,
                        "source_content_sha256": sha256_bytes(block_text.encode("utf-8")),
                        "target_content_sha256": None,
                        "translation_state": "source_frozen",
                        "content_hash_guard": "pass",
                        "source_target_relationship": "locally_authored_adaptation",
                        "provenance": "primary O018 Indonesian content; source relation is explicit at unit level",
                        "concept_ids": native_seed.get("concept_ids", []),
                        "prerequisite_concept_ids": native_seed.get("prerequisite_concept_ids", []),
                        "rights_component_id": native_seed["rights_component_id"],
                        "asset_refs": [],
                        "asset_ids": native_seed.get("asset_ids", []),
                        "code_data_refs": native_seed.get("code_data_refs", []),
                        "external_refs": sorted(set(re.findall(r"https?://[^)>\s]+", block_text))),
                        "status": "source_frozen",
                    },
                    source,
                )
            )

    for solution_id, exercise_label in pending_solution_links:
        exercise_id = exercise_by_label.get(exercise_label)
        if not exercise_id:
            # Expository solution environments often first reference a nested
            # figure or equation rather than an exercise.  Preserve strict
            # failure for dangling references, but do not misclassify a known
            # non-exercise label as an exercise/solution linkage.
            if exercise_label in event_kinds_by_label:
                continue
            raise ValueError(f"solution {solution_id} references unknown exercise label {exercise_label}")
        generated_relations.append(
            relation(f"relation.solves.{solution_id}.{exercise_id}", "solves", solution_id, exercise_id, source)
        )
    for solution_id, parent_id, exercise_ordinal in pending_ordinal_solution_links:
        exercise_id = exercise_by_parent_ordinal.get((parent_id, exercise_ordinal))
        if not exercise_id:
            raise ValueError(
                f"manual solution {solution_id} references unknown exercise ordinal "
                f"{exercise_ordinal} under {parent_id}"
            )
        generated_relations.append(
            relation(f"relation.solves.{solution_id}.{exercise_id}", "solves", solution_id, exercise_id, source)
        )
    for answer_id, checkpoint_label in pending_checkpoint_answer_links:
        checkpoint_id = checkpoint_by_label.get(checkpoint_label)
        if not checkpoint_id:
            raise ValueError(
                f"checkpoint answer {answer_id} references unknown checkpoint label {checkpoint_label}"
            )
        generated_relations.append(
            relation(
                f"relation.answers.{answer_id}.{checkpoint_id}",
                "answers",
                answer_id,
                checkpoint_id,
                source,
            )
        )

    for concept in source["concepts"]:
        for prerequisite in concept.get("prerequisite_concept_ids", []):
            generated_relations.append(
                relation(f"relation.prerequisite.{concept['id']}.{prerequisite}", "prerequisite", concept["id"], prerequisite, source)
            )

    asset_records: list[dict[str, Any]] = []
    asset_source_guard_rows: list[dict[str, Any]] = []
    asset_guard_rows: list[dict[str, Any]] = []
    for seed in source["assets"]:
        record = dict(seed)
        source_relative = seed.get("source_path")
        target_relative = seed.get("target_path")
        if source_relative:
            source_path = safe_join(authority_root, source_relative)
            if not source_path.is_file():
                raise FileNotFoundError(f"missing authority asset: {source_path}")
            actual_source_hash = sha256_file(source_path)
            expected_source_hash = seed.get("source_sha256")
            if expected_source_hash and actual_source_hash != expected_source_hash:
                raise ValueError(f"source asset hash drift for {seed['id']}")
            record["source_content_sha256"] = actual_source_hash
            record["source_bytes"] = source_path.stat().st_size
            asset_source_guard_rows.append({"id": seed["id"], "state": "pass", "sha256": actual_source_hash})
        if target_relative:
            target_path = safe_join(target_root, target_relative)
            if not target_path.is_file():
                raise FileNotFoundError(f"missing target asset: {target_path}")
            actual_target_hash = sha256_file(target_path)
            expected_target_hash = seed.get("expected_target_sha256")
            if expected_target_hash is not None and actual_target_hash != expected_target_hash:
                raise ValueError(f"target asset hash drift for {seed['id']}")
            if require_bound and expected_target_hash is None:
                raise ValueError(f"target asset hash guard is unbound for {seed['id']}: current {actual_target_hash}")
            record["target_content_sha256"] = actual_target_hash
            record["target_bytes"] = target_path.stat().st_size
            record["target_hash_guard"] = "unbound" if expected_target_hash is None else "pass"
            asset_guard_rows.append({"id": seed["id"], "state": record["target_hash_guard"], "sha256": actual_target_hash})
        record.pop("source_sha256", None)
        record.pop("expected_target_sha256", None)
        asset_records.append(enrich("assets", record, source))

    output["assets"] = asset_records
    output["units"].extend(generated_units)
    output["segments"].extend(generated_segments)
    output["relations"].extend(generated_relations)

    r017_units_by_label: defaultdict[str, list[str]] = defaultdict(list)
    r017_units_by_chapter_ordinal: dict[tuple[int, int], str] = {}
    r017_exercises_by_chapter: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for unit in output["units"]:
        if (
            unit.get("resource_id") == "resource.r017.open-optimization-book"
            and unit.get("source_local_id")
            and unit.get("unit_type") == "exercise"
        ):
            r017_units_by_label[unit["source_local_id"]].append(unit["id"])
        match = re.match(r"unit\.r017\.book1\.ch(\d\d)\.", unit["id"])
        if match and unit.get("unit_type") == "exercise":
            r017_exercises_by_chapter[int(match.group(1))].append(unit)
    for chapter, exercises in r017_exercises_by_chapter.items():
        for ordinal, unit in enumerate(
            sorted(exercises, key=lambda item: (item.get("topology_order_path", []), item["id"])),
            start=1,
        ):
            r017_units_by_chapter_ordinal[(chapter, ordinal)] = unit["id"]
    o018_exercise_alignment: list[dict[str, Any]] = []
    for unit in output["units"]:
        source_book_label = unit.get("source_book_label")
        candidates = r017_units_by_label.get(source_book_label, []) if source_book_label else []
        source_book_reference = source_book_label
        match_mode = "source_book_label"
        if (
            not source_book_label
            and re.match(r"^unit\.o018\.lab\.ch(?:10|11)\.ex-", unit["id"])
        ):
            numeric_match = re.fullmatch(
                r"exercise-(\d+)\.(\d+)", unit.get("source_local_id", "")
            )
            if numeric_match:
                chapter_ordinal = (int(numeric_match.group(1)), int(numeric_match.group(2)))
                candidate = r017_units_by_chapter_ordinal.get(chapter_ordinal)
                candidates = [candidate] if candidate else []
                source_book_reference = f"exercise-number:{chapter_ordinal[0]}.{chapter_ordinal[1]}"
                match_mode = "explicit_book_exercise_number"
        if not source_book_reference:
            continue
        if len(candidates) == 1:
            for relation_type in ("adapts", "solves"):
                output["relations"].append(
                    relation(
                        f"relation.{relation_type}.{unit['id']}.{candidates[0]}",
                        relation_type,
                        unit["id"],
                        candidates[0],
                        source,
                    )
                )
            o018_exercise_alignment.append(
                {
                    "o018_unit_id": unit["id"],
                    "source_book_label": source_book_label,
                    "source_book_reference": source_book_reference,
                    "match_mode": match_mode,
                    "r017_unit_id": candidates[0],
                    "state": "matched",
                }
            )
        elif not candidates:
            o018_exercise_alignment.append(
                {
                    "o018_unit_id": unit["id"],
                    "source_book_label": source_book_label,
                    "source_book_reference": source_book_reference,
                    "match_mode": match_mode,
                    "r017_unit_id": None,
                    "state": "label_preserved_without_parser_match",
                }
            )
        elif len(candidates) > 1:
            raise ValueError(
                f"ambiguous R017 source label for {unit['id']}: {source_book_label} -> {candidates}"
            )
    if o018_exercise_alignment:
        unresolved_alignment = [
            row for row in o018_exercise_alignment if row["state"] != "matched"
        ]
        output["qa_events"].append(
            enrich(
                "qa_events",
                {
                    "id": "qa.backend.o018-exercise-source-alignment",
                    "qa_type": "topology",
                    "result": (
                        "pass"
                        if not unresolved_alignment
                        else "pass_with_explicit_file_level_source_labels"
                    ),
                    "witness": o018_exercise_alignment,
                    "affected_ids": [row["o018_unit_id"] for row in o018_exercise_alignment],
                    "status": "complete",
                },
                source,
            )
        )

    unit_lookup = {unit["id"]: unit for unit in output["units"]}
    topology_cache: dict[str, tuple[list[str], list[int]]] = {}

    def topology(unit_id: str, active: tuple[str, ...] = ()) -> tuple[list[str], list[int]]:
        if unit_id in topology_cache:
            return topology_cache[unit_id]
        if unit_id in active:
            raise ValueError(f"unit-parent cycle: {' -> '.join(active + (unit_id,))}")
        unit = unit_lookup[unit_id]
        parent_id = unit.get("parent_id")
        if parent_id:
            if parent_id not in unit_lookup:
                raise ValueError(f"unit {unit_id} has unknown parent {parent_id}")
            parent_path, parent_order = topology(parent_id, active + (unit_id,))
        else:
            parent_path, parent_order = [], []
        result = (parent_path + [unit_id], parent_order + [int(unit.get("order", 0))])
        topology_cache[unit_id] = result
        return result

    for unit in output["units"]:
        unit["topology_path"], unit["topology_order_path"] = topology(unit["id"])
    for segment in output["segments"]:
        parent_path, parent_order = topology(segment["parent_id"])
        segment["topology_path"] = parent_path + [segment["id"]]
        segment["topology_order_path"] = parent_order + [segment["order"]]

    output["qa_events"].extend(
        [
            enrich(
                "qa_events",
                {
                    "id": "qa.backend.source-hash-guards",
                    "qa_type": "source",
                    "result": "pass",
                    "witness": source_guard_rows + asset_source_guard_rows,
                    "affected_ids": [row["id"] for row in source_guard_rows + asset_source_guard_rows],
                    "status": "complete",
                },
                source,
            ),
            enrich(
                "qa_events",
                {
                    "id": "qa.backend.target-hash-guards",
                    "qa_type": "source",
                    "result": "pass" if all(row["state"] == "pass" for row in target_guard_rows + asset_guard_rows) else "unbound",
                    "witness": target_guard_rows + asset_guard_rows,
                    "affected_ids": [row["id"] for row in target_guard_rows + asset_guard_rows],
                    "status": "complete" if all(row["state"] == "pass" for row in target_guard_rows + asset_guard_rows) else "open",
                },
                source,
            ),
            enrich(
                "qa_events",
                {
                    "id": "qa.backend.segment-alignment",
                    "qa_type": "topology",
                    "result": "pass",
                    "witness": alignment_rows,
                    "affected_ids": [row["id"] for row in alignment_rows],
                    "status": "complete",
                },
                source,
            ),
            enrich(
                "qa_events",
                {
                    "id": "qa.backend.schema-validation",
                    "qa_type": "backend",
                    "result": "pass",
                    "witness": "Input and output validate against the checked-in Draft 2020-12 schemas using the lane's deterministic standard-library validator.",
                    "affected_ids": ["artifact.backend.canonical-json"],
                    "status": "complete",
                },
                source,
            ),
            enrich(
                "qa_events",
                {
                    "id": "qa.backend.deterministic-serialization",
                    "qa_type": "backend",
                    "result": "pass",
                    "witness": "Two independent in-memory serializations are required to be byte-identical before any output is written; --check verifies a later run against disk.",
                    "affected_ids": ["artifact.backend.canonical-json"],
                    "status": "complete",
                },
                source,
            ),
        ]
    )

    output["artifacts"].append(
        enrich(
            "artifacts",
            {
                "id": "artifact.backend.canonical-json",
                "artifact_type": "modular_backend_export",
                "path": "backend/dist/backend-v0.json",
                "bytes": None,
                "sha256": None,
                "toolchain": "scripts/export_backend.py; Python standard library",
                "build_receipt": "Hash is carried by backend/dist/manifest.json to avoid a self-referential digest.",
                "status": "generated",
            },
            source,
        )
    )

    for collection in COLLECTIONS:
        output[collection] = sorted(output[collection], key=lambda record: record["id"])
    validate_references(output)
    return output


def validate_references(output: dict[str, Any]) -> None:
    all_records = [record for collection in COLLECTIONS for record in output[collection]]
    ids = [record["id"] for record in all_records]
    duplicates = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
    if duplicates:
        raise ValueError(f"duplicate global IDs: {duplicates}")
    id_set = set(ids)
    for record in all_records:
        if not ID_RE.fullmatch(record["id"]):
            raise ValueError(f"invalid stable ID: {record['id']}")
        for key, value in record.items():
            if key.endswith("_sha256") and value is not None and not SHA256_RE.fullmatch(value):
                raise ValueError(f"invalid SHA-256 in {record['id']} field {key}")
        for key in ("parent_id", "resource_id", "edition_id", "source_edition_id", "target_edition_id", "rights_component_id", "from_id", "to_id", "program_id", "concept_id"):
            ref = record.get(key)
            if ref is not None and ref not in id_set:
                raise ValueError(f"{record['id']} references missing {key}={ref}")
        for key in ("resource_ids", "prerequisite_course_ids", "concept_ids", "prerequisite_concept_ids", "asset_ids", "rights_component_ids", "additional_rights_component_ids", "replacement_asset_ids", "affected_ids", "affected_unit_ids"):
            for ref in record.get(key, []):
                if ref not in id_set:
                    raise ValueError(f"{record['id']} references missing {key} member {ref}")
    for asset in output["assets"]:
        evidence_id = asset.get("machine_backend_evidence_artifact_id")
        if evidence_id is not None and evidence_id not in id_set:
            raise ValueError(
                f"{asset['id']} references missing machine backend evidence {evidence_id}"
            )
        runtime_evidence_id = asset.get("runtime_closure_evidence_artifact_id")
        if runtime_evidence_id is not None and runtime_evidence_id not in id_set:
            raise ValueError(
                f"{asset['id']} references missing runtime closure evidence {runtime_evidence_id}"
            )
        for ref in asset.get("runtime_dependency_ids", []):
            if ref not in id_set:
                raise ValueError(
                    f"{asset['id']} references missing runtime_dependency_ids member {ref}"
                )
        o018 = asset.get("o018_pyomo_highs")
        if not isinstance(o018, dict):
            continue
        for key in ("mapping_unit_ids", "runtime_dependency_ids"):
            for ref in o018.get(key, []):
                if ref not in id_set:
                    raise ValueError(
                        f"{asset['id']} references missing o018_pyomo_highs.{key} member {ref}"
                    )
    allowed_states = {
        "source_frozen",
        "queued",
        "draft",
        "translated",
        "structurally_verified",
        "mathematically_reviewed",
        "language_reviewed",
        "built",
        "visually_checked",
        "published",
        "superseded",
        "blocked",
    }
    for segment in output["segments"]:
        if segment["translation_state"] not in allowed_states:
            raise ValueError(f"invalid translation state in {segment['id']}")


def flatten_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def csv_bytes(records: list[dict[str, Any]]) -> bytes:
    columns = sorted({key for record in records for key in record})
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for record in sorted(
        records,
        key=lambda item: item.get("id", item.get("exercise_id", canonical_json(item).decode("utf-8"))),
    ):
        writer.writerow([flatten_csv_value(record.get(column)) for column in columns])
    return buffer.getvalue().encode("utf-8")


def exercise_link_records(output: dict[str, Any]) -> list[dict[str, Any]]:
    exercise_ids = {unit["id"] for unit in output["units"] if unit.get("unit_type") == "exercise"}
    rows: list[dict[str, Any]] = []
    solved: set[str] = set()
    for rel in output["relations"]:
        if rel.get("relation_type") == "solves":
            rows.append(
                {
                    "exercise_id": rel["to_id"],
                    "solution_id": rel["from_id"],
                    "hint_id": "",
                    "answer_id": "",
                    "relation_id": rel["id"],
                }
            )
            solved.add(rel["to_id"])
    for exercise_id in sorted(exercise_ids - solved):
        rows.append(
            {
                "exercise_id": exercise_id,
                "solution_id": "",
                "hint_id": "",
                "answer_id": "",
                "relation_id": "",
            }
        )
    return sorted(rows, key=lambda row: row["exercise_id"])


def build_files(output: dict[str, Any]) -> dict[str, bytes]:
    files: dict[str, bytes] = {"backend-v0.json": canonical_json(output, pretty=True)}
    for collection in COLLECTIONS:
        files[f"jsonl/{collection}.jsonl"] = b"".join(canonical_json(record) for record in output[collection])
        files[f"csv/{collection}.csv"] = csv_bytes(output[collection])
    files["csv/exercise_links.csv"] = csv_bytes(exercise_link_records(output))
    return files


def validate_projections(files: dict[str, bytes]) -> None:
    for path, data in files.items():
        if path.endswith(".json"):
            json.loads(data.decode("utf-8"))
        elif path.endswith(".jsonl"):
            for number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
                if line:
                    record = json.loads(line)
                    missing = {"schema_name", "schema_version", "id", "status", "recorded_at", "responsible_workflow", "supersedes_id"} - record.keys()
                    if missing:
                        raise ValueError(f"{path}:{number}: missing common fields {sorted(missing)}")
        elif path.endswith(".csv"):
            rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
            if not rows:
                raise ValueError(f"empty CSV projection: {path}")
            if len(rows[0]) != len(set(rows[0])):
                raise ValueError(f"duplicate CSV columns: {path}")
            width = len(rows[0])
            for number, row in enumerate(rows[1:], start=2):
                if len(row) != width:
                    raise ValueError(f"{path}:{number}: {len(row)} columns, expected {width}")


def add_manifest(files: dict[str, bytes], output: dict[str, Any]) -> dict[str, bytes]:
    manifest = {
        "schema_name": "interlanguage.artifact-manifest",
        "schema_version": SCHEMA_VERSION,
        "snapshot_at": output["snapshot_at"],
        "hash_algorithm": "sha256",
        "artifacts": [
            {"path": path, "bytes": len(data), "sha256": sha256_bytes(data)}
            for path, data in sorted(files.items())
        ],
        "manifest_self_hash_location": "SHA256SUMS.txt",
    }
    result = dict(files)
    result["manifest.json"] = canonical_json(manifest, pretty=True)
    result["SHA256SUMS.txt"] = "".join(
        f"{sha256_bytes(data)}  {path}\n" for path, data in sorted(result.items())
    ).encode("utf-8")
    return result


def write_files(dist: Path, files: dict[str, bytes]) -> None:
    if dist.exists():
        actual = {
            path.relative_to(dist).as_posix()
            for path in dist.rglob("*")
            if path.is_file()
        }
        undeclared = sorted(actual - set(files))
        if undeclared:
            raise ValueError(
                "refusing to write over output tree with undeclared files: "
                + "; ".join(undeclared)
            )
    for relative, data in sorted(files.items()):
        path = safe_join(dist, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def check_files(dist: Path, files: dict[str, bytes]) -> None:
    failures: list[str] = []
    actual = {
        path.relative_to(dist).as_posix()
        for path in dist.rglob("*")
        if path.is_file()
    } if dist.is_dir() else set()
    expected = set(files)
    for relative in sorted(actual - expected):
        failures.append(f"undeclared extra file {relative}")
    for relative in sorted(expected - actual):
        failures.append(f"missing {relative}")
    for relative, data in sorted(files.items()):
        path = safe_join(dist, relative)
        if path.is_file() and path.read_bytes() != data:
            failures.append(f"byte mismatch {relative}")
    if failures:
        raise ValueError("deterministic disk check failed: " + "; ".join(failures))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--check", action="store_true", help="compare regenerated bytes to the existing dist tree")
    result.add_argument("--require-bound-targets", action="store_true", help="fail if any target hash guard is null")
    result.add_argument("--show-target-hashes", action="store_true", help="print current target-hash values for guard binding")
    result.add_argument(
        "--output-dir",
        default="backend/dist",
        help="lane-relative output directory (default: backend/dist; useful for an independent clean replay)",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    lane_root = Path(__file__).resolve().parents[1]
    input_path = lane_root / "backend" / "input" / "backend-input.json"
    supplement_path = lane_root / "backend" / "input" / "full-corpus-supplement.json"
    input_schema_path = lane_root / "backend" / "schema" / "backend-input-v0.schema.json"
    supplement_schema_path = lane_root / "backend" / "schema" / "full-corpus-supplement-v0.schema.json"
    output_schema_path = lane_root / "backend" / "schema" / "modular-backend-v0.schema.json"
    dist = safe_join(lane_root, args.output_dir.replace("\\", "/"))

    source = load_json(input_path)
    if not supplement_path.is_file():
        raise FileNotFoundError(f"missing full-corpus backend supplement: {supplement_path}")
    supplement = load_json(supplement_path)
    input_schema = load_json(input_schema_path)
    supplement_schema = load_json(supplement_schema_path)
    output_schema = load_json(output_schema_path)
    validate_schema_document(input_schema, input_schema_path.name)
    validate_schema_document(supplement_schema, supplement_schema_path.name)
    validate_schema_document(output_schema, output_schema_path.name)
    supplement_errors = validate_against_schema(
        supplement, supplement_schema, supplement_schema
    )
    if supplement_errors:
        raise ValueError(
            "supplement schema validation failed:\n" + "\n".join(supplement_errors)
        )
    evidence_binding = supplement["machine_backend_evidence"]
    evidence_path = safe_join(lane_root, evidence_binding["path"])
    evidence_schema_path = safe_join(lane_root, evidence_binding["schema_path"])
    if not evidence_path.is_file():
        raise FileNotFoundError(f"missing machine-backend evidence: {evidence_path}")
    if evidence_path.stat().st_size != evidence_binding["bytes"]:
        raise ValueError("machine-backend evidence byte binding drift")
    if sha256_file(evidence_path) != evidence_binding["sha256"]:
        raise ValueError("machine-backend evidence hash binding drift")
    machine_evidence = load_json(evidence_path)
    evidence_schema = load_json(evidence_schema_path)
    validate_schema_document(evidence_schema, evidence_schema_path.name)
    evidence_errors = validate_against_schema(
        machine_evidence, evidence_schema, evidence_schema
    )
    if evidence_errors:
        raise ValueError(
            "machine-backend evidence schema validation failed:\n"
            + "\n".join(evidence_errors)
        )
    source = merge_full_corpus_supplement(
        source, supplement, machine_evidence, lane_root
    )
    input_errors = validate_against_schema(source, input_schema, input_schema)
    if input_errors:
        raise ValueError("input schema validation failed:\n" + "\n".join(input_errors))

    output_a = make_output(source, lane_root, args.require_bound_targets)
    output_errors = validate_against_schema(output_a, output_schema, output_schema)
    if output_errors:
        raise ValueError("output schema validation failed:\n" + "\n".join(output_errors))
    files_a = add_manifest(build_files(output_a), output_a)
    validate_projections(files_a)

    output_b = make_output(source, lane_root, args.require_bound_targets)
    files_b = add_manifest(build_files(output_b), output_b)
    if files_a != files_b:
        raise ValueError("two independent in-memory export runs were not byte-identical")

    if args.check:
        check_files(dist, files_a)
        action = "checked"
    else:
        write_files(dist, files_a)
        action = "wrote"

    if args.show_target_hashes:
        print("TARGET HASH GUARD VALUES")
        hash_seeds = list(source["file_units"]) + list(source["assets"])
        for native_seed in source["native_file_units"]:
            print(f"{native_seed['id']} {native_seed['expected_content_sha256']}")
        for seed in hash_seeds:
            relative = seed.get("target_path")
            if relative:
                current = sha256_file(safe_join(safe_join(lane_root, source["path_roots"]["target"]), relative))
                print(f"{seed['id']} {current}")
    print(
        f"{action} {len(files_a)} deterministic files; "
        f"units={len(output_a['units'])}; segments={len(output_a['segments'])}; "
        f"relations={len(output_a['relations'])}; target_guards_required={args.require_bound_targets}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # concise CLI failure with nonzero exit
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
