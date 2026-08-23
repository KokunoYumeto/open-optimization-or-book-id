"""Bangun atau periksa keluaran laboratorium algoritme graf Bab 14.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from model import evaluate_all, load_data
from plot_svg import generate_plot_payloads


HERE = Path(__file__).resolve().parent


def serialize_results(results: dict) -> bytes:
    return (
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def assemble_results(data: dict) -> tuple[dict, dict[str, bytes]]:
    results = evaluate_all(data)
    plots, records = generate_plot_payloads(data, results)
    for exercise_id, record in records.items():
        results["exercises"][exercise_id]["plot"] = record
    results["summary"]["plot_count"] = len(plots)
    return results, plots


def compare_outputs(
    output_path: Path,
    plots_dir: Path,
    results_payload: bytes,
    plots: dict[str, bytes],
) -> list[str]:
    failures: list[str] = []
    if not output_path.is_file():
        failures.append("results.json hilang")
    elif output_path.read_bytes() != results_payload:
        failures.append("results.json berbeda dari regenerasi")
    actual_names = {
        path.name for path in plots_dir.glob("*.svg") if path.is_file()
    } if plots_dir.is_dir() else set()
    if actual_names != set(plots):
        failures.append(
            f"inventaris SVG berbeda: aktual={sorted(actual_names)} diharapkan={sorted(plots)}"
        )
    for filename, payload in plots.items():
        path = plots_dir / filename
        if not path.is_file():
            failures.append(f"{filename} hilang")
        elif path.read_bytes() != payload:
            failures.append(f"{filename} berbeda dari regenerasi")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="tulis keluaran deterministik")
    mode.add_argument("--check", action="store_true", help="periksa keluaran yang ada")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_data()
    results, plots = assemble_results(data)
    payload = serialize_results(results)
    output_path = HERE / "results.json"
    plots_dir = HERE / "plots"
    if args.write:
        plots_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        for filename, plot_payload in plots.items():
            (plots_dir / filename).write_bytes(plot_payload)
        print(
            "WRITE_OK "
            f"results_bytes={len(payload)} "
            f"results_sha256={hashlib.sha256(payload).hexdigest()} "
            f"plots={len(plots)} exercises={results['summary']['exercise_count']} "
            f"algorithm_checks={results['summary']['algorithm_check_count']}"
        )
        return 0
    failures = compare_outputs(output_path, plots_dir, payload, plots)
    if failures:
        for failure in failures:
            print(f"CHECK_FAIL {failure}")
        return 1
    print(
        "CHECK_OK "
        f"results_bytes={len(payload)} "
        f"results_sha256={hashlib.sha256(payload).hexdigest()} "
        f"plots={len(plots)} exercises={results['summary']['exercise_count']} "
        f"algorithm_checks={results['summary']['algorithm_check_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
