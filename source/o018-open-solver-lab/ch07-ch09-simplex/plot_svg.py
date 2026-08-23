"""Renderer SVG deterministik untuk tiga geometri simpleks yang material.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from html import escape
from typing import Any, Callable


WIDTH = 960
HEIGHT = 680
PLOT_IDS = ("7.15", "7.17", "9.12")


def _frame(
    exercise_id: str,
    title: str,
    description: str,
    alternative: dict[str, Any],
    body: str,
) -> bytes:
    slug = exercise_id.replace(".", "-")
    metadata = {
        "alternative_text": alternative,
        "content_license": "CC BY-SA 4.0",
        "exercise": exercise_id,
        "language": "id-ID",
        "renderer": "o018-local-svg-1.0",
    }
    document = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" lang="id" xml:lang="id-ID" aria-labelledby="title-{slug} desc-{slug}">
  <title id="title-{slug}">{escape(title)}</title>
  <desc id="desc-{slug}">{escape(description)}</desc>
  <metadata>{escape(json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")))}</metadata>
  <defs>
    <marker id="arrow-{slug}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#b42318"/></marker>
    <style><![CDATA[
      .axis{{stroke:#334155;stroke-width:2}}.grid{{stroke:#dbe5ee;stroke-width:1}}.line{{fill:none;stroke:#345995;stroke-width:3}}.secondary{{fill:none;stroke:#6b7280;stroke-width:2;stroke-dasharray:8 6}}.region{{fill:#b8d8f0;fill-opacity:.62;stroke:#176b87;stroke-width:2}}.ray{{fill:none;stroke:#b42318;stroke-width:4}}.point{{fill:#fff;stroke:#13293d;stroke-width:3}}.tie{{fill:#f4b942;stroke:#7c4a03;stroke-width:3}}.label{{font:600 20px 'DejaVu Sans',sans-serif;fill:#13293d}}.small{{font:16px 'DejaVu Sans',sans-serif;fill:#334155}}.heading{{font:700 27px 'DejaVu Sans',sans-serif;fill:#102a43}}.note{{font:17px 'DejaVu Sans',sans-serif;fill:#475569}}
    ]]></style>
  </defs>
  <rect width="960" height="680" fill="#fbfdff"/>
  <text x="58" y="48" class="heading">{escape(title)}</text>
{body}
</svg>
'''
    return document.encode("utf-8")


def _mapper(xmax: float, ymax: float) -> tuple[Callable[[float, float], tuple[float, float]], float]:
    left, right, top, bottom = 92.0, 700.0, 86.0, 610.0
    scale = min((right - left) / xmax, (bottom - top) / ymax)
    used_width = xmax * scale
    used_height = ymax * scale
    x0 = left + ((right - left) - used_width) / 2
    y0 = bottom - ((bottom - top) - used_height) / 2

    def point(x: float, y: float) -> tuple[float, float]:
        return x0 + x * scale, y0 - y * scale

    return point, scale


def _poly(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def _axes(mapper: Callable[[float, float], tuple[float, float]], xmax: int, ymax: int) -> str:
    origin = mapper(0, 0)
    xend = mapper(xmax, 0)
    yend = mapper(0, ymax)
    parts = [
        f'  <line class="axis" x1="{origin[0]:.2f}" y1="{origin[1]:.2f}" x2="{xend[0]:.2f}" y2="{xend[1]:.2f}"/>',
        f'  <line class="axis" x1="{origin[0]:.2f}" y1="{origin[1]:.2f}" x2="{yend[0]:.2f}" y2="{yend[1]:.2f}"/>',
    ]
    for value_ in range(1, xmax + 1):
        x, y = mapper(value_, 0)
        parts.append(f'  <line class="grid" x1="{x:.2f}" y1="{y:.2f}" x2="{x:.2f}" y2="{mapper(value_, ymax)[1]:.2f}"/>')
        parts.append(f'  <text class="small" x="{x - 5:.2f}" y="{y + 25:.2f}">{value_}</text>')
    for value_ in range(1, ymax + 1):
        x, y = mapper(0, value_)
        parts.append(f'  <line class="grid" x1="{x:.2f}" y1="{y:.2f}" x2="{mapper(xmax, value_)[0]:.2f}" y2="{y:.2f}"/>')
        parts.append(f'  <text class="small" x="{x - 28:.2f}" y="{y + 6:.2f}">{value_}</text>')
    parts.append(f'  <text class="label" x="{xend[0] + 14:.2f}" y="{xend[1] + 7:.2f}">x₁</text>')
    parts.append(f'  <text class="label" x="{yend[0] - 9:.2f}" y="{yend[1] - 15:.2f}">x₂</text>')
    return "\n".join(parts)


def _plot_715() -> bytes:
    mapper, _ = _mapper(8, 6)
    vertices = {
        "A": (2.0, 1.0),
        "B": (5.0, 1.0),
        "C": (7.0, 3.0),
        "D": (0.0, 16.0 / 3.0),
        "E": (0.0, 7.0 / 3.0),
    }
    points = [mapper(*vertices[name]) for name in ("A", "B", "C", "D", "E")]
    d = mapper(*vertices["D"])
    c = mapper(*vertices["C"])
    body = [_axes(mapper, 8, 6), f'  <polygon class="region" points="{_poly(points)}"/>']
    body.append(f'  <line class="ray" x1="{d[0]:.2f}" y1="{d[1]:.2f}" x2="{c[0]:.2f}" y2="{c[1]:.2f}" marker-end="url(#arrow-7-15)"/>')
    offsets = {"A": (-28, 26), "B": (-2, 28), "C": (12, -8), "D": (10, -10), "E": (10, 22)}
    for name, point in vertices.items():
        x, y = mapper(*point)
        dx, dy = offsets[name]
        body.append(f'  <circle class="point" cx="{x:.2f}" cy="{y:.2f}" r="7"/>')
        body.append(f'  <text class="label" x="{x + dx:.2f}" y="{y + dy:.2f}">{name}</text>')
    body.extend(
        [
            '  <rect x="728" y="116" width="195" height="215" rx="14" fill="#eef6fb" stroke="#9bbbd1"/>',
            '  <text x="748" y="151" class="label">Pivot D → C</text>',
            '  <text x="748" y="187" class="small">masuk: x₁</text>',
            '  <text x="748" y="219" class="small">keluar: s₃</text>',
            '  <text x="748" y="251" class="small">tetap nol: s₄</text>',
            '  <text x="748" y="293" class="note">Daerah biru = layak</text>',
            '  <text x="92" y="650" class="note">Skala koordinat seragam; segmen merah mengikuti sisi s₄ = 0.</text>',
        ]
    )
    return _frame(
        "7.15",
        "Latihan 7.15 — basis dan pivot pada daerah layak",
        "Poligon layak A-B-C-D-E. Panah merah dari D ke C menunjukkan x1 masuk, s3 keluar, sedangkan s4 tetap nonbasis nol.",
        {"feasible_vertices_in_order": ["A", "B", "C", "D", "E"], "pivot": {"from": "D", "to": "C", "entering": "x1", "leaving": "s3"}},
        "\n".join(body),
    )


def _plot_717() -> bytes:
    mapper, _ = _mapper(5, 5)
    region = [mapper(0, 0), mapper(4, 0), mapper(0, 4)]
    tie = mapper(4, 0)
    first_line = [mapper(0, 4), mapper(4, 0)]
    second_line = [mapper(1.5, 5), mapper(4, 0)]
    body = [
        _axes(mapper, 5, 5),
        f'  <polygon class="region" points="{_poly(region)}"/>',
        f'  <line class="line" x1="{first_line[0][0]:.2f}" y1="{first_line[0][1]:.2f}" x2="{first_line[1][0]:.2f}" y2="{first_line[1][1]:.2f}"/>',
        f'  <line class="secondary" x1="{second_line[0][0]:.2f}" y1="{second_line[0][1]:.2f}" x2="{second_line[1][0]:.2f}" y2="{second_line[1][1]:.2f}"/>',
        f'  <circle class="tie" cx="{tie[0]:.2f}" cy="{tie[1]:.2f}" r="10"/>',
        f'  <text class="label" x="{tie[0] - 48:.2f}" y="{tie[1] - 18:.2f}">(4,0)</text>',
        '  <rect x="724" y="118" width="205" height="248" rx="14" fill="#fff7df" stroke="#d6a11d"/>',
        '  <text x="744" y="154" class="label">Uji rasio x masuk</text>',
        '  <text x="744" y="193" class="small">s₁: 4 / 1 = 4</text>',
        '  <text x="744" y="225" class="small">s₂: 8 / 2 = 4</text>',
        '  <text x="744" y="269" class="small">imbang → degenerat</text>',
        '  <text x="744" y="310" class="note">Dua basis optimal,</text>',
        '  <text x="744" y="337" class="note">satu titik optimal.</text>',
        '  <text x="92" y="650" class="note">Garis penuh: x+y=4. Garis putus: 2x+y=8.</text>',
    ]
    return _frame(
        "7.17",
        "Latihan 7.17 — hasil imbang dan degenerasi",
        "Daerah layak segitiga dengan dua batas bertemu di titik 4,0. Kedua rasio untuk x yang masuk sama dengan empat, sehingga pivot mana pun menyisakan variabel basis nol.",
        {"entering": "x", "minimum_ratio": 4, "tied_leaving_rows": ["s1", "s2"], "degenerate_point": [4, 0]},
        "\n".join(body),
    )


def _plot_912() -> bytes:
    mapper, _ = _mapper(8, 9)
    clipped = [mapper(0, 0), mapper(1, 0), mapper(8, 7), mapper(8, 9), mapper(7, 9), mapper(0, 2)]
    lower = [mapper(1, 0), mapper(8, 7)]
    upper = [mapper(0, 2), mapper(7, 9)]
    start = mapper(1, 0)
    end = mapper(7, 6)
    body = [
        _axes(mapper, 8, 9),
        f'  <polygon class="region" points="{_poly(clipped)}"/>',
        f'  <line class="line" x1="{lower[0][0]:.2f}" y1="{lower[0][1]:.2f}" x2="{lower[1][0]:.2f}" y2="{lower[1][1]:.2f}"/>',
        f'  <line class="line" x1="{upper[0][0]:.2f}" y1="{upper[0][1]:.2f}" x2="{upper[1][0]:.2f}" y2="{upper[1][1]:.2f}"/>',
        f'  <line class="ray" x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}" marker-end="url(#arrow-9-12)"/>',
        f'  <circle class="point" cx="{start[0]:.2f}" cy="{start[1]:.2f}" r="7"/>',
        f'  <text class="label" x="{start[0] - 17:.2f}" y="{start[1] - 16:.2f}">(1,0)</text>',
        '  <rect x="724" y="118" width="205" height="238" rx="14" fill="#fff0ed" stroke="#d47a6a"/>',
        '  <text x="744" y="154" class="label">Sinar sertifikat</text>',
        '  <text x="744" y="194" class="small">x(t)=(1+t,t)</text>',
        '  <text x="744" y="226" class="small">d=(1,1)</text>',
        '  <text x="744" y="258" class="small">s=(0,3)</text>',
        '  <text x="744" y="303" class="small">z(t)=1+2t → ∞</text>',
        '  <text x="92" y="650" class="note">Biru menunjukkan bagian daerah layak yang terlihat; panah berlanjut melewati jendela.</text>',
    ]
    return _frame(
        "9.12",
        "Latihan 9.12 — sinar ketakterbatasan",
        "Daerah layak berupa pita diagonal tak terbatas. Sinar merah berawal di 1,0 dengan arah 1,1; kedua slack tetap 0 dan 3, sementara objektif tumbuh sebagai 1 tambah 2t.",
        {"base_point": [1, 0], "direction": [1, 1], "objective": "1+2t", "visible_window_is_not_a_model_constraint": True},
        "\n".join(body),
    )


def generate_plot_payloads(_data: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    payloads = {
        "ex07-15.svg": _plot_715(),
        "ex07-17.svg": _plot_717(),
        "ex09-12.svg": _plot_912(),
    }
    generated = {"7.15": "ex07-15.svg", "7.17": "ex07-17.svg", "9.12": "ex09-12.svg"}
    records: dict[str, dict[str, Any]] = {}
    for exercise_id in [
        *[f"7.{index}" for index in range(1, 18)],
        *[f"8.{index}" for index in range(1, 10)],
        *[f"9.{index}" for index in range(1, 13)],
    ]:
        if exercise_id not in generated:
            records[exercise_id] = {"status": "not_generated", "reason": "visual tidak menambah informasi material pada jawaban eksak"}
            continue
        filename = generated[exercise_id]
        payload = payloads[filename]
        records[exercise_id] = {
            "bytes": len(payload),
            "path": f"plots/{filename}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "status": "generated",
        }
    return payloads, records
