"""Renderer SVG deterministik untuk tiga visual sensitivitas yang material.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import json
from html import escape
from typing import Any, Callable


WIDTH = 960
HEIGHT = 680
PLOT_IDS = ("10.3", "10.11", "10.12")


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
<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" lang="id" xml:lang="id-ID" aria-labelledby="title-{slug} desc-{slug}">
  <title id="title-{slug}">{escape(title)}</title>
  <desc id="desc-{slug}">{escape(description)}</desc>
  <metadata>{escape(json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")))}</metadata>
  <defs>
    <style><![CDATA[
      .axis{{stroke:#334155;stroke-width:2}}.grid{{stroke:#e2e8f0;stroke-width:1}}.segment{{fill:none;stroke:#64748b;stroke-width:4}}.active{{fill:none;stroke:#176b87;stroke-width:6}}.prediction{{fill:none;stroke:#b42318;stroke-width:4;stroke-dasharray:10 7}}.guide{{stroke:#8b5e00;stroke-width:2;stroke-dasharray:7 6}}.point{{fill:#fff;stroke:#13293d;stroke-width:3}}.emphasis{{fill:#f4b942;stroke:#7c4a03;stroke-width:3}}.actual{{fill:#176b87;stroke:#0f4c5c;stroke-width:3}}.label{{font:600 20px 'DejaVu Sans',sans-serif;fill:#13293d}}.small{{font:16px 'DejaVu Sans',sans-serif;fill:#334155}}.heading{{font:700 27px 'DejaVu Sans',sans-serif;fill:#102a43}}.note{{font:17px 'DejaVu Sans',sans-serif;fill:#475569}}
    ]]></style>
  </defs>
  <rect width="960" height="680" fill="#fbfdff"/>
  <text x="58" y="48" class="heading">{escape(title)}</text>
{body}
</svg>
'''
    return document.encode("utf-8")


def _mapper(
    xmax: float, ymax: float
) -> Callable[[float, float], tuple[float, float]]:
    left, right, top, bottom = 92.0, 690.0, 92.0, 590.0

    def point(x: float, y: float) -> tuple[float, float]:
        return (
            left + (right - left) * x / xmax,
            bottom - (bottom - top) * y / ymax,
        )

    return point


def _axes(
    mapper: Callable[[float, float], tuple[float, float]],
    xmax: int,
    ymax: int,
    xticks: list[int],
    yticks: list[int],
    xlabel: str,
    ylabel: str,
) -> str:
    origin = mapper(0, 0)
    xend = mapper(xmax, 0)
    yend = mapper(0, ymax)
    parts = [
        f'  <line class="axis" x1="{origin[0]:.2f}" y1="{origin[1]:.2f}" x2="{xend[0]:.2f}" y2="{xend[1]:.2f}"/>',
        f'  <line class="axis" x1="{origin[0]:.2f}" y1="{origin[1]:.2f}" x2="{yend[0]:.2f}" y2="{yend[1]:.2f}"/>',
    ]
    for tick in xticks:
        x, y = mapper(tick, 0)
        parts.append(
            f'  <line class="grid" x1="{x:.2f}" y1="{y:.2f}" x2="{x:.2f}" y2="{mapper(tick, ymax)[1]:.2f}"/>'
        )
        parts.append(
            f'  <text class="small" x="{x - 8:.2f}" y="{y + 26:.2f}">{tick}</text>'
        )
    for tick in yticks:
        x, y = mapper(0, tick)
        parts.append(
            f'  <line class="grid" x1="{x:.2f}" y1="{y:.2f}" x2="{mapper(xmax, tick)[0]:.2f}" y2="{y:.2f}"/>'
        )
        parts.append(
            f'  <text class="small" x="{x - 43:.2f}" y="{y + 6:.2f}">{tick}</text>'
        )
    parts.append(
        f'  <text class="label" x="{xend[0] + 12:.2f}" y="{xend[1] + 7:.2f}">{escape(xlabel)}</text>'
    )
    parts.append(
        f'  <text class="label" x="{yend[0] - 12:.2f}" y="{yend[1] - 16:.2f}">{escape(ylabel)}</text>'
    )
    return "\n".join(parts)


def _line(
    mapper: Callable[[float, float], tuple[float, float]],
    points: list[tuple[float, float]],
    css_class: str,
) -> str:
    coordinates = " ".join(
        f"{mapper(x, y)[0]:.2f},{mapper(x, y)[1]:.2f}"
        for x, y in points
    )
    return f'  <polyline class="{css_class}" points="{coordinates}"/>'


def _circle(
    mapper: Callable[[float, float], tuple[float, float]],
    point: tuple[float, float],
    css_class: str,
) -> str:
    x, y = mapper(*point)
    return (
        f'  <circle class="{css_class}" cx="{x:.2f}" cy="{y:.2f}" r="8"/>'
    )


def _plot_103() -> bytes:
    mapper = _mapper(8, 70)
    x3 = mapper(3, 0)[0]
    x6 = mapper(6, 0)[0]
    body = [
        _axes(mapper, 8, 70, list(range(0, 9)), list(range(0, 71, 10)), "c₁", "z*"),
        _line(mapper, [(0, 30), (3, 30)], "segment"),
        _line(mapper, [(3, 30), (6, 48)], "active"),
        _line(mapper, [(6, 48), (8, 64)], "segment"),
        f'  <line class="guide" x1="{x3:.2f}" y1="92" x2="{x3:.2f}" y2="590"/>',
        f'  <line class="guide" x1="{x6:.2f}" y1="92" x2="{x6:.2f}" y2="590"/>',
        _circle(mapper, (3, 30), "emphasis"),
        _circle(mapper, (6, 48), "emphasis"),
        '  <rect x="720" y="118" width="210" height="258" rx="14" fill="#eef6fb" stroke="#9bbbd1"/>',
        '  <text x="740" y="154" class="label">Basis saat ini</text>',
        '  <text x="740" y="193" class="small">3 ≤ c₁ ≤ 6</text>',
        '  <text x="740" y="225" class="small">(x₁,x₂)=(6,4)</text>',
        '  <text x="740" y="257" class="small">z*=12+6c₁</text>',
        '  <text x="740" y="307" class="note">Di luar rentang,</text>',
        '  <text x="740" y="335" class="note">basis berganti.</text>',
        '  <text x="92" y="648" class="note">Segmen biru adalah rentang koefisien yang mempertahankan basis optimal.</text>',
    ]
    return _frame(
        "10.3",
        "Latihan 10.3 — nilai optimal terhadap c₁",
        "Grafik nilai optimal program linier sebagai fungsi koefisien c1. Segmen biru dari 3 hingga 6 memiliki rumus 12 tambah 6c1; di luar kedua titik itu basis optimal berubah.",
        {
            "active_basis_interval": [3, 6],
            "piecewise_value": [
                {"domain": "c1<=3", "formula": "30"},
                {"domain": "3<=c1<=6", "formula": "12+6*c1"},
                {"domain": "c1>=6", "formula": "8*c1"},
            ],
        },
        "\n".join(body),
    )


def _plot_1011() -> bytes:
    mapper = _mapper(3, 3)
    kink = mapper(2, 2)
    body = [
        _axes(mapper, 3, 3, [0, 1, 2, 3], [0, 1, 2, 3], "b₃", "z*"),
        _line(mapper, [(0, 0), (2, 2)], "active"),
        _line(mapper, [(2, 2), (3, 2)], "segment"),
        _circle(mapper, (2, 2), "emphasis"),
        f'  <text class="label" x="{kink[0] - 58:.2f}" y="{kink[1] - 18:.2f}">(2,2)</text>',
        '  <rect x="720" y="118" width="210" height="258" rx="14" fill="#fff7df" stroke="#d6a11d"/>',
        '  <text x="740" y="154" class="label">Tekukan degenerat</text>',
        '  <text x="740" y="195" class="small">turunan kiri = 1</text>',
        '  <text x="740" y="227" class="small">turunan kanan = 0</text>',
        '  <text x="740" y="277" class="note">Harga bayangan</text>',
        '  <text x="740" y="305" class="note">tidak tunggal:</text>',
        '  <text x="740" y="337" class="small">0 ≤ y₃ ≤ 1</text>',
        '  <text x="92" y="648" class="note">Satu angka tidak dapat mewakili kedua arah perubahan pada b₃=2.</text>',
    ]
    return _frame(
        "10.11",
        "Latihan 10.11 — tekukan dan harga bayangan",
        "Nilai optimal sama dengan b3 hingga b3 sama dengan 2, lalu tetap 2. Tekukan di 2 memiliki turunan kiri 1 dan turunan kanan 0.",
        {
            "dual_shadow_price_set_at_kink": [0, 1],
            "left_derivative": 1,
            "right_derivative": 0,
            "value_formula": "min(b3,2)",
        },
        "\n".join(body),
    )


def _plot_1012() -> bytes:
    mapper = _mapper(15, 30)
    actual = mapper(14, 24)
    predicted = mapper(14, 28)
    body = [
        _axes(mapper, 15, 30, [0, 3, 6, 7, 9, 10, 12, 14, 15], [0, 5, 10, 15, 20, 25, 30], "b₁", "z*"),
        _line(mapper, [(0, 0), (7, 21)], "segment"),
        _line(mapper, [(7, 21), (10, 24)], "active"),
        _line(mapper, [(10, 24), (15, 24)], "segment"),
        _line(mapper, [(9, 23), (14, 28)], "prediction"),
        _circle(mapper, (9, 23), "point"),
        _circle(mapper, (14, 24), "actual"),
        _circle(mapper, (14, 28), "emphasis"),
        f'  <text class="small" x="{actual[0] - 72:.2f}" y="{actual[1] + 29:.2f}">aktual 24</text>',
        f'  <text class="small" x="{predicted[0] - 98:.2f}" y="{predicted[1] - 16:.2f}">prediksi 28</text>',
        '  <rect x="720" y="118" width="210" height="274" rx="14" fill="#fff0ed" stroke="#d47a6a"/>',
        '  <text x="740" y="154" class="label">Harga bayangan = 1</text>',
        '  <text x="740" y="195" class="small">berlaku: 7 ≤ b₁ ≤ 10</text>',
        '  <text x="740" y="237" class="small">b₁=9: z*=23</text>',
        '  <text x="740" y="269" class="small">b₁=10: z*=24</text>',
        '  <text x="740" y="301" class="small">b₁=14: z*=24</text>',
        '  <text x="740" y="349" class="note">Garis merah =</text>',
        '  <text x="740" y="377" class="note">ekstrapolasi keliru.</text>',
        '  <text x="92" y="648" class="note">Sesudah b₁=10, kendala jam tidak lagi mengikat dan kemiringannya menjadi nol.</text>',
    ]
    return _frame(
        "10.12",
        "Latihan 10.12 — harga bayangan di luar rentang",
        "Nilai optimal naik dari 23 pada b1 sama dengan 9 menjadi 24 pada b1 sama dengan 10, lalu mendatar. Ekstrapolasi harga bayangan ke b1 sama dengan 14 memprediksi 28, tetapi nilai aktual tetap 24.",
        {
            "actual": {"b1": 14, "objective": 24},
            "allowable_range": [7, 10],
            "prediction": {"b1": 14, "objective": 28},
            "shadow_price_at_b1_9": 1,
        },
        "\n".join(body),
    )


def generate_plot_payloads(
    _data: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    payloads = {
        "ex10-03.svg": _plot_103(),
        "ex10-11.svg": _plot_1011(),
        "ex10-12.svg": _plot_1012(),
    }
    generated = {
        "10.3": "ex10-03.svg",
        "10.11": "ex10-11.svg",
        "10.12": "ex10-12.svg",
    }
    records: dict[str, dict[str, Any]] = {}
    for exercise_id in [f"10.{index}" for index in range(1, 13)]:
        if exercise_id not in generated:
            records[exercise_id] = {
                "reason": (
                    "visual tidak menambah informasi material pada sertifikat "
                    "eksak atau laporan"
                ),
                "status": "not_generated",
            }
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
