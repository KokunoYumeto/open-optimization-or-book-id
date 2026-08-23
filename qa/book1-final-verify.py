#!/usr/bin/env python3
"""Deterministic structural QA for the complete Indonesian Book 1 PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "output" / "book1-pdf" / "book1-id.pdf"
REPLAY = ROOT / "qa" / "book1-final-replay-id4" / "book1-id.pdf"
LOG = ROOT / "output" / "book1-pdf" / "book1-id.log"
REPORT = ROOT / "qa" / "book1-final-qa-report.json"

EXPECTED_METADATA = {
    "/Author": "Robert Hildebrand",
    "/Title": (
        "Pemrograman Matematis dan Riset Operasi: Pemodelan, Algoritme, dan "
        "Kompleksitas; Contoh dalam Python dan Excel"
    ),
    "/Subject": "Edisi Bahasa Indonesia, Buku 1: Pemrograman Linear dan Bilangan Bulat",
    "/CreationDate": "D:20260821000000Z",
    "/ModDate": "D:20260821000000Z",
}

FATAL_LOG_PATTERNS = {
    "latex_error": r"LaTeX Error",
    "package_error": r"Package .* Error",
    "fatal_error": r"Fatal error",
    "emergency_stop": r"Emergency stop",
    "undefined_control": r"Undefined control sequence",
    "undefined_references": r"There were undefined references",
    "undefined_citation": r"Citation .* undefined",
    "multiply_defined": r"multiply defined",
    "duplicate_destination": r"destination with the same identifier",
    "missing_character": r"Missing character",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def flatten_outline(reader: PdfReader) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []

    def walk(items: list[object], depth: int = 0) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
                continue
            try:
                page = reader.get_destination_page_number(item) + 1
                error = None
            except Exception as exc:
                page = None
                error = str(exc)
            flattened.append(
                {"depth": depth, "title": str(item.title), "page": page, "error": error}
            )

    walk(reader.outline)
    return flattened


def destination_is_valid(reader: PdfReader, destination: object, page_ids: set[int]) -> bool:
    destination = destination.get_object() if hasattr(destination, "get_object") else destination
    if isinstance(destination, str):
        return destination in reader.named_destinations
    if isinstance(destination, (list, tuple)) and destination:
        first = destination[0]
        reference = getattr(first, "indirect_reference", None)
        if reference is None and hasattr(first, "idnum"):
            reference = first
        return bool(reference and reference.idnum in page_ids)
    return False


def inspect_links(reader: PdfReader) -> dict[str, object]:
    counts: Counter[str] = Counter()
    uri_schemes: Counter[str] = Counter()
    invalid: list[dict[str, object]] = []
    page_ids = {
        page.indirect_reference.idnum
        for page in reader.pages
        if page.indirect_reference is not None
    }
    for page_number, page in enumerate(reader.pages, 1):
        for annotation_ref in page.get("/Annots", []) or []:
            annotation = annotation_ref.get_object()
            if str(annotation.get("/Subtype")) != "/Link":
                continue
            counts["links"] += 1
            if "/Dest" in annotation:
                counts["internal"] += 1
                if not destination_is_valid(reader, annotation["/Dest"], page_ids):
                    invalid.append(
                        {"page": page_number, "kind": "Dest", "value": str(annotation["/Dest"])}
                    )
                continue
            action_ref = annotation.get("/A")
            if action_ref is None:
                invalid.append({"page": page_number, "kind": "missing-target"})
                continue
            action = action_ref.get_object()
            action_type = str(action.get("/S"))
            if action_type == "/GoTo":
                counts["internal"] += 1
                if not destination_is_valid(reader, action.get("/D"), page_ids):
                    invalid.append(
                        {"page": page_number, "kind": "GoTo", "value": str(action.get("/D"))}
                    )
            elif action_type == "/URI":
                counts["uri"] += 1
                uri = str(action.get("/URI", ""))
                scheme = urlparse(uri).scheme.lower()
                uri_schemes[scheme] += 1
                if scheme not in {"http", "https", "mailto"}:
                    invalid.append({"page": page_number, "kind": "URI", "value": uri})
            else:
                invalid.append({"page": page_number, "kind": "action", "value": action_type})
    return {
        "counts": dict(counts),
        "uri_schemes": dict(uri_schemes),
        "invalid": invalid,
    }


def inspect_fonts(pdf: Path) -> dict[str, object]:
    completed = subprocess.run(
        ["pdffonts", str(pdf)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    fonts: list[dict[str, str]] = []
    pattern = re.compile(
        r"^(?P<name>\S+)\s+(?P<type>(?:CID )?(?:Type \d|TrueType))\s+"
        r"(?P<encoding>\S+)\s+(?P<embedded>yes|no)\s+"
        r"(?P<subset>yes|no)\s+(?P<unicode>yes|no)\s+"
    )
    for line in completed.stdout.splitlines()[2:]:
        match = pattern.match(line)
        if match:
            fonts.append(match.groupdict())
    return {
        "count": len(fonts),
        "all_embedded": bool(fonts) and all(font["embedded"] == "yes" for font in fonts),
        "all_unicode": bool(fonts) and all(font["unicode"] == "yes" for font in fonts),
        "type3_count": sum(font["type"] == "Type 3" for font in fonts),
        "fonts": fonts,
    }


def inspect_log(path: Path) -> dict[str, object]:
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "fatal_counts": {
            name: len(re.findall(pattern, content, flags=re.IGNORECASE))
            for name, pattern in FATAL_LOG_PATTERNS.items()
        },
        "overfull_hbox_count": len(re.findall(r"Overfull \\hbox", content)),
        "overfull_vbox_count": len(re.findall(r"Overfull \\vbox", content)),
    }


def inspect_pdf(path: Path) -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    reader = PdfReader(path)
    metadata = {key: str(value) for key, value in (reader.metadata or {}).items()}
    catalog = reader.trailer["/Root"]
    outline = flatten_outline(reader)
    outline_pages = [entry["page"] for entry in outline if entry["page"] is not None]

    page_geometry_exceptions = []
    for page_number, page in enumerate(reader.pages, 1):
        media_box = [float(value) for value in page.mediabox]
        rotation = int(page.get("/Rotate", 0) or 0)
        if media_box != [0.0, 0.0, 612.0, 792.0] or rotation != 0:
            page_geometry_exceptions.append(
                {"page": page_number, "mediabox": media_box, "rotation": rotation}
            )

    named_destination_errors = []
    for name, destination in reader.named_destinations.items():
        try:
            reader.get_destination_page_number(destination)
        except Exception as exc:
            named_destination_errors.append({"name": name, "error": str(exc)})

    links = inspect_links(reader)
    fonts = inspect_fonts(path)
    names = catalog.get("/Names")
    names = names.get_object() if names is not None else {}
    javascript = bool(names and names.get("/JavaScript"))
    acroform = bool(catalog.get("/AcroForm"))

    if len(reader.pages) != 666:
        failures.append("pages:count")
    if page_geometry_exceptions:
        failures.append("pages:geometry")
    if str(catalog.get("/Lang")) != "id-ID":
        failures.append("catalog:lang")
    if reader.is_encrypted:
        failures.append("catalog:encrypted")
    if javascript:
        failures.append("catalog:javascript")
    if acroform:
        failures.append("catalog:acroform")
    for key, expected in EXPECTED_METADATA.items():
        if metadata.get(key) != expected:
            failures.append(f"metadata:{key}")
    if any(entry["error"] for entry in outline):
        failures.append("outline:invalid")
    if outline_pages != sorted(outline_pages):
        failures.append("outline:nonmonotonic")
    if named_destination_errors:
        failures.append("named-destinations:invalid")
    if links["invalid"]:
        failures.append("links:invalid")
    if not fonts["all_embedded"]:
        failures.append("fonts:not-embedded")
    if not fonts["all_unicode"]:
        failures.append("fonts:missing-unicode")
    if fonts["type3_count"]:
        failures.append("fonts:type3")

    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "pages": len(reader.pages),
        "page_geometry_exceptions": page_geometry_exceptions,
        "catalog": {
            "lang": str(catalog.get("/Lang")),
            "encrypted": reader.is_encrypted,
            "tagged": bool(catalog.get("/StructTreeRoot")),
            "acroform": acroform,
            "javascript": javascript,
        },
        "metadata": metadata,
        "outline_count": len(outline),
        "outline_destinations_all_valid": not any(entry["error"] for entry in outline),
        "outline_pages_monotonic": outline_pages == sorted(outline_pages),
        "named_destination_count": len(reader.named_destinations),
        "named_destination_errors": named_destination_errors,
        "links": links,
        "fonts": fonts,
    }, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-replay", action="store_true")
    args = parser.parse_args()

    missing = [str(path) for path in (CANONICAL, LOG) if not path.is_file()]
    if args.require_replay and not REPLAY.is_file():
        missing.append(str(REPLAY))
    if missing:
        print(json.dumps({"missing": missing}, indent=2))
        return 2

    canonical, failures = inspect_pdf(CANONICAL)
    tex_log = inspect_log(LOG)
    if any(tex_log["fatal_counts"].values()):
        failures.append("tex-log:fatal-pattern")
    if tex_log["overfull_hbox_count"] or tex_log["overfull_vbox_count"]:
        failures.append("tex-log:overfull-box")

    replay_result = None
    replay_byte_identical = None
    if REPLAY.is_file():
        replay_result, replay_failures = inspect_pdf(REPLAY)
        failures.extend(f"replay:{failure}" for failure in replay_failures)
        replay_byte_identical = CANONICAL.read_bytes() == REPLAY.read_bytes()
        if not replay_byte_identical:
            failures.append("replay:not-byte-identical")

    report = {
        "schema": "book1-final-qa-v1",
        "canonical": canonical,
        "replay": replay_result,
        "replay_byte_identical": replay_byte_identical,
        "tex_log": tex_log,
        "failures": failures,
        "passed": not failures,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": not failures,
                "failures": failures,
                "pages": canonical["pages"],
                "sha256": canonical["sha256"],
                "outlines": canonical["outline_count"],
                "named_destinations": canonical["named_destination_count"],
                "links": canonical["links"]["counts"],
                "type3_fonts": canonical["fonts"]["type3_count"],
                "report": str(REPORT),
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
