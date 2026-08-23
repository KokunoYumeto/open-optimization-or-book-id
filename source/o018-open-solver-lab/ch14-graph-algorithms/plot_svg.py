"""Bangun SVG aksesibel untuk dua kasus algoritme graf Bab 14.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any


def _edge_key(u: str, v: str) -> tuple[str, str]:
    return tuple(sorted((u, v)))


def _svg(
    *,
    title: str,
    description: str,
    alternative_text: str,
    positions: dict[str, tuple[int, int]],
    edges: list[list[Any]],
    highlighted: set[tuple[str, str]],
    label_offsets: dict[tuple[str, str], tuple[int, int]] | None = None,
) -> bytes:
    metadata = json.dumps(
        {
            "alternative_text": alternative_text,
            "language": "id-ID",
            "license": "CC-BY-SA-4.0",
            "schema_version": "1.0.0",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="640" viewBox="0 0 960 640" role="img" xml:lang="id-ID" aria-labelledby="title desc">',
        f"  <title id=\"title\">{html.escape(title)}</title>",
        f"  <desc id=\"desc\">{html.escape(description)}</desc>",
        f"  <metadata>{html.escape(metadata)}</metadata>",
        '  <rect width="960" height="640" fill="#fffdf7"/>',
        f'  <text x="480" y="42" text-anchor="middle" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#172554">{html.escape(title)}</text>',
        '  <g stroke-linecap="round">',
    ]
    for u, v, weight in edges:
        x1, y1 = positions[u]
        x2, y2 = positions[v]
        selected = _edge_key(u, v) in highlighted
        color = "#c2410c" if selected else "#94a3b8"
        width = 7 if selected else 3
        lines.append(
            f'    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>'
        )
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        dx, dy = (label_offsets or {}).get(_edge_key(u, v), (0, 0))
        mx, my = mx + dx, my + dy
        lines.extend(
            [
                f'    <circle cx="{mx}" cy="{my}" r="16" fill="#fffdf7" stroke="none"/>',
                f'    <text x="{mx}" y="{my + 5}" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#111827">{weight}</text>',
            ]
        )
    lines.append("  </g>")
    lines.append('  <g font-family="Arial, sans-serif" font-size="20" font-weight="700" text-anchor="middle">')
    for node in sorted(positions):
        x, y = positions[node]
        lines.extend(
            [
                f'    <circle cx="{x}" cy="{y}" r="24" fill="#dbeafe" stroke="#1e3a8a" stroke-width="3"/>',
                f'    <text x="{x}" y="{y + 7}" fill="#172554">{html.escape(node)}</text>',
            ]
        )
    lines.extend(
        [
            "  </g>",
            '  <line x1="300" y1="604" x2="365" y2="604" stroke="#c2410c" stroke-width="7" stroke-linecap="round"/>',
            '  <text x="380" y="611" font-family="Arial, sans-serif" font-size="18" fill="#111827">sisi yang dipilih</text>',
            '  <line x1="535" y1="604" x2="600" y2="604" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>',
            '  <text x="615" y="611" font-family="Arial, sans-serif" font-size="18" fill="#111827">sisi lain</text>',
            "</svg>",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def generate_plot_payloads(data: dict[str, Any], results: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    mst_edges = data["cases"]["in_chapter_mst"]["edges"]
    mst_selected = {
        _edge_key(edge[0], edge[1])
        for edge in results["exercises"]["14.1"]["certificate"]["accepted_edges"]
    }
    shortest_edges = data["cases"]["in_chapter_shortest"]["edges"]
    shortest_path = results["exercises"]["14.4"]["certificate"]["path"]
    shortest_selected = {
        _edge_key(shortest_path[index], shortest_path[index + 1])
        for index in range(len(shortest_path) - 1)
    }
    payloads = {
        "ex14-01-mst.svg": _svg(
            title="Latihan 14.1 — Pohon merentang minimum",
            description="Graf berbobot enam simpul. Lima sisi pohon merentang minimum disorot jingga.",
            alternative_text="Sisi terpilih adalah A–B berbobot 11, B–G 13, A–E 14, E–F 16, dan C–E 17; total bobot 71.",
            positions={"A": (90, 320), "B": (280, 90), "C": (280, 550), "E": (620, 90), "F": (620, 550), "G": (870, 320)},
            edges=mst_edges,
            highlighted=mst_selected,
            label_offsets={
                _edge_key("A", "B"): (-20, -15),
                _edge_key("A", "E"): (-15, -20),
                _edge_key("A", "F"): (-15, 20),
                _edge_key("A", "G"): (0, 30),
                _edge_key("B", "C"): (25, 0),
                _edge_key("B", "E"): (0, -18),
                _edge_key("B", "F"): (-30, -25),
                _edge_key("B", "G"): (15, -15),
                _edge_key("C", "E"): (45, -30),
                _edge_key("C", "F"): (0, 18),
                _edge_key("C", "G"): (15, 15),
                _edge_key("E", "F"): (25, 0),
                _edge_key("E", "G"): (15, -15),
                _edge_key("F", "G"): (15, 15),
            },
        ),
        "ex14-04-shortest.svg": _svg(
            title="Latihan 14.4 — Lintasan terpendek A ke G",
            description="Graf berbobot tujuh simpul. Lintasan terpendek dari A ke G disorot jingga.",
            alternative_text="Lintasan terpendek adalah A–B–D–E–G dengan bobot 1+3+2+7=13.",
            positions={"A": (80, 320), "B": (250, 135), "C": (250, 505), "D": (440, 320), "E": (640, 135), "F": (640, 505), "G": (875, 320)},
            edges=shortest_edges,
            highlighted=shortest_selected,
        ),
    }
    records: dict[str, dict[str, Any]] = {}
    mapping = {"14.1": "ex14-01-mst.svg", "14.4": "ex14-04-shortest.svg"}
    for exercise_id in data["exercise_order"]:
        if exercise_id not in mapping:
            records[exercise_id] = {"status": "not_required"}
            continue
        filename = mapping[exercise_id]
        payload = payloads[filename]
        records[exercise_id] = {
            "bytes": len(payload),
            "language": "id-ID",
            "path": f"plots/{filename}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "status": "generated",
        }
    return payloads, records
