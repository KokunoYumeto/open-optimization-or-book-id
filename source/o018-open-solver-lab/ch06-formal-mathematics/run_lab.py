"""Jalankan laboratorium Bab 6 secara deterministik.

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
    output_path: Path,
    plots_dir: Path,
    results_payload: bytes,
    plots: dict[str, bytes],
) -> list[str]:
    failures: list[str] = []
    expected_digest = hashlib.sha256(results_payload).hexdigest()
    if not output_path.is_file():
        failures.append(f"missing={output_path}")
    elif output_path.read_bytes() != results_payload:
        failures.append(
            "results_mismatch="
            f"{hashlib.sha256(output_path.read_bytes()).hexdigest()}!={expected_digest}"
        )
    expected_names = set(plots)
    actual_names = (
        {path.name for path in plots_dir.glob("*.svg")}
        if plots_dir.is_dir()
        else set()
    )
    if actual_names != expected_names:
        failures.append(
            "plot_inventory_mismatch="
            f"expected:{sorted(expected_names)};actual:{sorted(actual_names)}"
        )
    for filename, expected_payload in plots.items():
        path = plots_dir / filename
        if not path.is_file():
            failures.append(f"plot_missing={path}")
        elif path.read_bytes() != expected_payload:
            failures.append(f"plot_mismatch={path}")
    return failures


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
        failures = compare_outputs(args.output, args.plots_dir, payload, plots)
        if failures:
            print("CHECK_FAIL " + " | ".join(failures))
            return 1
        print(
            "CHECK_OK "
            f"results_bytes={len(payload)} results_sha256={digest} "
            f"plots={len(plots)} exercises={results['summary']['exercise_count']} "
            f"solver_calls={results['summary']['solver_call_count']}"
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.plots_dir.mkdir(parents=True, exist_ok=True)
    existing_names = {path.name for path in args.plots_dir.glob("*.svg")}
    unexpected = existing_names - set(plots)
    if unexpected:
        raise RuntimeError(
            "direktori plot memuat SVG tak terkelola; hapus secara eksplisit: "
            + ", ".join(sorted(unexpected))
        )
    for filename, plot_payload in plots.items():
        (args.plots_dir / filename).write_bytes(plot_payload)
    args.output.write_bytes(payload)
    print(
        "WRITE_OK "
        f"results_bytes={len(payload)} results_sha256={digest} "
        f"plots={len(plots)} exercises={results['summary']['exercise_count']} "
        f"solver_calls={results['summary']['solver_call_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
