"""Bangun atau periksa resi laboratorium algoritme graf Bab 14.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import Counter
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
    "source/o018-open-solver-lab/requirements.lock",
    "source/o018-open-solver-lab/runtime-receipt.json",
)


def _record(path: Path, displayed_path: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = path.read_bytes()
    return {"bytes": len(payload), "path": displayed_path, "sha256": hashlib.sha256(payload).hexdigest()}


def _serialize(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _combined_plot_hash(plots: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for filename, payload in sorted(plots.items()):
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
    return digest.hexdigest()


def _validate_inventory(plots: dict[str, bytes]) -> None:
    expected = set(PACKAGE_FILES) | {f"plots/{filename}" for filename in plots}
    allowed = set(expected)
    if RECEIPT_PATH.is_file():
        allowed.add(RECEIPT_PATH.name)
    actual = {
        path.relative_to(HERE).as_posix()
        for path in HERE.rglob("*")
        if path.is_file()
    }
    missing, unexpected = expected - actual, actual - allowed
    if missing or unexpected:
        raise RuntimeError(f"inventaris paket tidak tertutup: missing={sorted(missing)} unexpected={sorted(unexpected)}")


def _validate_log(results_payload: bytes) -> None:
    log = (HERE / "verification.log").read_text(encoding="utf-8")
    digest = hashlib.sha256(results_payload).hexdigest()
    check_line = (
        f"CHECK_OK results_bytes={len(results_payload)} results_sha256={digest} "
        "plots=2 exercises=23 algorithm_checks=23"
    )
    required = {
        check_line: 2,
        "unittest: 33 passed, 0 failed, 0 errors": 2,
        "visual_qa: 2 SVG diperiksa pada ukuran asli 960x640": 1,
        "networkx_runtime: unavailable; implementation: pure_stdlib": 1,
        "source_notes_recorded: 4": 1,
        "o018_math_corrections: 0": 1,
        "unresolved_exercises: 0": 1,
    }
    for text, expected_count in required.items():
        actual_count = log.count(text)
        if actual_count != expected_count:
            raise RuntimeError(f"bukti log tidak lengkap untuk {text!r}: {actual_count} != {expected_count}")


def build_receipt() -> dict[str, Any]:
    data = load_data()
    first_results, first_plots = assemble_results(data)
    second_results, second_plots = assemble_results(data)
    first_payload, second_payload = serialize_results(first_results), serialize_results(second_results)
    if first_payload != second_payload or first_plots != second_plots:
        raise RuntimeError("dua regenerasi dalam memori tidak identik")
    failures = compare_outputs(HERE / "results.json", HERE / "plots", first_payload, first_plots)
    if failures:
        raise RuntimeError("keluaran disk tidak cocok: " + " | ".join(failures))
    _validate_log(first_payload)
    _validate_inventory(first_plots)
    artifacts = [_record(HERE / filename, filename) for filename in PACKAGE_FILES]
    artifacts.extend(_record(HERE / "plots" / filename, f"plots/{filename}") for filename in sorted(first_plots))
    runtime_closure = [_record(LANE_ROOT / path, path) for path in RUNTIME_CLOSURE_FILES]
    return {
        "artifacts": artifacts,
        "content_license": data["content_license"],
        "lab_id": data["lab_id"],
        "provenance": data["provenance"],
        "runtime": {
            "closure_files": runtime_closure,
            "implementation": "pure_stdlib",
            "networkx": "not_installed_not_used",
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
        "schema_version": "1.0.0",
        "verification": {
            "algorithm_check_count_per_run": first_results["summary"]["algorithm_check_count"],
            "artifact_count_excluding_receipt": len(artifacts),
            "exercise_count": first_results["summary"]["exercise_count"],
            "method_counts": dict(sorted(Counter(spec["method"] for spec in data["exercises"].values()).items())),
            "o018_math_correction_count": first_results["summary"]["o018_math_correction_count"],
            "plot_accessibility_contract": {"generated_svg_count": len(first_plots), "language": "id-ID", "required_svg_elements": ["title", "desc", "metadata"], "structured_alternatives": True},
            "plots_combined_sha256": _combined_plot_hash(first_plots),
            "results_bytes": len(first_payload),
            "results_regeneration_runs": 2,
            "results_sha256": hashlib.sha256(first_payload).hexdigest(),
            "source_note_ids": [item["id"] for item in data["source_notes"]],
            "tests_failed_per_run": 0,
            "tests_passed_per_run": 33,
            "unresolved_exercises": data["unresolved_exercises"],
            "unittest_runs": 2,
            "verification_date": "2026-08-22",
            "verified_count": first_results["summary"]["verified_count"],
            "visual_qa_svg_count": len(first_plots),
        },
    }


def verify_receipt() -> dict[str, Any]:
    if not RECEIPT_PATH.is_file():
        raise FileNotFoundError(RECEIPT_PATH)
    current = RECEIPT_PATH.read_bytes()
    expected = _serialize(build_receipt())
    if current != expected:
        raise RuntimeError(
            "resi tidak cocok: "
            f"current={hashlib.sha256(current).hexdigest()} expected={hashlib.sha256(expected).hexdigest()}"
        )
    return json.loads(current.decode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="tulis resi baru")
    mode.add_argument("--check", action="store_true", help="periksa resi")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write:
        payload = _serialize(build_receipt())
        RECEIPT_PATH.write_bytes(payload)
        print(f"RECEIPT_WRITE_OK artifacts={len(json.loads(payload)['artifacts'])} bytes={len(payload)} sha256={hashlib.sha256(payload).hexdigest()}")
        return 0
    receipt = verify_receipt()
    payload = RECEIPT_PATH.read_bytes()
    print(f"RECEIPT_CHECK_OK artifacts={len(receipt['artifacts'])} bytes={len(payload)} sha256={hashlib.sha256(payload).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
