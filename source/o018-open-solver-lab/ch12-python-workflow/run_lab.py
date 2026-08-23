"""Jalankan laboratorium alur kerja Python Bab 12 secara deterministik.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from model import evaluate_all, load_data


HERE = Path(__file__).resolve().parent


def serialize_results(results: dict) -> bytes:
    return (json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def assemble_results(data: dict) -> dict:
    return evaluate_all(data)


def compare_output(output_path: Path, payload: bytes) -> list[str]:
    if not output_path.is_file():
        return [f"missing={output_path}"]
    current = output_path.read_bytes()
    if current != payload:
        return [
            "results_mismatch="
            f"{hashlib.sha256(current).hexdigest()}!={hashlib.sha256(payload).hexdigest()}"
        ]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results.json")
    parser.add_argument("--check", action="store_true", help="bandingkan byte tanpa menulis")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = assemble_results(load_data(HERE / "data.json"))
    payload = serialize_results(results)
    digest = hashlib.sha256(payload).hexdigest()
    if args.check:
        failures = compare_output(args.output, payload)
        if failures:
            print("CHECK_FAIL " + " | ".join(failures))
            return 1
        print(
            "CHECK_OK "
            f"results_bytes={len(payload)} results_sha256={digest} "
            f"exercises={results['summary']['exercise_count']} "
            f"solver_calls={results['summary']['solver_call_count']}"
        )
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(
        "WRITE_OK "
        f"results_bytes={len(payload)} results_sha256={digest} "
        f"exercises={results['summary']['exercise_count']} "
        f"solver_calls={results['summary']['solver_call_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
