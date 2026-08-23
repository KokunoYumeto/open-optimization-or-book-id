"""Renderer SVG deterministik dan aksesibel untuk LP dua variabel.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import html
import math
from typing import Any, Callable


WIDTH = 720
HEIGHT = 520
LEFT = 72
RIGHT = 28
TOP = 58
BOTTOM = 62
EPSILON = 1e-9


def _fmt(number: float) -> str:
    value = round(float(number), 6)
    if abs(value) <= 5e-7:
        value = 0.0
    rendered = f"{value:.6f}".rstrip("0").rstrip(".")
    return rendered or "0"


def _halfplanes(spec: dict[str, Any]) -> list[tuple[float, float, float]]:
    ids = tuple(variable["id"] for variable in spec["variables"])
    if len(ids) != 2:
        raise ValueError("plot hanya mendukung tepat dua variabel")
    first, second = ids
    halfplanes: list[tuple[float, float, float]] = []
    for constraint in spec["constraints"]:
        a_value = float(constraint["coefficients"].get(first, 0.0))
        b_value = float(constraint["coefficients"].get(second, 0.0))
        rhs = float(constraint["rhs"])
        if constraint["sense"] == "<=":
            halfplanes.append((a_value, b_value, rhs))
        elif constraint["sense"] == ">=":
            halfplanes.append((-a_value, -b_value, -rhs))
        elif constraint["sense"] == "=":
            halfplanes.extend(
                ((a_value, b_value, rhs), (-a_value, -b_value, -rhs))
            )
        else:
            raise ValueError(f"arah kendala tidak sah: {constraint['sense']}")
    for index, variable in enumerate(spec["variables"]):
        lower = variable.get("lower")
        upper = variable.get("upper")
        if index == 0:
            if lower is not None:
                halfplanes.append((-1.0, 0.0, -float(lower)))
            if upper is not None:
                halfplanes.append((1.0, 0.0, float(upper)))
        else:
            if lower is not None:
                halfplanes.append((0.0, -1.0, -float(lower)))
            if upper is not None:
                halfplanes.append((0.0, 1.0, float(upper)))
    return halfplanes


def _clip_polygon(
    polygon: list[tuple[float, float]],
    a_value: float,
    b_value: float,
    rhs: float,
) -> list[tuple[float, float]]:
    if not polygon:
        return []

    def residual(point: tuple[float, float]) -> float:
        return a_value * point[0] + b_value * point[1] - rhs

    clipped: list[tuple[float, float]] = []
    previous = polygon[-1]
    previous_residual = residual(previous)
    previous_inside = previous_residual <= EPSILON
    for current in polygon:
        current_residual = residual(current)
        current_inside = current_residual <= EPSILON
        if current_inside != previous_inside:
            denominator = previous_residual - current_residual
            if abs(denominator) > EPSILON:
                fraction = previous_residual / denominator
                clipped.append(
                    (
                        previous[0] + fraction * (current[0] - previous[0]),
                        previous[1] + fraction * (current[1] - previous[1]),
                    )
                )
        if current_inside:
            clipped.append(current)
        previous = current
        previous_residual = current_residual
        previous_inside = current_inside
    return clipped


def feasible_polygon(
    spec: dict[str, Any], window: list[float]
) -> list[tuple[float, float]]:
    xmin, xmax, ymin, ymax = map(float, window)
    polygon = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
    for a_value, b_value, rhs in _halfplanes(spec):
        polygon = _clip_polygon(polygon, a_value, b_value, rhs)
    return polygon


def _line_segment(
    a_value: float,
    b_value: float,
    rhs: float,
    window: list[float],
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    xmin, xmax, ymin, ymax = map(float, window)
    points: list[tuple[float, float]] = []
    if abs(b_value) > EPSILON:
        for x_value in (xmin, xmax):
            y_value = (rhs - a_value * x_value) / b_value
            if ymin - EPSILON <= y_value <= ymax + EPSILON:
                points.append((x_value, min(ymax, max(ymin, y_value))))
    if abs(a_value) > EPSILON:
        for y_value in (ymin, ymax):
            x_value = (rhs - b_value * y_value) / a_value
            if xmin - EPSILON <= x_value <= xmax + EPSILON:
                points.append((min(xmax, max(xmin, x_value)), y_value))
    unique: list[tuple[float, float]] = []
    for point in points:
        if not any(math.dist(point, existing) <= EPSILON for existing in unique):
            unique.append(point)
    if len(unique) < 2:
        return None
    first, second = max(
        (
            (first, second)
            for index, first in enumerate(unique)
            for second in unique[index + 1 :]
        ),
        key=lambda pair: math.dist(pair[0], pair[1]),
    )
    return first, second


def _coordinate_mapper(
    window: list[float],
) -> tuple[Callable[[float], float], Callable[[float], float]]:
    xmin, xmax, ymin, ymax = map(float, window)
    plot_width = WIDTH - LEFT - RIGHT
    plot_height = HEIGHT - TOP - BOTTOM

    def map_x(value: float) -> float:
        return LEFT + (float(value) - xmin) * plot_width / (xmax - xmin)

    def map_y(value: float) -> float:
        return TOP + (ymax - float(value)) * plot_height / (ymax - ymin)

    return map_x, map_y


def _svg_line(
    first: tuple[float, float],
    second: tuple[float, float],
    map_x: Callable[[float], float],
    map_y: Callable[[float], float],
    css_class: str,
    extra: str = "",
) -> str:
    return (
        f'<line class="{css_class}" x1="{_fmt(map_x(first[0]))}" '
        f'y1="{_fmt(map_y(first[1]))}" x2="{_fmt(map_x(second[0]))}" '
        f'y2="{_fmt(map_y(second[1]))}"{extra}/>'
    )


def _scenario_filename(exercise_id: str, scenario_id: str) -> str:
    number = exercise_id.partition(".")[2]
    safe_scenario = "".join(
        character if character.isalnum() or character == "_" else "-"
        for character in scenario_id
    )
    return f"ex05_{int(number):02d}_{safe_scenario}.svg"


def render_svg(
    exercise_id: str,
    spec: dict[str, Any],
    scenario_id: str,
) -> bytes:
    scenario = spec["scenarios"][scenario_id]
    expected = scenario["expected"]
    classification = expected["classification"]
    plot = spec["plot"]
    window = list(map(float, plot["window"]))
    xmin, xmax, ymin, ymax = window
    map_x, map_y = _coordinate_mapper(window)
    polygon = feasible_polygon(spec, window)
    title = f"Latihan {exercise_id}: {scenario['title_id']}"
    description = plot["description_id"]
    if classification in {"feasible_region_unbounded", "unbounded"} or spec.get(
        "recession_certificates"
    ):
        description += (
            f" Tampilan dipotong pada jendela x=[{_fmt(xmin)},{_fmt(xmax)}] "
            f"dan y=[{_fmt(ymin)},{_fmt(ymax)}]; tepi jendela bukan kendala model."
        )
    title_id = f"title-ex05-{exercise_id.partition('.')[2]}-{scenario_id}"
    desc_id = f"desc-ex05-{exercise_id.partition('.')[2]}-{scenario_id}"
    pieces = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
            f'aria-labelledby="{html.escape(title_id)} {html.escape(desc_id)}" '
            'xml:lang="id-ID" lang="id" focusable="false">'
        ),
        f"<title id=\"{html.escape(title_id)}\">{html.escape(title)}</title>",
        f"<desc id=\"{html.escape(desc_id)}\">{html.escape(description)}</desc>",
        "<metadata>Konten, model, dan data: CC BY-SA 4.0; kode renderer: MIT.</metadata>",
        "<defs>",
        '<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#b45309"/></marker>',
        "<style>",
        ".background{fill:#ffffff}.frame{fill:none;stroke:#334155;stroke-width:1.5}",
        ".grid{stroke:#e2e8f0;stroke-width:1}.axis{stroke:#475569;stroke-width:1.4}",
        ".constraint{stroke:#be123c;stroke-width:2;fill:none}",
        ".objective{stroke:#047857;stroke-width:2;stroke-dasharray:8 6;fill:none}",
        ".region{fill:#67e8f9;fill-opacity:.38;stroke:#0891b2;stroke-width:1.5}",
        ".optimum{stroke:#1d4ed8;stroke-width:5;fill:#1d4ed8}",
        ".ray{stroke:#b45309;stroke-width:3;stroke-dasharray:7 5;fill:none}",
        ".label{font:14px 'Segoe UI',Arial,sans-serif;fill:#0f172a}",
        ".small{font:12px 'Segoe UI',Arial,sans-serif;fill:#334155}",
        ".status{font:600 15px 'Segoe UI',Arial,sans-serif;fill:#0f172a}",
        "</style>",
        "</defs>",
        f'<rect class="background" width="{WIDTH}" height="{HEIGHT}"/>',
        f'<text class="status" x="{LEFT}" y="30">{html.escape(title)}</text>',
    ]

    for index in range(6):
        x_value = xmin + index * (xmax - xmin) / 5.0
        y_value = ymin + index * (ymax - ymin) / 5.0
        x_screen = map_x(x_value)
        y_screen = map_y(y_value)
        pieces.append(
            f'<line class="grid" x1="{_fmt(x_screen)}" y1="{TOP}" '
            f'x2="{_fmt(x_screen)}" y2="{HEIGHT - BOTTOM}"/>'
        )
        pieces.append(
            f'<line class="grid" x1="{LEFT}" y1="{_fmt(y_screen)}" '
            f'x2="{WIDTH - RIGHT}" y2="{_fmt(y_screen)}"/>'
        )
        pieces.append(
            f'<text class="small" text-anchor="middle" x="{_fmt(x_screen)}" '
            f'y="{HEIGHT - BOTTOM + 22}">{html.escape(_fmt(x_value))}</text>'
        )
        pieces.append(
            f'<text class="small" text-anchor="end" x="{LEFT - 9}" '
            f'y="{_fmt(y_screen + 4)}">{html.escape(_fmt(y_value))}</text>'
        )

    if polygon:
        points = " ".join(
            f"{_fmt(map_x(point[0]))},{_fmt(map_y(point[1]))}" for point in polygon
        )
        pieces.append(f'<polygon class="region" points="{points}"/>')

    ids = tuple(variable["id"] for variable in spec["variables"])
    for constraint in spec["constraints"]:
        segment = _line_segment(
            float(constraint["coefficients"].get(ids[0], 0.0)),
            float(constraint["coefficients"].get(ids[1], 0.0)),
            float(constraint["rhs"]),
            window,
        )
        if segment is not None:
            pieces.append(_svg_line(*segment, map_x, map_y, "constraint"))

    if 0.0 >= xmin and 0.0 <= xmax:
        pieces.append(
            _svg_line((0.0, ymin), (0.0, ymax), map_x, map_y, "axis")
        )
    if 0.0 >= ymin and 0.0 <= ymax:
        pieces.append(
            _svg_line((xmin, 0.0), (xmax, 0.0), map_x, map_y, "axis")
        )

    objective = scenario["objective"]
    objective_coefficients = objective["coefficients"]
    objective_rhs: float | None = None
    if "objective" in expected:
        objective_rhs = float(expected["objective"])
    elif classification == "unbounded" and spec.get("recession_certificates"):
        base = spec["recession_certificates"][0]["base"]
        objective_rhs = sum(
            float(objective_coefficients.get(variable_id, 0.0)) * float(base[index])
            for index, variable_id in enumerate(ids)
        )
    if objective_rhs is not None and any(
        abs(float(objective_coefficients.get(variable_id, 0.0))) > EPSILON
        for variable_id in ids
    ):
        segment = _line_segment(
            float(objective_coefficients.get(ids[0], 0.0)),
            float(objective_coefficients.get(ids[1], 0.0)),
            objective_rhs,
            window,
        )
        if segment is not None:
            pieces.append(_svg_line(*segment, map_x, map_y, "objective"))

    if "segment" in expected:
        first = tuple(map(float, expected["segment"][0]))
        second = tuple(map(float, expected["segment"][1]))
        pieces.append(_svg_line(first, second, map_x, map_y, "optimum"))
    if "point" in expected:
        point = tuple(map(float, expected["point"]))
        pieces.append(
            f'<circle class="optimum" cx="{_fmt(map_x(point[0]))}" '
            f'cy="{_fmt(map_y(point[1]))}" r="5"/>'
        )

    for ray in spec.get("recession_certificates", ()):
        base = tuple(map(float, ray["base"]))
        direction = tuple(map(float, ray["direction"]))
        positive_limits: list[float] = []
        if direction[0] > EPSILON:
            positive_limits.append((xmax - base[0]) / direction[0])
        elif direction[0] < -EPSILON:
            positive_limits.append((xmin - base[0]) / direction[0])
        if direction[1] > EPSILON:
            positive_limits.append((ymax - base[1]) / direction[1])
        elif direction[1] < -EPSILON:
            positive_limits.append((ymin - base[1]) / direction[1])
        positive_limits = [limit for limit in positive_limits if limit > 0]
        if positive_limits:
            scale = 0.82 * min(positive_limits)
            end = (
                base[0] + scale * direction[0],
                base[1] + scale * direction[1],
            )
            pieces.append(
                _svg_line(
                    base,
                    end,
                    map_x,
                    map_y,
                    "ray",
                    ' marker-end="url(#arrow)"',
                )
            )

    pieces.extend(
        [
            f'<rect class="frame" x="{LEFT}" y="{TOP}" width="{WIDTH - LEFT - RIGHT}" height="{HEIGHT - TOP - BOTTOM}"/>',
            f'<text class="label" text-anchor="end" x="{WIDTH - RIGHT}" y="{HEIGHT - 15}">{html.escape(plot["x_label"])}</text>',
            f'<text class="label" x="18" y="{TOP + 5}">{html.escape(plot["y_label"])}</text>',
            f'<text class="small" x="{LEFT}" y="{HEIGHT - 15}">Daerah sian = layak; merah = batas; hijau putus-putus = kurva aras; jingga = sinar; biru = optimum.</text>',
            "</svg>",
            "",
        ]
    )
    return "\n".join(pieces).encode("utf-8")


def generate_plot_payloads(
    data: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Menghasilkan byte SVG dan catatan terstruktur tanpa menyentuh disk."""
    payloads: dict[str, bytes] = {}
    records: dict[str, Any] = {}
    for exercise_id in data["exercise_order"]:
        spec = data["exercises"][exercise_id]
        plot = spec["plot"]
        if not plot["enabled"]:
            records[exercise_id] = {
                "description_id": plot["description_id"],
                "reason": plot["reason"],
                "status": "not_generated",
            }
            continue
        scenario_records: dict[str, Any] = {}
        for scenario_id, scenario in spec["scenarios"].items():
            filename = _scenario_filename(exercise_id, scenario_id)
            payload = render_svg(exercise_id, spec, scenario_id)
            payloads[filename] = payload
            scenario_records[scenario_id] = {
                "alt_text_id": plot["description_id"],
                "bytes": len(payload),
                "path": f"plots/{filename}",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "status": "generated",
                "title_id": f"Latihan {exercise_id}: {scenario['title_id']}",
                "viewport": plot["window"],
            }
        records[exercise_id] = {
            "scenarios": scenario_records,
            "status": "generated",
        }
    return payloads, records
