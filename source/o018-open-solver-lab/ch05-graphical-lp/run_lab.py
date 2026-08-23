"""Jalankan laboratorium grafis Bab 5 secara deterministik.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from model import load_data, solve_all
from plot_svg import generate_plot_payloads


HERE = Path(__file__).resolve().parent


def serialize_results(results: dict) -> bytes:
    return (
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def assemble_results(data: dict) -> tuple[dict, dict[str, bytes]]:
    results = solve_all(data)
    plot_payloads, plot_records = generate_plot_payloads(data)
    classifications: Counter[str] = Counter()
    solved_count = 0
    maximum_violation = 0.0
    for exercise_id, exercise_result in results["exercises"].items():
        exercise_result["plot"] = plot_records[exercise_id]
        for scenario in exercise_result["scenarios"].values():
            classifications[scenario["classification"]] += 1
            solved_count += 1
            maximum_violation = max(
                maximum_violation,
                float(scenario["execution"].get("maximum_violation", 0.0)),
            )
    results["summary"] = {
        "classification_counts": dict(sorted(classifications.items())),
        "exercise_count": len(data["exercise_order"]),
        "executable_exercise_count": sum(
            spec["model_status"] == "executable"
            for spec in data["exercises"].values()
        ),
        "maximum_solver_violation": maximum_violation,
        "parameter_required_count": sum(
            spec["model_status"] == "parameter_required"
            for spec in data["exercises"].values()
        ),
        "plot_count": len(plot_payloads),
        "scenario_solve_count": solved_count,
    }
    return results, plot_payloads


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "results.json",
        help="lokasi hasil JSON",
    )
    parser.add_argument(
        "--plots-dir",
        type=Path,
        default=HERE / "plots",
        help="direktori keluaran SVG",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="bandingkan semua byte keluaran tanpa menulis",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_data(HERE / "data.json")
    results, plots = assemble_results(data)
    payload = serialize_results(results)
    digest = hashlib.sha256(payload).hexdigest()

    if args.check:
        failures: list[str] = []
        if not args.output.is_file():
            failures.append(f"missing={args.output}")
        elif args.output.read_bytes() != payload:
            failures.append(
                "results_mismatch="
                f"{hashlib.sha256(args.output.read_bytes()).hexdigest()}!={digest}"
            )
        expected_plot_names = set(plots)
        existing_plot_names = (
            {path.name for path in args.plots_dir.glob("*.svg")}
            if args.plots_dir.is_dir()
            else set()
        )
        if existing_plot_names != expected_plot_names:
            failures.append(
                "plot_inventory_mismatch="
                f"expected:{sorted(expected_plot_names)};actual:{sorted(existing_plot_names)}"
            )
        for filename, plot_payload in plots.items():
            path = args.plots_dir / filename
            if not path.is_file():
                failures.append(f"plot_missing={path}")
            elif path.read_bytes() != plot_payload:
                failures.append(f"plot_mismatch={path}")
        if failures:
            print("CHECK_FAIL " + " | ".join(failures))
            return 1
        print(
            "CHECK_OK "
            f"results_bytes={len(payload)} results_sha256={digest} "
            f"plots={len(plots)}"
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.plots_dir.mkdir(parents=True, exist_ok=True)
    for filename, plot_payload in plots.items():
        (args.plots_dir / filename).write_bytes(plot_payload)
    args.output.write_bytes(payload)
    print(
        "WRITE_OK "
        f"results_bytes={len(payload)} results_sha256={digest} "
        f"plots={len(plots)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
