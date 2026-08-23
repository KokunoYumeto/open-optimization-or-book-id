"""Jalankan laboratorium kaus dan tulis hasil JSON deterministik.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from model import load_data, solve_model


HERE = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("lp", "integer", "both"),
        default="both",
        help="domain variabel yang akan diselesaikan",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "results.json",
        help="lokasi hasil JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_data(HERE / "data.json")
    modes = ("lp", "integer") if args.mode == "both" else (args.mode,)
    results = {
        "schema_version": "1.0.0",
        "lab_id": data["lab_id"],
        "modes": {
            mode: solve_model(data, integer=mode == "integer") for mode in modes
        },
    }
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

