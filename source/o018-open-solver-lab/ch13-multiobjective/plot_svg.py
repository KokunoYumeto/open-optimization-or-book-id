"""Renderer SVG deterministik dan dapat diakses untuk laboratorium Bab 13.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any, Callable


PLOT_IDS = ("13.4", "13.7", "13.9")
WIDTH = 900
HEIGHT = 640
LEFT = 92
RIGHT = 36
TOP = 70
BOTTOM = 86


def _mapper(
    xmin: float, xmax: float, ymin: float, ymax: float
) -> tuple[Callable[[float], float], Callable[[float], float]]:
    plot_width = WIDTH - LEFT - RIGHT
    plot_height = HEIGHT - TOP - BOTTOM

    def map_x(number: float) -> float:
        return LEFT + (number - xmin) / (xmax - xmin) * plot_width

    def map_y(number: float) -> float:
        return TOP + (ymax - number) / (ymax - ymin) * plot_height

    return map_x, map_y


def _line(x1: float, y1: float, x2: float, y2: float, style: str) -> str:
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" '
        f'y2="{y2:.2f}" class="{style}"/>'
    )


def _circle(x: float, y: float, style: str, label: str) -> str:
    return (
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8" class="{style}"/>'
        f'<text x="{x + 12:.2f}" y="{y - 10:.2f}" class="point-label">'
        f'{html.escape(label)}</text>'
    )


def _axes(
    map_x: Callable[[float], float],
    map_y: Callable[[float], float],
    xticks: list[float],
    yticks: list[float],
    xlabel: str,
    ylabel: str,
) -> list[str]:
    parts = [
        _line(LEFT, HEIGHT - BOTTOM, WIDTH - RIGHT, HEIGHT - BOTTOM, "axis"),
        _line(LEFT, TOP, LEFT, HEIGHT - BOTTOM, "axis"),
    ]
    for tick in xticks:
        x = map_x(tick)
        parts.append(_line(x, TOP, x, HEIGHT - BOTTOM, "grid"))
        parts.append(
            f'<text x="{x:.2f}" y="{HEIGHT - BOTTOM + 27}" '
            f'class="tick" text-anchor="middle">{tick:g}</text>'
        )
    for tick in yticks:
        y = map_y(tick)
        parts.append(_line(LEFT, y, WIDTH - RIGHT, y, "grid"))
        parts.append(
            f'<text x="{LEFT - 16}" y="{y + 5:.2f}" '
            f'class="tick" text-anchor="end">{tick:g}</text>'
        )
    parts.extend(
        [
            f'<text x="{(LEFT + WIDTH - RIGHT) / 2:.2f}" y="{HEIGHT - 25}" '
            f'class="axis-label" text-anchor="middle">{html.escape(xlabel)}</text>',
            f'<text x="28" y="{(TOP + HEIGHT - BOTTOM) / 2:.2f}" '
            f'class="axis-label" text-anchor="middle" '
            f'transform="rotate(-90 28 {(TOP + HEIGHT - BOTTOM) / 2:.2f})">'
            f'{html.escape(ylabel)}</text>',
        ]
    )
    return parts


def _frame(
    exercise_id: str,
    title: str,
    description: str,
    body: list[str],
    structured_data: dict[str, Any],
) -> bytes:
    title_id = f"title-{exercise_id.replace('.', '-')}"
    desc_id = f"desc-{exercise_id.replace('.', '-')}"
    metadata = {
        "alternative_text": description,
        "exercise_id": exercise_id,
        "language": "id-ID",
        "structured_data": structured_data,
    }
    metadata_text = html.escape(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    )
    payload = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'xml:lang="id-ID" aria-labelledby="{title_id} {desc_id}">',
        f'<title id="{title_id}">{html.escape(title)}</title>',
        f'<desc id="{desc_id}">{html.escape(description)}</desc>',
        f'<metadata>{metadata_text}</metadata>',
        "<style>",
        ".background{fill:#fffdf8}.axis{stroke:#25364a;stroke-width:2}.grid{stroke:#dce3ea;stroke-width:1}",
        ".frontier{fill:none;stroke:#1769aa;stroke-width:4}.hull{fill:none;stroke:#1769aa;stroke-width:4}",
        ".slice{fill:none;stroke:#7c3aed;stroke-width:3;stroke-dasharray:8 6}.supported{fill:#1769aa;stroke:#0b3558;stroke-width:2}",
        ".unsupported{fill:#f59e0b;stroke:#8a4b00;stroke-width:2}.dominated{fill:#a8b0ba;stroke:#59636f;stroke-width:2}",
        ".epsilon{fill:#7c3aed;stroke:#3d176d;stroke-width:2}.point-label{font:600 18px sans-serif;fill:#17212b}",
        ".tick{font:15px sans-serif;fill:#334155}.axis-label{font:600 18px sans-serif;fill:#1e293b}",
        ".heading{font:700 24px sans-serif;fill:#102a43}.note{font:16px sans-serif;fill:#334155}",
        "</style>",
        '<rect class="background" x="0" y="0" width="900" height="640"/>',
        f'<text x="{LEFT}" y="38" class="heading">{html.escape(title)}</text>',
        *body,
        "</svg>",
        "",
    ]
    return "\n".join(payload).encode("utf-8")


def _plot_134(data: dict[str, Any]) -> bytes:
    items = data["cases"]["designs"]["items"]
    by_name = {item["name"]: item for item in items}
    map_x, map_y = _mapper(2, 11, 2, 9)
    body = _axes(map_x, map_y, list(range(2, 12)), list(range(2, 10)), "f1: biaya (lebih kecil lebih baik)", "f2: emisi (lebih kecil lebih baik)")
    frontier = [by_name[name] for name in ("D", "A", "C", "F")]
    points = " ".join(
        f"{map_x(item['f1']):.2f},{map_y(item['f2']):.2f}" for item in frontier
    )
    body.append(f'<polyline points="{points}" class="frontier"/>')
    for item in items:
        style = (
            "unsupported"
            if item["name"] == "A"
            else "supported"
            if item["name"] in {"D", "C", "F"}
            else "dominated"
        )
        body.append(_circle(map_x(item["f1"]), map_y(item["f2"]), style, item["name"]))
    body.extend(
        [
            '<text x="610" y="94" class="note">Biru: didukung jumlah berbobot</text>',
            '<text x="610" y="119" class="note">Jingga: Pareto, tetapi tidak didukung</text>',
            '<text x="610" y="144" class="note">Abu-abu: terdominasi</text>',
            '<text x="620" y="600" class="note">Arah perbaikan: kiri bawah</text>',
        ]
    )
    return _frame(
        "13.4",
        "Latihan 13.4 — batas Pareto desain",
        "Enam desain pada ruang tujuan. D, A, C, dan F membentuk batas Pareto; A berwarna jingga karena tidak pernah optimal untuk jumlah berbobot, sedangkan B dan E terdominasi.",
        body,
        {"pareto": ["D", "A", "C", "F"], "supported": ["D", "C", "F"], "unsupported": ["A"], "dominated": ["B", "E"]},
    )


def _plot_137(_data: dict[str, Any]) -> bytes:
    map_x, map_y = _mapper(0, 6.5, 0, 6.5)
    body = _axes(map_x, map_y, list(range(0, 7)), list(range(0, 7)), "x1", "x2")
    polygon = " ".join(
        f"{map_x(x):.2f},{map_y(y):.2f}" for x, y in ((0, 0), (6, 0), (0, 6), (0, 0))
    )
    frontier = " ".join(
        f"{map_x(x):.2f},{map_y(y):.2f}" for x, y in ((6, 0), (0, 6))
    )
    body.append(f'<polygon points="{polygon}" fill="#dbeafe" stroke="#6b8fb3" stroke-width="2"/>')
    body.append(f'<polyline points="{frontier}" class="frontier"/>')
    table = [(6, 6, 0), (10, 4, 2), (14, 2, 4), (18, 0, 6)]
    for epsilon, x1, x2 in table:
        body.append(_circle(map_x(x1), map_y(x2), "epsilon", f"ε={epsilon}"))
    body.extend(
        [
            '<text x="565" y="95" class="note">Batas Pareto: x1+x2=6</text>',
            '<text x="565" y="121" class="note">f1=18-2t; f2=6+2t</text>',
            '<text x="565" y="147" class="note">Δf1/Δf2 = -1</text>',
        ]
    )
    return _frame(
        "13.7",
        "Latihan 13.7 — penyapuan kendala-epsilon",
        "Segitiga layak dengan sisi Pareto x1 tambah x2 sama dengan 6. Empat titik ungu menunjukkan solusi untuk epsilon 6, 10, 14, dan 18.",
        body,
        {"epsilon_points": [[6, 6, 0], [10, 4, 2], [14, 2, 4], [18, 0, 6]], "frontier": "x1+x2=6"},
    )


def _plot_139(data: dict[str, Any]) -> bytes:
    items = data["cases"]["nonconvex"]["items"]
    by_name = {item["name"]: item for item in items}
    map_x, map_y = _mapper(0, 4.5, 0, 4.5)
    body = _axes(map_x, map_y, [0, 1, 2, 3, 4], [0, 1, 2, 3, 4], "f1 (diminimumkan)", "f2 (diminimumkan)")
    p = by_name["P"]
    r = by_name["R"]
    body.append(_line(map_x(p["f1"]), map_y(p["f2"]), map_x(r["f1"]), map_y(r["f2"]), "hull"))
    for item in items:
        style = "unsupported" if item["name"] == "Q" else "supported"
        body.append(_circle(map_x(item["f1"]), map_y(item["f2"]), style, item["name"]))
    body.extend(
        [
            '<text x="550" y="95" class="note">Selubung bawah: ruas P–R</text>',
            '<text x="550" y="121" class="note">Q optimal Pareto, tetapi tidak didukung</text>',
            '<text x="550" y="147" class="note">Kendala ε=3 memperoleh kembali Q</text>',
        ]
    )
    return _frame(
        "13.9",
        "Latihan 13.9 — titik Pareto yang tidak didukung",
        "Titik P dan R membentuk selubung konveks bawah. Q berada di atas ruas P–R, sehingga tetap optimal Pareto tetapi tidak pernah memenangi jumlah berbobot.",
        body,
        {"lower_convex_hull": ["P", "R"], "pareto": ["P", "Q", "R"], "unsupported": ["Q"]},
    )


def generate_plot_payloads(
    data: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    payloads = {
        "ex13-04.svg": _plot_134(data),
        "ex13-07.svg": _plot_137(data),
        "ex13-09.svg": _plot_139(data),
    }
    filenames = {"13.4": "ex13-04.svg", "13.7": "ex13-07.svg", "13.9": "ex13-09.svg"}
    records: dict[str, dict[str, Any]] = {}
    for exercise_id in data["exercise_order"]:
        if exercise_id in filenames:
            filename = filenames[exercise_id]
            payload = payloads[filename]
            records[exercise_id] = {
                "bytes": len(payload),
                "language": "id-ID",
                "path": f"plots/{filename}",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "status": "generated",
            }
        else:
            records[exercise_id] = {
                "reason": "Latihan ini memiliki alternatif terstruktur dalam sertifikat JSON; SVG tambahan tidak diperlukan.",
                "status": "not_required",
            }
    return payloads, records
