"""Bangun atau periksa resi laboratorium alur kerja Python Bab 12.

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
from run_lab import assemble_results, compare_output, serialize_results


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
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _validate_inventory() -> None:
    expected = set(PACKAGE_FILES)
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
        f"CHECK_OK results_bytes={len(results_payload)} "
        f"results_sha256={digest} exercises=9 solver_calls=25"
    )
    required_counts = {
        check_line: 2,
        "unittest: 22 passed, 0 failed, 0 errors": 2,
        "exercise_coverage: 9/9 verified": 1,
        "solver_terminations: 25 optimal": 1,
        "maximum_solver_violation: 0": 1,
        "source_defects_recorded: 0": 1,
        "o018_math_corrections: 0": 1,
        "unresolved_exercises: 0": 1,
    }
    for text, count in required_counts.items():
        observed = log.count(text)
        if observed != count:
            raise RuntimeError(f"bukti log tidak lengkap untuk {text!r}: {observed} != {count}")


def build_receipt() -> dict[str, Any]:
    data = load_data(HERE / "data.json")
    first = assemble_results(data)
    second = assemble_results(data)
    first_payload = serialize_results(first)
    second_payload = serialize_results(second)
    if first_payload != second_payload:
        raise RuntimeError("dua regenerasi dalam memori tidak identik")
    failures = compare_output(HERE / "results.json", first_payload)
    if failures:
        raise RuntimeError("keluaran disk tidak cocok: " + " | ".join(failures))
    _validate_verification_log(first_payload)
    _validate_inventory()

    artifacts = [
        _record(HERE / filename, filename) for filename in PACKAGE_FILES
    ]
    runtime_closure = [
        _record(LANE_ROOT / relative_path, relative_path)
        for relative_path in RUNTIME_CLOSURE_FILES
    ]
    methods = Counter(spec["method"] for spec in data["exercises"].values())
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
            "exercise_count": first["summary"]["exercise_count"],
            "maximum_solver_violation": first["summary"]["maximum_solver_violation"],
            "method_counts": dict(sorted(methods.items())),
            "o018_math_correction_count": first["summary"]["o018_math_correction_count"],
            "results_bytes": len(first_payload),
            "results_regeneration_runs": 2,
            "results_sha256": hashlib.sha256(first_payload).hexdigest(),
            "solver_call_count_per_run": first["summary"]["solver_call_count"],
            "solver_termination_counts": first["summary"]["solver_termination_counts"],
            "source_defect_ids": [],
            "tests_failed_per_run": 0,
            "tests_passed_per_run": 22,
            "unresolved_exercises": [],
            "unittest_runs": 2,
            "verification_date": "2026-08-22",
            "verified_count": first["summary"]["verified_count"],
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
            f"current={hashlib.sha256(current).hexdigest()} "
            f"expected={hashlib.sha256(expected).hexdigest()}"
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
        f"artifacts={len(receipt['artifacts'])} bytes={len(payload)} "
        f"sha256={hashlib.sha256(payload).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
