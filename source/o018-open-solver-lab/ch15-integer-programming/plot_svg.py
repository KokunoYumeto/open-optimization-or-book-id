"""Bangun SVG id-ID yang dapat diakses untuk Latihan 15.9 dan 15.16.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any


def _metadata(payload: dict[str, Any]) -> str:
    return html.escape(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def _svg_bytes(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def _graph_coloring_svg(data: dict[str, Any]) -> bytes:
    case = data["cases"]["graph_coloring"]
    positions = {
        "A": (360, 135),
        "B": (565, 260),
        "C": (490, 430),
        "D": (230, 430),
        "E": (155, 260),
    }
    coloring = {"A": 1, "B": 2, "C": 3, "D": 1, "E": 2}
    palette = {1: "#0072B2", 2: "#E69F00", 3: "#009E73"}
    meta = {
        "exercise_id": "15.9",
        "edges": case["edges"],
        "coloring": coloring,
        "chromatic_number": 3,
        "language": "id-ID",
    }
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="560" '
        'viewBox="0 0 720 560" role="img" xml:lang="id-ID" '
        'aria-labelledby="title desc">',
        "  <title id=\"title\">Pewarnaan optimal graf lima simpul pada Latihan 15.9</title>",
        "  <desc id=\"desc\">Graf siklus lima dengan tali busur A–C. "
        "Simpul A dan D berwarna biru, B dan E jingga, serta C hijau. "
        "Segitiga A–B–C membuktikan bahwa tiga warna diperlukan.</desc>",
        f"  <metadata>{_metadata(meta)}</metadata>",
        '  <rect width="720" height="560" fill="#ffffff"/>',
        '  <text x="360" y="34" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="22" font-weight="700" '
        'fill="#111827">Pewarnaan optimal: 3 warna</text>',
        '  <text x="360" y="58" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="14" fill="#374151">'
        'Segitiga A–B–C adalah sertifikat batas bawah.</text>',
        '  <g stroke="#263238" stroke-width="5" stroke-linecap="round">',
    ]
    for first, second in case["edges"]:
        x1, y1 = positions[first]
        x2, y2 = positions[second]
        lines.append(
            f'    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
        )
    lines.append("  </g>")
    lines.append('  <g font-family="Arial, sans-serif" font-weight="700">')
    for vertex in case["vertices"]:
        x, y = positions[vertex]
        color = palette[coloring[vertex]]
        lines.extend(
            [
                f'    <circle cx="{x}" cy="{y}" r="37" fill="{color}" '
                'stroke="#111827" stroke-width="3"/>',
                f'    <text x="{x}" y="{y + 8}" text-anchor="middle" '
                'font-size="25" fill="#ffffff">'
                f"{html.escape(vertex)}</text>",
            ]
        )
    lines.extend(
        [
            "  </g>",
            '  <g transform="translate(185 510)" font-family="Arial, sans-serif" '
            'font-size="14" fill="#111827">',
        ]
    )
    for index, label in enumerate(("Warna 1", "Warna 2", "Warna 3"), start=1):
        x = (index - 1) * 135
        lines.append(
            f'    <circle cx="{x}" cy="0" r="10" fill="{palette[index]}" '
            'stroke="#111827"/>'
        )
        lines.append(f'    <text x="{x + 17}" y="5">{label}</text>')
    lines.extend(["  </g>", "</svg>"])
    return _svg_bytes(lines)


def _flowshop_svg(data: dict[str, Any]) -> bytes:
    case = data["cases"]["flowshop"]
    schedule = {
        "Pekerjaan 1": [(0, 3), (3, 5), (5, 9)],
        "Pekerjaan 2": [(3, 5), (5, 9), (9, 12)],
    }
    palette = {"Pekerjaan 1": "#0072B2", "Pekerjaan 2": "#E69F00"}
    meta = {
        "exercise_id": "15.16",
        "language": "id-ID",
        "makespan": 12,
        "processing_times": case["processing_times"],
        "schedule": schedule,
    }
    width = 900
    height = 430
    plot_left = 115
    plot_top = 100
    plot_width = 720
    row_height = 82
    scale = plot_width / 12
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" xml:lang="id-ID" '
        'aria-labelledby="title desc">',
        "  <title id=\"title\">Jadwal optimal dua pekerjaan pada tiga mesin</title>",
        "  <desc id=\"desc\">Diagram Gantt. Pekerjaan 1 berjalan pada M1 dari "
        "0 sampai 3, M2 dari 3 sampai 5, dan M3 dari 5 sampai 9. Pekerjaan 2 "
        "berjalan pada M1 dari 3 sampai 5, M2 dari 5 sampai 9, dan M3 dari 9 "
        "sampai 12. Makespan optimal adalah 12.</desc>",
        f"  <metadata>{_metadata(meta)}</metadata>",
        '  <rect width="900" height="430" fill="#ffffff"/>',
        '  <text x="450" y="34" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="22" font-weight="700" '
        'fill="#111827">Jadwal flow-shop optimal</text>',
        '  <text x="450" y="59" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="15" fill="#374151">'
        'Makespan = 12</text>',
        '  <g stroke="#d1d5db" stroke-width="1">',
    ]
    for time in range(13):
        x = plot_left + time * scale
        lines.append(
            f'    <line x1="{x:g}" y1="{plot_top - 13}" '
            f'x2="{x:g}" y2="{plot_top + 3 * row_height}"/>'
        )
    lines.append("  </g>")
    lines.append(
        '  <g font-family="Arial, sans-serif" font-size="14" fill="#111827">'
    )
    for time in range(13):
        x = plot_left + time * scale
        lines.append(
            f'    <text x="{x:g}" y="{plot_top - 22}" '
            f'text-anchor="middle">{time}</text>'
        )
    for machine_index, machine in enumerate(case["machines"]):
        y = plot_top + machine_index * row_height
        lines.append(
            f'    <text x="{plot_left - 28}" y="{y + 34}" '
            f'text-anchor="end" font-weight="700">{machine}</text>'
        )
        lines.append(
            f'    <line x1="{plot_left}" y1="{y + 58}" '
            f'x2="{plot_left + plot_width}" y2="{y + 58}" '
            'stroke="#9ca3af"/>'
        )
        for job in case["jobs"]:
            begin, finish = schedule[job][machine_index]
            x = plot_left + begin * scale
            bar_width = (finish - begin) * scale
            lines.append(
                f'    <rect x="{x:g}" y="{y}" width="{bar_width:g}" '
                f'height="54" rx="6" fill="{palette[job]}" '
                'stroke="#111827" stroke-width="2"/>'
            )
            short = "P1" if job.endswith("1") else "P2"
            lines.append(
                f'    <text x="{x + bar_width / 2:g}" y="{y + 24}" '
                'text-anchor="middle" font-weight="700" fill="#ffffff">'
                f"{short}</text>"
            )
            lines.append(
                f'    <text x="{x + bar_width / 2:g}" y="{y + 43}" '
                'text-anchor="middle" font-size="12" fill="#ffffff">'
                f"{begin}–{finish}</text>"
            )
    lines.extend(
        [
            "  </g>",
            '  <g transform="translate(280 388)" font-family="Arial, sans-serif" '
            'font-size="14" fill="#111827">',
            '    <rect x="0" y="-13" width="22" height="18" rx="3" '
            'fill="#0072B2" stroke="#111827"/>',
            '    <text x="31" y="2">Pekerjaan 1</text>',
            '    <rect x="185" y="-13" width="22" height="18" rx="3" '
            'fill="#E69F00" stroke="#111827"/>',
            '    <text x="216" y="2">Pekerjaan 2</text>',
            "  </g>",
            "</svg>",
        ]
    )
    return _svg_bytes(lines)


def generate_plot_payloads(
    data: dict[str, Any]
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    payloads = {
        "ex15-09.svg": _graph_coloring_svg(data),
        "ex15-16.svg": _flowshop_svg(data),
    }
    records: dict[str, dict[str, Any]] = {}
    for exercise_id in data["exercise_order"]:
        filename = {
            "15.9": "ex15-09.svg",
            "15.16": "ex15-16.svg",
        }.get(exercise_id)
        if filename is None:
            records[exercise_id] = {"status": "not_required"}
        else:
            payload = payloads[filename]
            records[exercise_id] = {
                "bytes": len(payload),
                "language": "id-ID",
                "path": f"plots/{filename}",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "status": "generated",
                "structured_alternative": True,
            }
    return payloads, records
