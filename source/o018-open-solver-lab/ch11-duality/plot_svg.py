"""Bangun SVG id-ID yang dapat diakses untuk laboratorium dualitas.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any


WIDTH = 960
HEIGHT = 680
LEFT = 100
RIGHT = 900
TOP = 72
BOTTOM = 580
XMAX = 7
YMAX = 5


def _x(value: float) -> float:
    return LEFT + value * (RIGHT - LEFT) / XMAX


def _y(value: float) -> float:
    return BOTTOM - value * (BOTTOM - TOP) / YMAX


def _fmt(value: float) -> str:
    rounded = round(value, 3)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def _line(x1: float, y1: float, x2: float, y2: float, css: str) -> str:
    return (
        f'<line x1="{_fmt(_x(x1))}" y1="{_fmt(_y(y1))}" '
        f'x2="{_fmt(_x(x2))}" y2="{_fmt(_y(y2))}" class="{css}" />'
    )


def _meal_kit_svg() -> bytes:
    metadata = {
        "alternative_text": {
            "active_constraints": ["y1 ≥ 4", "y2 ≥ 2"],
            "conclusion": "Minimum 10y1 + 12y2 dicapai di (4,2) dengan nilai 64.",
            "feasible_region": "Daerah di kanan y1=4 dan di atas y2=2.",
            "inactive_constraints": [
                "y1 + 2y2 ≥ 3",
                "2y1 ≥ 2",
                "y2 ≥ 1",
                "y1 + 3y2 ≥ 5",
            ],
        },
        "content_license": "CC-BY-SA-4.0",
        "exercise_id": "11.16",
        "language": "id-ID",
        "renderer": "o018.ch11.plot-svg.v1",
    }
    machine = html.escape(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True), quote=False
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
            'aria-labelledby="title desc" xml:lang="id-ID">'
        ),
        '<title id="title">Daerah layak dual Latihan 11.16</title>',
        (
            '<desc id="desc">Daerah layak berada di kanan garis y1 sama dengan 4 '
            'dan di atas garis y2 sama dengan 2. Titik optimum adalah (4,2) '
            'dengan nilai tujuan 64.</desc>'
        ),
        f'<metadata>{machine}</metadata>',
        '<defs><style><![CDATA[',
        '.axis{stroke:#172554;stroke-width:2}.grid{stroke:#cbd5e1;stroke-width:1}',
        '.inactive{stroke:#94a3b8;stroke-width:2;stroke-dasharray:7 7}',
        '.active{stroke:#0f766e;stroke-width:4}.level{stroke:#7e22ce;stroke-width:3;stroke-dasharray:10 7}',
        '.label{font:18px system-ui,sans-serif;fill:#172554}.small{font:15px system-ui,sans-serif;fill:#334155}',
        '.heading{font:bold 25px system-ui,sans-serif;fill:#0f172a}.opt{fill:#dc2626;stroke:#fff;stroke-width:3}',
        ']]></style></defs>',
        '<rect width="960" height="680" fill="#f8fafc" />',
        '<text x="480" y="38" text-anchor="middle" class="heading">Latihan 11.16 — harga sumber daya dual</text>',
        (
            f'<rect x="{_fmt(_x(4))}" y="{_fmt(_y(5))}" '
            f'width="{_fmt(_x(7)-_x(4))}" height="{_fmt(_y(2)-_y(5))}" '
            'fill="#99f6e4" fill-opacity="0.55" />'
        ),
    ]
    for tick in range(0, XMAX + 1):
        lines.append(_line(tick, 0, tick, YMAX, "grid"))
        lines.append(
            f'<text x="{_fmt(_x(tick))}" y="608" text-anchor="middle" class="small">{tick}</text>'
        )
    for tick in range(0, YMAX + 1):
        lines.append(_line(0, tick, XMAX, tick, "grid"))
        lines.append(
            f'<text x="78" y="{_fmt(_y(tick)+5)}" text-anchor="end" class="small">{tick}</text>'
        )
    lines.extend(
        [
            _line(0, 0, XMAX, 0, "axis"),
            _line(0, 0, 0, YMAX, "axis"),
            _line(1, 0, 1, YMAX, "inactive"),
            _line(0, 1, XMAX, 1, "inactive"),
            _line(0, 1.5, 3, 0, "inactive"),
            _line(0, 5 / 3, 5, 0, "inactive"),
            _line(4, 0, 4, YMAX, "active"),
            _line(0, 2, XMAX, 2, "active"),
            _line(0.4, 5, 6.4, 0, "level"),
            '<text x="900" y="630" text-anchor="end" class="label">y₁ (jam dapur)</text>',
            '<text x="27" y="92" class="label">y₂</text>',
            f'<circle cx="{_fmt(_x(4))}" cy="{_fmt(_y(2))}" r="9" class="opt" />',
            f'<text x="{_fmt(_x(4)+14)}" y="{_fmt(_y(2)-14)}" class="label">optimum (4,2), nilai 64</text>',
            f'<text x="{_fmt(_x(4)+8)}" y="{_fmt(_y(4.6))}" class="small">y₁ ≥ 4 (aktif)</text>',
            f'<text x="{_fmt(_x(5.1))}" y="{_fmt(_y(2)-9)}" class="small">y₂ ≥ 2 (aktif)</text>',
            '<rect x="110" y="626" width="18" height="18" fill="#99f6e4" fill-opacity="0.7" />',
            '<text x="138" y="641" class="small">daerah layak</text>',
            '<line x1="290" y1="636" x2="340" y2="636" class="level" />',
            '<text x="350" y="641" class="small">10y₁+12y₂=64</text>',
            '</svg>',
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def generate_plot_payloads(
    data: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    if "11.16" not in data["exercises"]:
        raise ValueError("Latihan 11.16 tidak tersedia untuk visual")
    plots = {"ex11-16.svg": _meal_kit_svg()}
    records: dict[str, dict[str, Any]] = {}
    for exercise_id in data["exercise_order"]:
        if exercise_id == "11.16":
            payload = plots["ex11-16.svg"]
            records[exercise_id] = {
                "bytes": len(payload),
                "path": "plots/ex11-16.svg",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "status": "generated",
            }
        else:
            records[exercise_id] = {
                "reason": "visual tidak diperlukan untuk sertifikat latihan ini",
                "status": "not_generated",
            }
    return plots, records


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "plots" / "ex11-16.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_meal_kit_svg())

