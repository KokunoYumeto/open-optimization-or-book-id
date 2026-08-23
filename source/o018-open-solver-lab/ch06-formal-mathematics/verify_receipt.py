"""Bangun atau periksa receipt laboratorium Bab 6.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from typing import Any

from model import load_data
from run_lab import assemble_results, compare_outputs, serialize_results


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]
RECEIPT_PATH = HERE / "verification-receipt.json"
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


def _validate_inventory(plots: dict[str, bytes]) -> None:
    expected = set(PACKAGE_FILES)
    expected.update(f"plots/{filename}" for filename in plots)
    allowed = set(expected)
    if RECEIPT_PATH.is_file():
        allowed.add(RECEIPT_PATH.name)
    actual = {
        path.relative_to(HERE).as_posix()
        for path in HERE.rglob("*")
        if path.is_file()
    }
    missing = expected - actual
    unexpected = actual - allowed
    if missing or unexpected:
        raise RuntimeError(
            f"inventaris paket tidak tertutup: missing={sorted(missing)} "
            f"unexpected={sorted(unexpected)}"
        )


def _validate_verification_log(results_payload: bytes) -> None:
    log = (HERE / "verification.log").read_text(encoding="utf-8")
    digest = hashlib.sha256(results_payload).hexdigest()
    check_line = (
        f"CHECK_OK results_bytes={len(results_payload)} results_sha256={digest} "
        "plots=5 exercises=12 solver_calls=5"
    )
    required_counts = {
        check_line: 2,
        "unittest: 21 passed, 0 failed, 0 errors": 2,
        "visual_qa: 5 SVG diperiksa pada raster 1440x1040": 1,
        "source_math_corrections: 0": 1,
        "implementation_visual_corrections: 2": 1,
    }
    for text, count in required_counts.items():
        if log.count(text) != count:
            raise RuntimeError(
                f"bukti log tidak lengkap untuk {text!r}: {log.count(text)} != {count}"
            )


def build_receipt() -> dict[str, Any]:
    data = load_data(HERE / "data.json")
    first_results, first_plots = assemble_results(data)
    second_results, second_plots = assemble_results(data)
    first_payload = serialize_results(first_results)
    second_payload = serialize_results(second_results)
    if first_payload != second_payload or first_plots != second_plots:
        raise RuntimeError("dua regenerasi dalam memori tidak identik")
    output_failures = compare_outputs(
        HERE / "results.json", HERE / "plots", first_payload, first_plots
    )
    if output_failures:
        raise RuntimeError("keluaran disk tidak cocok: " + " | ".join(output_failures))
    _validate_verification_log(first_payload)
    _validate_inventory(first_plots)

    artifact_paths = [HERE / filename for filename in PACKAGE_FILES]
    artifact_paths.extend(sorted((HERE / "plots").glob("*.svg")))
    artifacts = [
        _record(path, path.relative_to(HERE).as_posix()) for path in artifact_paths
    ]
    runtime_closure = [
        _record(LANE_ROOT / relative_path, relative_path)
        for relative_path in RUNTIME_CLOSURE_FILES
    ]
    methods = Counter(
        spec["method"] for spec in data["exercises"].values()
    )
    return {
        "artifacts": artifacts,
        "content_license": data["content_license"],
        "lab_id": data["lab_id"],
        "provenance": data["provenance"],
        "runtime": {
            "closure_files": runtime_closure,
            "highspy": version("highspy"),
            "numpy": version("numpy"),
            "pyomo": version("pyomo"),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "solver_interface": "appsi_highs",
        },
        "schema_version": "1.0.0",
        "verification": {
            "artifact_count_excluding_receipt": len(artifacts),
            "correction_count": first_results["summary"]["correction_count"],
            "exercise_count": first_results["summary"]["exercise_count"],
            "implementation_visual_corrections": [
                "uniform_coordinate_aspect_ratio_for_all_five_svgs",
                "relocated_three_annotations_after_readable_raster_review",
            ],
            "maximum_solver_violation": first_results["summary"][
                "maximum_solver_violation"
            ],
            "method_counts": dict(sorted(methods.items())),
            "plot_accessibility_contract": {
                "generated_svg_count": len(first_plots),
                "language": "id-ID",
                "required_svg_elements": ["title", "desc", "metadata"],
                "structured_alternatives": True,
                "uniform_coordinate_aspect_ratio": True,
            },
            "plots_combined_sha256": _combined_plot_hash(first_plots),
            "results_bytes": len(first_payload),
            "results_regeneration_runs": 2,
            "results_sha256": hashlib.sha256(first_payload).hexdigest(),
            "solver_call_count_per_run": first_results["summary"][
                "solver_call_count"
            ],
            "tests_failed_per_run": 0,
            "tests_passed_per_run": 21,
            "underdetermined_count": first_results["summary"][
                "underdetermined_count"
            ],
            "unittest_runs": 2,
            "verification_date": "2026-08-22",
            "verified_count": first_results["summary"]["verified_count"],
            "visual_qa_svg_count": 5,
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
            f"artifacts={len(json.loads(payload)['artifacts'])} "
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
