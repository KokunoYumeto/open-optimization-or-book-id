"""Jalankan laboratorium pemrograman bilangan bulat secara deterministik.

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
    plot_payloads, plot_records = generate_plot_payloads(data)
    for exercise_id, exercise in results["exercises"].items():
        exercise["plot"] = plot_records[exercise_id]
    results["summary"]["plot_count"] = len(plot_payloads)
    return results, plot_payloads


def compare_outputs(
    results_path: Path,
    plots_path: Path,
    expected_results: bytes,
    expected_plots: dict[str, bytes],
) -> list[str]:
    failures: list[str] = []
    if not results_path.is_file():
        failures.append(f"hasil hilang: {results_path}")
    elif results_path.read_bytes() != expected_results:
        failures.append(
            "results.json berbeda: "
            f"disk={hashlib.sha256(results_path.read_bytes()).hexdigest()} "
            f"expected={hashlib.sha256(expected_results).hexdigest()}"
        )
    actual_plot_files = (
        {path.name for path in plots_path.glob("*.svg")}
        if plots_path.is_dir()
        else set()
    )
    if actual_plot_files != set(expected_plots):
        failures.append(
            f"inventaris plot berbeda: disk={sorted(actual_plot_files)} "
            f"expected={sorted(expected_plots)}"
        )
    for filename, payload in sorted(expected_plots.items()):
        path = plots_path / filename
        if path.is_file() and path.read_bytes() != payload:
            failures.append(
                f"plot berbeda {filename}: "
                f"disk={hashlib.sha256(path.read_bytes()).hexdigest()} "
                f"expected={hashlib.sha256(payload).hexdigest()}"
            )
    return failures


def write_outputs(
    results_path: Path,
    plots_path: Path,
    results_payload: bytes,
    plot_payloads: dict[str, bytes],
) -> None:
    results_path.write_bytes(results_payload)
    plots_path.mkdir(parents=True, exist_ok=True)
    for path in plots_path.glob("*.svg"):
        if path.name not in plot_payloads:
            path.unlink()
    for filename, payload in sorted(plot_payloads.items()):
        (plots_path / filename).write_bytes(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write",
        action="store_true",
        help="tulis results.json dan SVG (modus baku)",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="bandingkan keluaran disk dengan regenerasi bersih",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_data(HERE / "data.json")
    results, plots = assemble_results(data)
    payload = serialize_results(results)
    results_path = HERE / "results.json"
    plots_path = HERE / "plots"
    if args.check:
        failures = compare_outputs(results_path, plots_path, payload, plots)
        if failures:
            for failure in failures:
                print(f"CHECK_FAIL {failure}")
            return 1
        print(
            "CHECK_OK "
            f"results_bytes={len(payload)} "
            f"results_sha256={hashlib.sha256(payload).hexdigest()} "
            f"plots={len(plots)} "
            f"exercises={results['summary']['exercise_count']} "
            f"solver_calls={results['summary']['solver_call_count']} "
            f"maximum_violation={results['summary']['maximum_solver_violation']}"
        )
        return 0
    write_outputs(results_path, plots_path, payload, plots)
    print(
        "WRITE_OK "
        f"results_bytes={len(payload)} "
        f"results_sha256={hashlib.sha256(payload).hexdigest()} "
        f"plots={len(plots)} "
        f"exercises={results['summary']['exercise_count']} "
        f"solver_calls={results['summary']['solver_call_count']} "
        f"maximum_violation={results['summary']['maximum_solver_violation']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
