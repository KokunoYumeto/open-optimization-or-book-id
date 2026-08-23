"""Renderer SVG deterministik untuk geometri terpilih Bab 6.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import html
import math
from dataclasses import dataclass
from typing import Any, Callable


WIDTH = 720
HEIGHT = 520


def _fmt(number: float) -> str:
    text = f"{float(number):.6f}".rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


@dataclass(frozen=True)
class Canvas:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    left: float = 70.0
    right: float = 690.0
    top: float = 35.0
    bottom: float = 455.0

    @property
    def scale(self) -> float:
        return min(
            (self.right - self.left) / (self.xmax - self.xmin),
            (self.bottom - self.top) / (self.ymax - self.ymin),
        )

    @property
    def plot_left(self) -> float:
        used_width = (self.xmax - self.xmin) * self.scale
        return self.left + ((self.right - self.left) - used_width) / 2

    @property
    def plot_right(self) -> float:
        return self.plot_left + (self.xmax - self.xmin) * self.scale

    @property
    def plot_top(self) -> float:
        used_height = (self.ymax - self.ymin) * self.scale
        return self.top + ((self.bottom - self.top) - used_height) / 2

    @property
    def plot_bottom(self) -> float:
        return self.plot_top + (self.ymax - self.ymin) * self.scale

    def point(self, x_value: float, y_value: float) -> tuple[float, float]:
        x_pixel = self.plot_left + (x_value - self.xmin) * self.scale
        y_pixel = self.plot_bottom - (y_value - self.ymin) * self.scale
        return x_pixel, y_pixel

    def path_points(self, points: list[tuple[float, float]]) -> str:
        return " ".join(
            f"{_fmt(x_pixel)},{_fmt(y_pixel)}"
            for x_pixel, y_pixel in (self.point(x, y) for x, y in points)
        )


def _axes(canvas: Canvas) -> str:
    items: list[str] = []
    if canvas.ymin <= 0 <= canvas.ymax:
        x1, y = canvas.point(canvas.xmin, 0)
        x2, _ = canvas.point(canvas.xmax, 0)
        items.append(
            f'<line class="axis" x1="{_fmt(x1)}" y1="{_fmt(y)}" '
            f'x2="{_fmt(x2)}" y2="{_fmt(y)}" marker-end="url(#arrow)"/>'
        )
    if canvas.xmin <= 0 <= canvas.xmax:
        x, y1 = canvas.point(0, canvas.ymin)
        _, y2 = canvas.point(0, canvas.ymax)
        items.append(
            f'<line class="axis" x1="{_fmt(x)}" y1="{_fmt(y1)}" '
            f'x2="{_fmt(x)}" y2="{_fmt(y2)}" marker-end="url(#arrow)"/>'
        )
    for tick in range(math.ceil(canvas.xmin), math.floor(canvas.xmax) + 1):
        if tick == 0 or not (canvas.ymin <= 0 <= canvas.ymax):
            continue
        x, y = canvas.point(tick, 0)
        items.append(
            f'<line class="tick" x1="{_fmt(x)}" y1="{_fmt(y-4)}" '
            f'x2="{_fmt(x)}" y2="{_fmt(y+4)}"/>'
        )
        items.append(
            f'<text class="tick-label" x="{_fmt(x)}" y="{_fmt(y+20)}">{tick}</text>'
        )
    for tick in range(math.ceil(canvas.ymin), math.floor(canvas.ymax) + 1):
        if tick == 0 or not (canvas.xmin <= 0 <= canvas.xmax):
            continue
        x, y = canvas.point(0, tick)
        items.append(
            f'<line class="tick" x1="{_fmt(x-4)}" y1="{_fmt(y)}" '
            f'x2="{_fmt(x+4)}" y2="{_fmt(y)}"/>'
        )
        items.append(
            f'<text class="tick-label y" x="{_fmt(x-10)}" y="{_fmt(y+4)}">{tick}</text>'
        )
    items.append(
        f'<text class="axis-label" x="{_fmt(canvas.plot_right+4)}" '
        f'y="{_fmt(canvas.plot_bottom+19)}">x₁</text>'
    )
    items.append(
        f'<text class="axis-label" x="{_fmt(canvas.plot_left-20)}" '
        f'y="{_fmt(canvas.plot_top-5)}">x₂</text>'
    )
    return "\n".join(items)


def _frame(canvas: Canvas) -> str:
    return (
        f'<rect class="frame" x="{_fmt(canvas.plot_left)}" '
        f'y="{_fmt(canvas.plot_top)}" '
        f'width="{_fmt(canvas.plot_right-canvas.plot_left)}" '
        f'height="{_fmt(canvas.plot_bottom-canvas.plot_top)}"/>'
    )


def _circle(canvas: Canvas, point: tuple[float, float], css: str, label: str) -> str:
    x, y = canvas.point(*point)
    return (
        f'<circle class="{css}" cx="{_fmt(x)}" cy="{_fmt(y)}" r="6"/>'
        f'<text class="point-label" x="{_fmt(x+9)}" y="{_fmt(y-9)}">'
        f'{html.escape(label)}</text>'
    )


def _svg_document(slug: str, title: str, description: str, body: str) -> bytes:
    title_id = f"{slug}-title"
    desc_id = f"{slug}-desc"
    payload = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}"
  role="img" aria-labelledby="{title_id} {desc_id}" lang="id"
  xml:lang="id-ID" focusable="false">
  <title id="{title_id}">{html.escape(title)}</title>
  <desc id="{desc_id}">{html.escape(description)}</desc>
  <metadata>Adaptasi latihan O018 Bab 6; CC BY-SA 4.0.</metadata>
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4"
      orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L8,4 L0,8 z" fill="#1c2430"/>
    </marker>
    <style><![CDATA[
      .background {{ fill: #ffffff; }}
      .frame {{ fill: none; stroke: #697386; stroke-width: 1; }}
      .axis {{ stroke: #1c2430; stroke-width: 1.5; }}
      .tick {{ stroke: #1c2430; stroke-width: 1; }}
      .tick-label {{ fill: #1c2430; font: 13px sans-serif; text-anchor: middle; }}
      .tick-label.y {{ text-anchor: end; }}
      .axis-label {{ fill: #1c2430; font: 16px sans-serif; font-weight: 700; }}
      .region {{ fill: #dcecff; stroke: #174a7e; stroke-width: 2.5; }}
      .boundary {{ fill: none; stroke: #174a7e; stroke-width: 3; }}
      .secondary {{ fill: none; stroke: #8a3f00; stroke-width: 2.5; stroke-dasharray: 8 5; }}
      .point {{ fill: #ffffff; stroke: #111111; stroke-width: 2.5; }}
      .point-filled {{ fill: #111111; stroke: #ffffff; stroke-width: 1.5; }}
      .point-alert {{ fill: #ffffff; stroke: #a32020; stroke-width: 3; }}
      .point-label {{ fill: #111111; font: 14px sans-serif; font-weight: 600; }}
      .annotation {{ fill: #111111; font: 14px sans-serif; }}
      .annotation-strong {{ fill: #111111; font: 14px sans-serif; font-weight: 700; }}
      .optimal {{ stroke: #111111; stroke-width: 4; }}
      .guide {{ stroke: #697386; stroke-width: 1.5; stroke-dasharray: 4 4; }}
    ]]></style>
  </defs>
  <rect class="background" x="0" y="0" width="{WIDTH}" height="{HEIGHT}"/>
  {body}
</svg>
'''
    return payload.encode("utf-8")


def _render_66(_spec: dict[str, Any]) -> tuple[str, str, bytes]:
    slug = "ex06-06"
    title = "Latihan 6.6 — Selubung konveks sebuah segitiga"
    description = (
        "Segitiga tertutup bertitik sudut (0,0), (2,0), dan (0,2). "
        "Titik (1,1) berada pada hipotenusa, sedangkan (1,5;1,5) berada di luar."
    )
    canvas = Canvas(-0.4, 3.2, -0.4, 3.2)
    polygon = canvas.path_points([(0, 0), (2, 0), (0, 2)])
    body = [_frame(canvas), f'<polygon class="region" points="{polygon}"/>', _axes(canvas)]
    for point, label in (
        ((0, 0), "(0,0)"),
        ((2, 0), "(2,0)"),
        ((0, 2), "(0,2)"),
    ):
        body.append(_circle(canvas, point, "point-filled", label))
    body.append(_circle(canvas, (1, 1), "point", "(1,1), dalam"))
    body.append(_circle(canvas, (1.5, 1.5), "point-alert", "(1,5;1,5), luar"))
    label = canvas.point(2.15, 0.35)
    body.append(
        f'<text class="annotation-strong" x="{_fmt(label[0])}" '
        f'y="{_fmt(label[1])}">x₁ + x₂ ≤ 2</text>'
    )
    return slug, description, _svg_document(slug, title, description, "\n".join(body))


def _render_67(_spec: dict[str, Any]) -> tuple[str, str, bytes]:
    slug = "ex06-07"
    title = "Latihan 6.7 — Setengah ruang x₁ + 2x₂ ≤ 4"
    description = (
        "Garis batas melalui (4,0) dan (0,2). Daerah layak berada pada sisi "
        "yang memuat titik asal. (2,1) berada pada batas, (1,2) di luar, dan "
        "titik tengah (1,1/2) berada di dalam. Tepi jendela bukan kendala model."
    )
    canvas = Canvas(-1, 5, -1, 3)
    region = canvas.path_points([(-1, -1), (5, -1), (5, -0.5), (-1, 2.5)])
    start = canvas.point(-1, 2.5)
    end = canvas.point(5, -0.5)
    body = [
        _frame(canvas),
        f'<polygon class="region" points="{region}"/>',
        f'<line class="boundary" x1="{_fmt(start[0])}" y1="{_fmt(start[1])}" '
        f'x2="{_fmt(end[0])}" y2="{_fmt(end[1])}"/>',
        _axes(canvas),
        _circle(canvas, (2, 1), "point-filled", "(2,1), batas"),
        _circle(canvas, (1, 2), "point-alert", "(1,2), luar"),
        _circle(canvas, (1, 0.5), "point", "(1,1/2), titik tengah"),
    ]
    boundary_label = canvas.point(2.7, 1.45)
    body.append(
        f'<text class="annotation-strong" x="{_fmt(boundary_label[0])}" '
        f'y="{_fmt(boundary_label[1])}">x₁ + 2x₂ = 4</text>'
    )
    return slug, description, _svg_document(slug, title, description, "\n".join(body))


def _render_68(_spec: dict[str, Any]) -> tuple[str, str, bytes]:
    slug = "ex06-08"
    title = "Latihan 6.8 — Titik sudut dan titik non-ekstrem"
    description = (
        "Potongan polihedron tak berbatas memperlihatkan titik sudut (0,0), "
        "(0,1), dan (2,3). Titik (2,3) mempunyai dua kendala aktif bebas "
        "linier. Titik (1,2) adalah titik tengah (0,1) dan (2,3), sehingga "
        "bukan titik ekstrem. Daerah berlanjut ke kanan melewati jendela."
    )
    canvas = Canvas(-0.5, 6.5, -0.5, 5.5)
    polygon = canvas.path_points([(0, 0), (0, 1), (2, 3), (6.5, 5.25), (6.5, 1.625)])
    body = [_frame(canvas), f'<polygon class="region" points="{polygon}"/>', _axes(canvas)]
    for point, label in (
        ((0, 0), "(0,0)"),
        ((0, 1), "(0,1)"),
        ((2, 3), "(2,3), rank aktif 2"),
    ):
        body.append(_circle(canvas, point, "point-filled", label))
    first = canvas.point(0, 1)
    second = canvas.point(2, 3)
    body.append(
        f'<line class="secondary" x1="{_fmt(first[0])}" y1="{_fmt(first[1])}" '
        f'x2="{_fmt(second[0])}" y2="{_fmt(second[1])}"/>'
    )
    body.append(_circle(canvas, (1, 2), "point", "(1,2), titik tengah"))
    continuation = canvas.point(3.55, 0.55)
    body.append(
        f'<text class="annotation" x="{_fmt(continuation[0])}" '
        f'y="{_fmt(continuation[1])}">P berlanjut ke kanan →</text>'
    )
    return slug, description, _svg_document(slug, title, description, "\n".join(body))


def _render_610(_spec: dict[str, Any]) -> tuple[str, str, bytes]:
    slug = "ex06-10"
    title = "Latihan 6.10 — Gabungan dua cakram konveks"
    description = (
        "Dua cakram satuan berpusat di (-2,0) dan (2,0) terpisah. Kedua pusat "
        "berada dalam gabungan, tetapi titik tengahnya (0,0) berada di luar "
        "kedua cakram; gabungan karena itu tidak konveks."
    )
    canvas = Canvas(-3.6, 3.6, -1.8, 1.8)
    center1 = canvas.point(-2, 0)
    center2 = canvas.point(2, 0)
    radius = canvas.scale
    body = [
        _frame(canvas),
        f'<circle class="region" cx="{_fmt(center1[0])}" cy="{_fmt(center1[1])}" r="{_fmt(radius)}"/>',
        f'<circle class="region" cx="{_fmt(center2[0])}" cy="{_fmt(center2[1])}" r="{_fmt(radius)}"/>',
        _axes(canvas),
        _circle(canvas, (-2, 0), "point-filled", "pusat C₁"),
        _circle(canvas, (2, 0), "point-filled", "pusat C₂"),
        _circle(canvas, (0, 0), "point-alert", "titik tengah, luar"),
    ]
    c1_label = canvas.point(-2.8, 1.35)
    c2_label = canvas.point(2.0, 1.35)
    body.extend(
        [
            f'<text class="annotation-strong" x="{_fmt(c1_label[0])}" '
            f'y="{_fmt(c1_label[1])}">C₁</text>',
            f'<text class="annotation-strong" x="{_fmt(c2_label[0])}" '
            f'y="{_fmt(c2_label[1])}">C₂</text>',
        ]
    )
    return slug, description, _svg_document(slug, title, description, "\n".join(body))


def _render_611(_spec: dict[str, Any]) -> tuple[str, str, bytes]:
    slug = "ex06-11"
    title = "Latihan 6.11 — Lempeng tak berbatas tanpa titik sudut"
    description = (
        "Lempeng horizontal 0 ≤ x₂ ≤ 1 memanjang tanpa batas ke kiri dan kanan. "
        "Tidak ada titik sudut karena arah (1,0) adalah linealitas. Seluruh "
        "garis x₂=0 optimal untuk memaksimumkan -x₂. Tepi kiri dan kanan "
        "jendela bukan kendala model."
    )
    canvas = Canvas(-4, 4, -0.5, 1.5)
    upper_left = canvas.point(-4, 1)
    lower_right = canvas.point(4, 0)
    strip_x = upper_left[0]
    strip_y = upper_left[1]
    strip_width = lower_right[0] - upper_left[0]
    strip_height = lower_right[1] - upper_left[1]
    y0_left = canvas.point(-4, 0)
    y0_right = canvas.point(4, 0)
    y1_left = canvas.point(-4, 1)
    y1_right = canvas.point(4, 1)
    body = [
        _frame(canvas),
        f'<rect class="region" x="{_fmt(strip_x)}" y="{_fmt(strip_y)}" '
        f'width="{_fmt(strip_width)}" height="{_fmt(strip_height)}"/>',
        f'<line class="boundary" x1="{_fmt(y1_left[0])}" y1="{_fmt(y1_left[1])}" '
        f'x2="{_fmt(y1_right[0])}" y2="{_fmt(y1_right[1])}"/>',
        f'<line class="optimal" x1="{_fmt(y0_left[0])}" y1="{_fmt(y0_left[1])}" '
        f'x2="{_fmt(y0_right[0])}" y2="{_fmt(y0_right[1])}"/>',
        _axes(canvas),
    ]
    upper_label = canvas.point(1.2, 1.22)
    lower_label = canvas.point(0.7, 0.18)
    lineality_label = canvas.point(-1.5, 0.5)
    body.extend(
        [
            f'<text class="annotation-strong" x="{_fmt(upper_label[0])}" '
            f'y="{_fmt(upper_label[1])}">x₂ = 1</text>',
            f'<text class="annotation-strong" x="{_fmt(lower_label[0])}" '
            f'y="{_fmt(lower_label[1])}">x₂ = 0: seluruh garis optimal</text>',
            f'<text class="annotation" x="{_fmt(lineality_label[0])}" '
            f'y="{_fmt(lineality_label[1])}">← arah linealitas (1,0) →</text>',
        ]
    )
    return slug, description, _svg_document(slug, title, description, "\n".join(body))


RENDERERS: dict[str, Callable[[dict[str, Any]], tuple[str, str, bytes]]] = {
    "6.6": _render_66,
    "6.7": _render_67,
    "6.8": _render_68,
    "6.10": _render_610,
    "6.11": _render_611,
}


def generate_plot_payloads(
    data: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    payloads: dict[str, bytes] = {}
    records: dict[str, dict[str, Any]] = {}
    for exercise_id in data["exercise_order"]:
        renderer = RENDERERS.get(exercise_id)
        if renderer is None:
            records[exercise_id] = {
                "description_id": f"alt.ex{exercise_id.replace('.', '-')}.not-applicable",
                "reason": "not_pedagogically_useful_for_this_exercise",
                "status": "not_generated",
            }
            continue
        slug, description, payload = renderer(data["exercises"][exercise_id])
        filename = f"{slug}.svg"
        if filename in payloads:
            raise RuntimeError(f"nama SVG ganda: {filename}")
        payloads[filename] = payload
        records[exercise_id] = {
            "alt_text_id": f"alt.{slug}",
            "bytes": len(payload),
            "description": description,
            "path": f"plots/{filename}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "status": "generated",
        }
    return payloads, records
