"""Jalankan pendamping terbuka Bab 4 dan tulis hasil JSON deterministik.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from model import load_data, solve_all


HERE = Path(__file__).resolve().parent


def serialize_results(results: dict) -> bytes:
    return (
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "results.json",
        help="lokasi hasil JSON",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="bandingkan hasil baru dengan berkas keluaran tanpa menulis",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_data(HERE / "data.json")
    payload = serialize_results(solve_all(data))
    digest = hashlib.sha256(payload).hexdigest()
    if args.check:
        if not args.output.is_file():
            print(f"CHECK_FAIL missing={args.output}")
            return 1
        existing = args.output.read_bytes()
        if existing != payload:
            print(
                "CHECK_FAIL "
                f"existing_sha256={hashlib.sha256(existing).hexdigest()} "
                f"generated_sha256={digest}"
            )
            return 1
        print(f"CHECK_OK bytes={len(payload)} sha256={digest}")
        return 0

    args.output.write_bytes(payload)
    print(f"WRITE_OK bytes={len(payload)} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
