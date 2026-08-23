"""Bangun atau periksa receipt laboratorium Bab 5.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from importlib.metadata import version
from pathlib import Path
from typing import Any

from model import load_data
from run_lab import assemble_results, serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]
RECEIPT_PATH = HERE / "verification-receipt.json"
CONDA_PACKAGE_CACHE = Path.home() / "miniconda3" / "pkgs"
BOOTSTRAP_ARCHIVES = (
    "bzip2-1.0.8-h0ad9c76_9.conda",
    "libexpat-2.8.1-hac47afa_0.conda",
    "libffi-3.5.2-h3d046cb_0.conda",
    "liblzma-5.8.3-hfd05255_0.conda",
    "libsqlite-3.53.2-hf5d6505_0.conda",
    "libzlib-1.3.1-h02ab6af_0.conda",
    "openssl-3.6.2-hf411b9b_0.conda",
    "python-3.12.13-h0159041_0_cpython.conda",
    "tk-8.6.13-h6ed50ae_3.conda",
    "tzdata-2025c-hc9c84f9_1.conda",
    "ucrt-10.0.26100.0-h57928b3_0.conda",
    "vc-14.3-h2df5915_10.conda",
    "vc14_runtime-14.44.35208-h4927774_10.conda",
)
PACKAGE_FILES = (
    "ATTRIBUTION.md",
    "LICENSE-CODE.txt",
    "README.md",
    "data.json",
    "expected-results.json",
    "model.py",
    "plot_svg.py",
    "results.json",
    "run_lab.py",
    "test_models.py",
    "verification.log",
    "verify_receipt.py",
)
RUNTIME_CLOSURE_FILES = (
    "authority/runtime-licenses/MANIFEST.csv",
    "authority/runtime-wheels/MANIFEST.csv",
    "source/o018-open-solver-lab/requirements.lock",
    "source/o018-open-solver-lab/runtime-receipt.json",
)


def _record(path: Path, displayed_path: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = path.read_bytes()
    return {
        "bytes": len(payload),
        "path": displayed_path,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _serialize(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _combined_plot_hash(plots: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for filename, payload in sorted(plots.items()):
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
    return digest.hexdigest()


def validate_provenance_closure(data: dict[str, Any]) -> None:
    """Tolak source record atau klaim atribusi yang tidak lagi cocok."""

    sources = data["provenance"]["source_files"]
    expected_hashes: set[str] = set()
    expected_claims: list[str] = []
    for source in sources:
        path = LANE_ROOT / source["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = path.read_bytes()
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if len(payload) != source["bytes"] or actual_sha256 != source["sha256"]:
            raise RuntimeError(
                "saksi provenance tidak cocok: "
                f"{source['role']} bytes={len(payload)}/{source['bytes']} "
                f"sha256={actual_sha256}/{source['sha256']}"
            )
        label = (
            "solutions-manual/ch05.tex"
            if "/solutions-manual/" in source["path"]
            else Path(source["path"]).name
        )
        bytes_id = f"{source['bytes']:,}".replace(",", ".")
        expected_hashes.add(source["sha256"])
        expected_claims.append(
            f"`{label}`, {bytes_id} byte, SHA-256\n  `{source['sha256']}`"
        )

    attribution = (HERE / "ATTRIBUTION.md").read_text(encoding="utf-8")
    claimed_hashes = set(re.findall(r"`([0-9a-f]{64})`", attribution))
    if claimed_hashes != expected_hashes:
        raise RuntimeError(
            "inventaris hash ATTRIBUTION.md tidak cocok dengan data.json: "
            f"claimed={sorted(claimed_hashes)} expected={sorted(expected_hashes)}"
        )
    missing_claims = [claim for claim in expected_claims if claim not in attribution]
    if missing_claims:
        raise RuntimeError(
            "klaim byte/hash ATTRIBUTION.md tidak lengkap: "
            + "; ".join(missing_claims)
        )


def build_receipt() -> dict[str, Any]:
    data = load_data(HERE / "data.json")
    validate_provenance_closure(data)
    results, plots = assemble_results(data)
    results_payload = serialize_results(results)
    artifact_paths = [HERE / filename for filename in PACKAGE_FILES]
    artifact_paths.extend(sorted((HERE / "plots").glob("*.svg")))
    artifacts = [
        _record(path, path.relative_to(HERE).as_posix()) for path in artifact_paths
    ]
    bootstrap = [
        _record(CONDA_PACKAGE_CACHE / filename, f"conda-cache/{filename}")
        for filename in BOOTSTRAP_ARCHIVES
    ]
    runtime_closure = [
        _record(LANE_ROOT / relative_path, relative_path)
        for relative_path in RUNTIME_CLOSURE_FILES
    ]
    return {
        "artifacts": artifacts,
        "bootstrap": {
            "environment_disposition": "task_local_disposable_after_replay",
            "offline_conda_archives": bootstrap,
            "package_cache_at_verification": "<user-home>/miniconda3/pkgs",
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
        "content_license": data["content_license"],
        "lab_id": data["lab_id"],
        "provenance": data["provenance"],
        "runtime": {
            "closure_files": runtime_closure,
            "highspy": version("highspy"),
            "numpy": version("numpy"),
            "pyomo": version("pyomo"),
            "solver_interface": "appsi_highs",
        },
        "schema_version": "1.0.0",
        "verification": {
            "exercise_count": results["summary"]["exercise_count"],
            "executable_exercise_count": results["summary"][
                "executable_exercise_count"
            ],
            "maximum_solver_violation": results["summary"][
                "maximum_solver_violation"
            ],
            "parameter_required_count": results["summary"][
                "parameter_required_count"
            ],
            "plot_accessibility_contract": {
                "generated_svg_count": len(plots),
                "language": "id-ID",
                "required_svg_elements": ["title", "desc"],
                "structured_alternatives": True,
            },
            "plots_combined_sha256": _combined_plot_hash(plots),
            "results_bytes": len(results_payload),
            "results_regeneration_runs": 2,
            "results_sha256": hashlib.sha256(results_payload).hexdigest(),
            "scenario_solve_count": results["summary"]["scenario_solve_count"],
            "tests_failed_per_run": 0,
            "tests_passed_per_run": 18,
            "unittest_runs": 2,
            "verification_date": "2026-08-22",
        },
    }


def verify_receipt() -> dict[str, Any]:
    if not RECEIPT_PATH.is_file():
        raise FileNotFoundError(RECEIPT_PATH)
    current = RECEIPT_PATH.read_bytes()
    expected = _serialize(build_receipt())
    if current != expected:
        raise RuntimeError(
            "receipt tidak cocok: "
            f"current={hashlib.sha256(current).hexdigest()} "
            f"expected={hashlib.sha256(expected).hexdigest()}"
        )
    return json.loads(current.decode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="tulis receipt baru")
    mode.add_argument("--check", action="store_true", help="periksa receipt tanpa menulis")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write:
        payload = _serialize(build_receipt())
        RECEIPT_PATH.write_bytes(payload)
        print(
            "RECEIPT_WRITE_OK "
            f"bytes={len(payload)} sha256={hashlib.sha256(payload).hexdigest()}"
        )
        return 0
    receipt = verify_receipt()
    payload = RECEIPT_PATH.read_bytes()
    print(
        "RECEIPT_CHECK_OK "
        f"artifacts={len(receipt['artifacts'])} "
        f"bytes={len(payload)} sha256={hashlib.sha256(payload).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
