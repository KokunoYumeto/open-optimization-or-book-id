#!/usr/bin/env python3
"""Apply or verify the universal program/original navigation contract.

The transform is byte-preserving outside two delimited additions: one stylesheet
reference in ``head`` and one accessible navigation landmark immediately inside
``body``.  Re-running ``--write`` is idempotent; ``--check`` performs no writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "federated_navigation.json"
STYLE_NAME = "federated-navigation.css"
RECEIPT_NAME = "FEDERATED_NAVIGATION_LOCAL_RECEIPT.json"
STYLE_MARKER = b"<!-- program-matematika-federated-nav-style-v1 -->"
NAV_BEGIN = b"<!-- program-matematika-federated-nav-v1:begin -->"
NAV_END = b"<!-- program-matematika-federated-nav-v1:end -->"

CSS = b""".program-matematika-federated-nav{position:relative;z-index:1000;box-sizing:border-box;width:100%;margin:0 0 1rem;padding:.72rem 1rem;background:#13213a;color:#fff;border-bottom:4px solid #f0b429;font:600 1rem/1.5 system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif;text-align:center}.program-matematika-federated-nav strong{display:inline-block;margin-right:.45rem}.program-matematika-federated-nav ul{display:inline-flex;flex-wrap:wrap;justify-content:center;gap:.35rem .8rem;margin:0;padding:0;list-style:none}.program-matematika-federated-nav li{margin:0;padding:0}.program-matematika-federated-nav a{color:#fff;text-decoration:underline;text-underline-offset:.18em}.program-matematika-federated-nav a:focus{outline:3px solid #fff;outline-offset:3px;border-radius:2px}@media print{.program-matematika-federated-nav{display:none}}\n"""


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    required = {
        "repository",
        "course_id",
        "content_language",
        "published_roots",
        "surface_url",
        "central_links",
        "authoritative_originals",
    }
    missing = sorted(required - set(config))
    if missing:
        raise RuntimeError(f"Configuration fields missing: {missing}")
    if len(config["central_links"]) != 2 or not config["authoritative_originals"]:
        raise RuntimeError("Exactly two central language links and at least one original are required")
    return config


def html_files(config: dict) -> list[tuple[Path, Path]]:
    selected: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for root_text in config["published_roots"]:
        root = (REPO_ROOT / root_text).resolve()
        if not root.is_dir() or root == REPO_ROOT.parent or REPO_ROOT not in (root, *root.parents):
            raise RuntimeError(f"Unsafe or missing published root: {root}")
        for candidate in sorted(root.rglob("*.html"), key=lambda path: path.as_posix()):
            if ".git" in candidate.parts or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            selected.append((root, candidate))
    if not selected:
        raise RuntimeError("No published HTML documents found")
    return selected


def render_style_link(relative_css: str) -> bytes:
    return (
        STYLE_MARKER
        + b"\n<link rel=\"stylesheet\" href=\""
        + relative_css.encode("utf-8")
        + b"\" data-program-matematika-nav=\"v1\">"
    )


def render_nav(config: dict) -> bytes:
    links = []
    for entry in config["central_links"]:
        links.append(
            f'<li><a href="{entry["url"]}" data-program-link="central-{entry["locale"]}">{entry["label"]}</a></li>'
        )
    for index, entry in enumerate(config["authoritative_originals"], start=1):
        links.append(
            f'<li><a href="{entry["url"]}" data-program-link="authoritative-original-{index}" rel="external">{entry["label"]}</a></li>'
        )
    html = (
        NAV_BEGIN.decode()
        + '\n<nav class="program-matematika-federated-nav" aria-label="Navigasi program matematika / Mathematics program navigation">'
        + '<strong>Program matematika / Mathematics program:</strong><ul>'
        + "".join(links)
        + "</ul></nav>\n"
        + NAV_END.decode()
    )
    return html.encode("utf-8")


def strip_insertions(payload: bytes) -> bytes:
    payload = re.sub(
        rb"<!-- program-matematika-federated-nav-style-v1 -->(?:\r?\n)?<link\b[^>]*data-program-matematika-nav=\"v1\"[^>]*>(?:\r?\n)",
        b"",
        payload,
        count=1,
        flags=re.IGNORECASE,
    )
    # Migrate the original v1 writer, which surrounded the delimited block
    # with two extra LF bytes, while preserving the document's own CRLF/LF.
    payload = re.sub(
        rb"\n<!-- program-matematika-federated-nav-v1:begin -->.*?<!-- program-matematika-federated-nav-v1:end -->\n",
        b"",
        payload,
        count=1,
        flags=re.DOTALL,
    )
    payload = re.sub(
        rb"<!-- program-matematika-federated-nav-v1:begin -->.*?<!-- program-matematika-federated-nav-v1:end -->",
        b"",
        payload,
        count=1,
        flags=re.DOTALL,
    )
    return payload


def inject(original: bytes, style_link: bytes, nav: bytes) -> bytes:
    clean = strip_insertions(original)
    eol = b"\r\n" if b"\r\n" in clean else b"\n"
    style_link = style_link.replace(b"\n", eol)
    nav = nav.replace(b"\n", eol)
    head_matches = list(re.finditer(rb"</head\s*>", clean, flags=re.IGNORECASE))
    body_match = re.search(rb"<body(?:\s[^>]*)?>", clean, flags=re.IGNORECASE)
    if len(head_matches) != 1 or body_match is None:
        raise RuntimeError("HTML must contain one closing head and an opening body")
    head_at = head_matches[0].start()
    transformed = clean[:head_at] + style_link + eol + clean[head_at:]
    body_match = re.search(rb"<body(?:\s[^>]*)?>", transformed, flags=re.IGNORECASE)
    assert body_match is not None
    body_at = body_match.end()
    transformed = transformed[:body_at] + nav + transformed[body_at:]
    if strip_insertions(transformed) != clean:
        raise RuntimeError("Round-trip content preservation check failed")
    return transformed


def manifest_digest(rows: list[dict]) -> str:
    payload = "".join(
        f'{row["path"]}\0{row["bytes"]}\0{row["sha256"]}\n' for row in rows
    ).encode("utf-8")
    return sha256(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    config = load_config()
    nav = render_nav(config)
    central_urls = [entry["url"].encode("utf-8") for entry in config["central_links"]]
    original_urls = [entry["url"].encode("utf-8") for entry in config["authoritative_originals"]]
    before_rows: list[dict] = []
    after_rows: list[dict] = []
    modified = 0
    roots_written: set[Path] = set()

    for root, candidate in html_files(config):
        roots_written.add(root)
        original = candidate.read_bytes()
        relative = candidate.relative_to(REPO_ROOT).as_posix()
        clean = strip_insertions(original)
        before_rows.append({"path": relative, "bytes": len(clean), "sha256": sha256(clean)})
        css_path = root / STYLE_NAME
        relative_css = os.path.relpath(css_path, candidate.parent).replace(os.sep, "/")
        expected = inject(original, render_style_link(relative_css), nav)
        if args.write and expected != original:
            candidate.write_bytes(expected)
            modified += 1
        actual = candidate.read_bytes()
        if actual != expected:
            raise RuntimeError(f"Navigation transform missing or non-canonical: {relative}")
        if actual.count(STYLE_MARKER) != 1 or actual.count(NAV_BEGIN) != 1 or actual.count(NAV_END) != 1:
            raise RuntimeError(f"Navigation markers are not unique: {relative}")
        nav_match = re.search(
            rb"<!-- program-matematika-federated-nav-v1:begin -->(.*?)<!-- program-matematika-federated-nav-v1:end -->",
            actual,
            flags=re.DOTALL,
        )
        if nav_match is None:
            raise RuntimeError(f"Navigation landmark cannot be isolated: {relative}")
        nav_actual = nav_match.group(1)
        for url in (*central_urls, *original_urls):
            if nav_actual.count(url) != 1:
                raise RuntimeError(f"Required navigation URL is absent or duplicated inside the landmark in {relative}: {url!r}")
        if strip_insertions(actual) != strip_insertions(original):
            raise RuntimeError(f"Content changed outside navigation markers: {relative}")
        after_rows.append({"path": relative, "bytes": len(actual), "sha256": sha256(actual)})

    for root in roots_written:
        css_path = root / STYLE_NAME
        if args.write and (not css_path.is_file() or css_path.read_bytes() != CSS):
            css_path.write_bytes(CSS)
        if not css_path.is_file() or css_path.read_bytes() != CSS:
            raise RuntimeError(f"Canonical navigation stylesheet differs: {css_path}")

    result = {
        "schema": "program-matematika.federated-navigation.local-receipt.v1",
        "status": "passed",
        "generated_by": "scripts/apply_federated_navigation.py",
        "repository": config["repository"],
        "course_id": config["course_id"],
        "content_language": config["content_language"],
        "surface_url": config["surface_url"],
        "published_roots": config["published_roots"],
        "html_documents": len(after_rows),
        "documents_with_navigation": len(after_rows),
        "before_manifest_sha256": manifest_digest(before_rows),
        "after_manifest_sha256": manifest_digest(after_rows),
        "html_bytes_after": sum(row["bytes"] for row in after_rows),
        "stylesheet_sha256": sha256(CSS),
        "central_links": config["central_links"],
        "authoritative_originals": config["authoritative_originals"],
        "checks": {
            "exactly_one_navigation_landmark_per_document": True,
            "exactly_one_stylesheet_reference_per_document": True,
            "all_central_and_original_links_present_once_per_document": True,
            "roundtrip_content_preservation": True,
            "idempotent_transform": True,
        },
    }
    receipt_path = SCRIPT_DIR / RECEIPT_NAME
    receipt = canonical_json(result)
    if args.write:
        if not receipt_path.is_file() or receipt_path.read_bytes() != receipt:
            receipt_path.write_bytes(receipt)
    elif not receipt_path.is_file() or receipt_path.read_bytes() != receipt:
        raise RuntimeError(f"Canonical local receipt is missing or stale: {receipt_path}")
    invocation = {
        "mode": "write" if args.write else "check",
        "documents_changed_this_run": modified,
        "receipt_sha256": sha256(receipt),
        **result,
    }
    print(canonical_json(invocation).decode("utf-8"), end="")


if __name__ == "__main__":
    main()
