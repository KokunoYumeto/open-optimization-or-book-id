#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble the bounded, deterministic R017/O018 public release package.

The script deliberately knows every admitted root. It never scans above this
edition lane, never invokes Git, never reads credentials, and refuses source
symlinks, path traversal, cache files, or a PDF identity different from the
explicit final identity supplied by the release operator.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


LANE = Path(__file__).resolve().parents[1]
RELEASE_DIR = LANE / "release"
OUT_DIR = RELEASE_DIR / "out"
STAGE_DIR = RELEASE_DIR / ".release-package-stage"
REPLAY_DIR = RELEASE_DIR / ".release-package-replay"
DOCS_DIR = LANE / "docs"
DOCS_DOWNLOADS = DOCS_DIR / "downloads"
QA_REPORT = LANE / "qa" / "release-package-report.json"
READER_IDENTITY = RELEASE_DIR / "reader-identity.json"

UPSTREAM_COMMIT = "1745df89b608899f66983834fa4ec8c8910d18ff"
UPSTREAM_TREE = "209d5de696ebac4e5921b73d6b6b2f539fc23d1c"
UPSTREAM_ARCHIVE_SHA256 = (
    "4bee88ed3af700b16d5643a3c18b9846244d3467eec7f4fb1f009a782b9143fc"
)
UPSTREAM_DIR = (
    LANE
    / "authority"
    / "upstream"
    / f"open-optimization-or-book-{UPSTREAM_COMMIT}"
)

SOURCE_DATE_EPOCH = 1_787_443_200  # 2026-08-23T00:00:00Z
ZIP_DATE_TIME = (2026, 8, 23, 0, 0, 0)
FIXED_ISO_TIMESTAMP = "2026-08-23T00:00:00Z"
EDITION_VERSION = "2026.08.23-id.5"
EDITION_ID = "r017-o018.book1.id-ID.2026.08.23-id.5"
RELEASE_TITLE = "Pemrograman Matematis dan Riset Operasi — Buku 1, Edisi Bahasa Indonesia"

PDF_SOURCE = LANE / "output" / "book1-pdf" / "book1-id.pdf"
PDF_NAME = "pemrograman-matematis-dan-riset-operasi-buku-1-id-ID.pdf"
SOURCE_ZIP_NAME = "pemrograman-matematis-dan-riset-operasi-buku-1-source-id-ID.zip"
LAB_ZIP_NAME = (
    "pemrograman-matematis-dan-riset-operasi-buku-1-"
    "o018-open-solver-labs-id-ID.zip"
)
BACKEND_ZIP_NAME = (
    "pemrograman-matematis-dan-riset-operasi-buku-1-modular-backend-v0.zip"
)
MANIFEST_NAME = "RELEASE-MANIFEST.json"
CHECKSUM_NAME = "SHA256SUMS.txt"

PRIMARY_OUTPUT_NAMES = (
    PDF_NAME,
    SOURCE_ZIP_NAME,
    LAB_ZIP_NAME,
    BACKEND_ZIP_NAME,
)
SUPPORT_OUTPUTS = {
    "README.md": RELEASE_DIR / "PUBLIC-README.md",
    "CITATION.cff": LANE / "CITATION.cff",
    "LICENSES-README.md": LANE / "LICENSES" / "README.md",
    "NOTICE-EDITION.md": LANE / "NOTICE" / "EDITION.md",
    "RELEASE-NOTES.md": RELEASE_DIR / "RELEASE-NOTES.md",
    "MIT-NEW-CODE.txt": LANE / "LICENSES" / "MIT-NEW-CODE.txt",
    "MIT-UPSTREAM-CODE.txt": LANE / "LICENSES" / "MIT-UPSTREAM-CODE.txt",
}
ALL_OUTPUT_NAMES = (
    *PRIMARY_OUTPUT_NAMES,
    *tuple(SUPPORT_OUTPUTS),
    MANIFEST_NAME,
    CHECKSUM_NAME,
)

FORBIDDEN_DIRECTORY_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "tmp",
}
FORBIDDEN_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".bak",
    ".swp",
    ".swo",
    ".fdb_latexmk",
    ".fls",
    ".synctex.gz",
    ".aux",
    ".bcf",
    ".blg",
    ".ilg",
    ".ind",
    ".run.xml",
    ".toc",
}
SENSITIVE_FILE_NAMES = {
    ".env",
    ".npmrc",
    "credentials.json",
    "github tokens.md",
    "zenodo token.md",
    "id_rsa",
    "id_ed25519",
}


@dataclass(frozen=True)
class ArchiveEntry:
    source: Path
    archive_path: str


@dataclass(frozen=True)
class PackageSpec:
    output_name: str
    role: str
    media_type: str
    roots: tuple[tuple[Path, str], ...]
    files: tuple[tuple[Path, str], ...] = ()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def assert_lane_path(path: Path, *, must_exist: bool = True) -> Path:
    resolved_lane = LANE.resolve(strict=True)
    resolved = path.resolve(strict=must_exist)
    if resolved != resolved_lane and not resolved.is_relative_to(resolved_lane):
        raise ValueError(f"path escapes edition lane: {path}")
    return resolved


def is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def forbidden_suffix(name: str) -> bool:
    lowered = name.casefold()
    return any(lowered.endswith(suffix) for suffix in FORBIDDEN_FILE_SUFFIXES)


def validate_archive_name(value: str) -> str:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"unsafe archive path: {value}")
    normalized = pure.as_posix()
    if normalized.startswith("/") or "\\" in normalized:
        raise ValueError(f"unsafe archive path: {value}")
    return normalized


def collect_tree(root: Path, prefix: str) -> tuple[list[ArchiveEntry], list[str]]:
    root = assert_lane_path(root)
    if not root.is_dir() or is_link_or_junction(root):
        raise ValueError(f"archive root is not a regular directory: {root}")
    prefix = validate_archive_name(prefix)
    entries: list[ArchiveEntry] = []
    skipped: list[str] = []
    for candidate in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = candidate.relative_to(root)
        if any(part.casefold() in FORBIDDEN_DIRECTORY_NAMES for part in relative.parts):
            if candidate.is_file():
                skipped.append(candidate.relative_to(LANE).as_posix())
            continue
        if is_link_or_junction(candidate):
            raise ValueError(f"links and junctions are not admitted: {candidate}")
        if candidate.is_dir():
            continue
        if not candidate.is_file():
            raise ValueError(f"non-regular archive input: {candidate}")
        if candidate.name.casefold() in SENSITIVE_FILE_NAMES:
            raise ValueError(f"sensitive filename in admitted root: {candidate}")
        if forbidden_suffix(candidate.name):
            skipped.append(candidate.relative_to(LANE).as_posix())
            continue
        assert_lane_path(candidate)
        archive_path = validate_archive_name(
            f"{prefix}/{relative.as_posix()}"
        )
        entries.append(ArchiveEntry(candidate, archive_path))
    if not entries:
        raise ValueError(f"archive root has no admitted files: {root}")
    return entries, skipped


def collect_package(spec: PackageSpec) -> tuple[list[ArchiveEntry], list[str]]:
    entries: list[ArchiveEntry] = []
    skipped: list[str] = []
    for root, prefix in spec.roots:
        root_entries, root_skipped = collect_tree(root, prefix)
        entries.extend(root_entries)
        skipped.extend(root_skipped)
    for source, archive_path in spec.files:
        source = assert_lane_path(source)
        if not source.is_file() or is_link_or_junction(source):
            raise ValueError(f"archive input is not a regular file: {source}")
        if source.name.casefold() in SENSITIVE_FILE_NAMES:
            raise ValueError(f"sensitive filename is not admitted: {source}")
        entries.append(ArchiveEntry(source, validate_archive_name(archive_path)))
    entries.sort(key=lambda item: item.archive_path)
    names = [entry.archive_path for entry in entries]
    if len(names) != len(set(names)):
        duplicates = sorted(name for name in set(names) if names.count(name) > 1)
        raise ValueError(f"duplicate archive paths: {duplicates}")
    return entries, sorted(set(skipped))


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=ZIP_DATE_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (0o100644 & 0xFFFF) << 16
    info.flag_bits |= 0x800
    info.extra = b""
    info.comment = b""
    return info


def build_zip(path: Path, entries: Iterable[ArchiveEntry]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    expected: dict[str, tuple[int, str]] = {}
    raw_bytes = 0
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        allowZip64=True,
        strict_timestamps=True,
    ) as archive:
        archive.comment = b""
        for entry in entries:
            data = entry.source.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            expected[entry.archive_path] = (len(data), digest)
            raw_bytes += len(data)
            archive.writestr(
                zip_info(entry.archive_path),
                data,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    os.utime(path, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))

    with zipfile.ZipFile(path, "r") as archive:
        if archive.testzip() is not None:
            raise ValueError(f"ZIP CRC verification failed: {path}")
        if archive.namelist() != sorted(expected):
            raise ValueError(f"ZIP entry order/inventory mismatch: {path}")
        for info in archive.infolist():
            if info.date_time != ZIP_DATE_TIME:
                raise ValueError(f"non-fixed ZIP timestamp: {path}:{info.filename}")
            data = archive.read(info.filename)
            expected_size, expected_hash = expected[info.filename]
            if len(data) != expected_size:
                raise ValueError(f"ZIP entry size mismatch: {path}:{info.filename}")
            if hashlib.sha256(data).hexdigest() != expected_hash:
                raise ValueError(f"ZIP entry hash mismatch: {path}:{info.filename}")

    return {
        "file_name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "entry_count": len(expected),
        "uncompressed_bytes": raw_bytes,
    }


def copy_fixed(source: Path, target: Path) -> None:
    source = assert_lane_path(source)
    if not source.is_file() or is_link_or_junction(source):
        raise ValueError(f"copy source is not a regular file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    os.utime(target, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))


def safe_remove_scratch(path: Path) -> None:
    resolved_parent = path.parent.resolve(strict=True)
    if resolved_parent != RELEASE_DIR.resolve(strict=True):
        raise ValueError(f"refusing to remove non-release scratch path: {path}")
    if path.exists():
        if is_link_or_junction(path) or not path.is_dir():
            raise ValueError(f"release scratch path is not a regular directory: {path}")
        shutil.rmtree(path)


def verify_pdf(expected_bytes: int, expected_sha256: str) -> dict[str, object]:
    pdf = assert_lane_path(PDF_SOURCE)
    actual_bytes = pdf.stat().st_size
    actual_sha256 = sha256_file(pdf)
    if actual_bytes != expected_bytes or actual_sha256 != expected_sha256:
        raise ValueError(
            "canonical PDF identity mismatch: "
            f"expected {expected_bytes}/{expected_sha256}, "
            f"observed {actual_bytes}/{actual_sha256}"
        )

    qa_path = assert_lane_path(LANE / "qa" / "book1-final-qa-report.json")
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if qa.get("passed") is not True or qa.get("failures") != []:
        raise ValueError("book1-final QA report does not record an unqualified pass")
    if qa.get("replay_byte_identical") is not True:
        raise ValueError("book1-final QA report does not prove a byte-identical replay")
    canonical = qa.get("canonical", {})
    if canonical.get("bytes") != expected_bytes or canonical.get("sha256") != expected_sha256:
        raise ValueError("book1-final QA report is not bound to the final PDF")
    if canonical.get("catalog", {}).get("lang") != "id-ID":
        raise ValueError("book1-final QA report does not prove /Lang id-ID")
    if canonical.get("catalog", {}).get("tagged") is not False:
        raise ValueError("accessibility disclosure must be reviewed: Tagged state changed")
    fonts = canonical.get("fonts", {})
    if not fonts.get("all_embedded") or not fonts.get("all_unicode"):
        raise ValueError("book1-final QA report does not prove embedded Unicode fonts")
    if fonts.get("type3_count") != 0:
        raise ValueError("book1-final QA report records Type 3 fonts")
    if canonical.get("links", {}).get("invalid"):
        raise ValueError("book1-final QA report records invalid links")
    replay = qa.get("replay", {})
    if replay.get("bytes") != expected_bytes or replay.get("sha256") != expected_sha256:
        raise ValueError("book1-final replay identity does not match the final PDF")
    if replay.get("pages") != canonical.get("pages"):
        raise ValueError("book1-final replay page count differs from the canonical PDF")
    return {
        "path": PDF_SOURCE.relative_to(LANE).as_posix(),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
        "pages": canonical.get("pages"),
        "qa_report": qa_path.relative_to(LANE).as_posix(),
        "qa_report_sha256": sha256_file(qa_path),
    }


def verify_backend() -> dict[str, object]:
    exporter = assert_lane_path(LANE / "scripts" / "export_backend.py")
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [
            sys.executable,
            str(exporter),
            "--require-bound-targets",
            "--check",
        ],
        cwd=LANE,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            "backend deterministic check failed\n"
            + process.stdout[-4000:]
            + process.stderr[-4000:]
        )
    manifest_path = assert_lane_path(LANE / "backend" / "dist" / "manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("backend manifest has no artifacts")
    dist = manifest_path.parent
    for record in artifacts:
        relative = PurePosixPath(str(record.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe backend manifest path: {relative}")
        artifact = dist.joinpath(*relative.parts)
        if not artifact.is_file():
            raise ValueError(f"backend manifest artifact missing: {artifact}")
        if artifact.stat().st_size != record.get("bytes"):
            raise ValueError(f"backend artifact size mismatch: {artifact}")
        if sha256_file(artifact) != record.get("sha256"):
            raise ValueError(f"backend artifact hash mismatch: {artifact}")
    output = (process.stdout + process.stderr).encode("utf-8")
    return {
        "command": "python scripts/export_backend.py --require-bound-targets --check",
        "exit_code": process.returncode,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "manifest": manifest_path.relative_to(LANE).as_posix(),
        "manifest_bytes": manifest_path.stat().st_size,
        "manifest_sha256": sha256_file(manifest_path),
        "artifact_count": len(artifacts),
    }


class LinkCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.html_lang: str | None = None
        self.iframe_titles: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang")
        for attribute in ("href", "src"):
            value = values.get(attribute)
            if value:
                self.links.append(value)
        if tag == "iframe":
            self.iframe_titles.append(values.get("title") or "")


def validate_docs_links(*, allow_missing_generated: bool) -> dict[str, object]:
    index = assert_lane_path(DOCS_DIR / "index.html")
    parser = LinkCollector()
    parser.feed(index.read_text(encoding="utf-8"))
    if parser.html_lang != "id-ID":
        raise ValueError("docs/index.html must declare lang=id-ID")
    if not parser.iframe_titles or any(not title.strip() for title in parser.iframe_titles):
        raise ValueError("every PDF iframe must have a nonempty title")

    internal: list[str] = []
    external: list[str] = []
    missing: list[str] = []
    for value in parser.links:
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme or parsed.netloc:
            external.append(value)
            continue
        if not parsed.path:
            continue
        relative = urllib.parse.unquote(parsed.path)
        target = (index.parent / relative).resolve(strict=False)
        if target != DOCS_DIR.resolve() and not target.is_relative_to(DOCS_DIR.resolve()):
            raise ValueError(f"docs link escapes docs root: {value}")
        internal.append(value)
        if not target.exists():
            generated = (
                target.parent == DOCS_DOWNLOADS.resolve(strict=False)
                and target.name in ALL_OUTPUT_NAMES
            )
            if not (allow_missing_generated and generated):
                missing.append(value)
    if missing:
        raise ValueError(f"missing local docs targets: {sorted(set(missing))}")
    return {
        "html_lang": parser.html_lang,
        "internal_link_count": len(internal),
        "external_link_count": len(external),
        "iframe_count": len(parser.iframe_titles),
        "missing_local_links": [],
    }


def validate_static_files() -> dict[str, object]:
    required = (
        LANE / "README.md",
        LANE / "CITATION.cff",
        LANE / "LICENSES" / "README.md",
        LANE / "LICENSES" / "MIT-NEW-CODE.txt",
        LANE / "LICENSES" / "MIT-UPSTREAM-CODE.txt",
        LANE / "NOTICE" / "EDITION.md",
        DOCS_DIR / "index.html",
        DOCS_DIR / "assets" / "site.css",
        DOCS_DIR / ".nojekyll",
        RELEASE_DIR / "README.md",
        RELEASE_DIR / "PUBLIC-README.md",
        RELEASE_DIR / "RELEASE-NOTES.md",
        READER_IDENTITY,
        RELEASE_DIR / "zenodo-metadata.json",
        RELEASE_DIR / "github-repository-metadata.json",
        LANE / "qa" / "release-package-browser-qa.json",
    )
    for path in required:
        assert_lane_path(path)
        if not path.is_file():
            raise ValueError(f"required release-facing file missing: {path}")
    citation = (LANE / "CITATION.cff").read_text(encoding="utf-8")
    for marker in (
        "cff-version: 1.2.0",
        "type: book",
        "family-names: Hildebrand",
        f'version: "{EDITION_VERSION}"',
        "  - CC-BY-SA-4.0",
        "  - MIT",
        UPSTREAM_COMMIT,
    ):
        if marker not in citation:
            raise ValueError(f"CITATION.cff missing required marker: {marker}")
    if "\t" in citation:
        raise ValueError("CITATION.cff contains tabs")
    zenodo = json.loads(
        (RELEASE_DIR / "zenodo-metadata.json").read_text(encoding="utf-8")
    )
    zenodo_metadata = zenodo.get("metadata", {})
    if zenodo_metadata.get("title") != RELEASE_TITLE:
        raise ValueError("Zenodo metadata title does not match the release title")
    if zenodo_metadata.get("language") != "ind":
        raise ValueError("Zenodo metadata must declare ISO 639-3 language ind")
    if zenodo_metadata.get("version") != EDITION_VERSION:
        raise ValueError("Zenodo metadata version does not match edition version")
    if zenodo_metadata.get("license") != "other-open":
        raise ValueError("Zenodo metadata must preserve the mixed-license release")
    if zenodo_metadata.get("access_right") != "open":
        raise ValueError("Zenodo metadata must declare open access")
    if zenodo_metadata.get("upload_type") != "publication":
        raise ValueError("Zenodo metadata must describe a publication upload")
    if zenodo_metadata.get("publication_type") != "book":
        raise ValueError("Zenodo metadata must describe a book publication")
    repository = json.loads(
        (RELEASE_DIR / "github-repository-metadata.json").read_text(
            encoding="utf-8"
        )
    )
    if repository.get("repository_name") != "open-optimization-or-book-id":
        raise ValueError("GitHub repository metadata has an unexpected name")
    if repository.get("pages", {}).get("source", {}).get("path") != "/docs":
        raise ValueError("GitHub Pages metadata must publish /docs")
    reader_identity = json.loads(READER_IDENTITY.read_text(encoding="utf-8"))
    if reader_identity.get("edition_id") != EDITION_ID:
        raise ValueError("reader identity edition ID does not match this release")
    reader = reader_identity.get("reader", {})
    reader_qa = reader_identity.get("qa", {})
    if reader.get("path") != PDF_SOURCE.relative_to(LANE).as_posix():
        raise ValueError("reader identity canonical path drift")
    if reader.get("release_file_name") != PDF_NAME:
        raise ValueError("reader identity release filename drift")
    if reader.get("media_type") != "application/pdf":
        raise ValueError("reader identity media type drift")
    if reader.get("language") != "id-ID":
        raise ValueError("reader identity language drift")
    if reader.get("bytes") != PDF_SOURCE.stat().st_size:
        raise ValueError("reader identity byte-count drift")
    if reader.get("sha256") != sha256_file(PDF_SOURCE):
        raise ValueError("reader identity PDF hash drift")
    final_qa = LANE / "qa" / "book1-final-qa-report.json"
    if reader_qa.get("bytes") != final_qa.stat().st_size:
        raise ValueError("reader identity QA byte-count drift")
    if reader_qa.get("sha256") != sha256_file(final_qa):
        raise ValueError("reader identity QA hash drift")
    if reader_qa.get("status") != "passed":
        raise ValueError("reader identity does not record passed QA")
    parsed_final_qa = json.loads(final_qa.read_text(encoding="utf-8"))
    if parsed_final_qa.get("canonical", {}).get("pages") != reader.get("pages"):
        raise ValueError("reader identity page-count drift")
    browser_qa = json.loads(
        (LANE / "qa" / "release-package-browser-qa.json").read_text(
            encoding="utf-8"
        )
    )
    browser_status = browser_qa.get("status")
    if browser_status not in {"passed", "passed_with_generated_downloads_pending"}:
        raise ValueError("browser QA does not record a recognized passing state")
    browser_inputs = browser_qa.get("inputs")
    if not isinstance(browser_inputs, list) or not browser_inputs:
        raise ValueError("browser QA must bind at least one authored input")
    for record in browser_inputs:
        if not isinstance(record, dict):
            raise ValueError("browser QA input record is not an object")
        raw_path = str(record.get("path", ""))
        relative = PurePosixPath(raw_path)
        if (
            not raw_path
            or relative.is_absolute()
            or ".." in relative.parts
            or "\\" in raw_path
        ):
            raise ValueError(f"unsafe browser QA input path: {raw_path!r}")
        path = assert_lane_path(LANE.joinpath(*relative.parts))
        if not path.is_file() or is_link_or_junction(path):
            raise ValueError(f"browser QA input is not a regular file: {path}")
        if path.stat().st_size != record.get("bytes"):
            raise ValueError(f"browser QA input size drift: {path}")
        if sha256_file(path) != record.get("sha256"):
            raise ValueError(f"browser QA input hash drift: {path}")
    return validate_docs_links(allow_missing_generated=True)


def common_package_files() -> tuple[tuple[Path, str], ...]:
    return (
        (LANE / "README.md", "README.md"),
        (LANE / "CITATION.cff", "CITATION.cff"),
        (LANE / "LICENSES" / "README.md", "LICENSES/README.md"),
        (LANE / "LICENSES" / "MIT-NEW-CODE.txt", "LICENSES/MIT-NEW-CODE.txt"),
        (
            LANE / "LICENSES" / "MIT-UPSTREAM-CODE.txt",
            "LICENSES/MIT-UPSTREAM-CODE.txt",
        ),
        (LANE / "NOTICE" / "EDITION.md", "NOTICE/EDITION.md"),
        (DOCS_DIR / "index.html", "docs/index.html"),
        (DOCS_DIR / "assets" / "site.css", "docs/assets/site.css"),
        (DOCS_DIR / ".nojekyll", "docs/.nojekyll"),
        (RELEASE_DIR / "README.md", "release/README.md"),
        (RELEASE_DIR / "RELEASE-NOTES.md", "release/RELEASE-NOTES.md"),
        (READER_IDENTITY, "release/reader-identity.json"),
        (RELEASE_DIR / "zenodo-metadata.json", "release/zenodo-metadata.json"),
        (
            RELEASE_DIR / "github-repository-metadata.json",
            "release/github-repository-metadata.json",
        ),
        (
            LANE / "qa" / "release-package-browser-qa.json",
            "qa/release-package-browser-qa.json",
        ),
        (Path(__file__), "release/assemble_release.py"),
        (UPSTREAM_DIR / "LICENSE-Content", "LICENSES/UPSTREAM-LICENSE-Content.txt"),
        (UPSTREAM_DIR / "LICENSE-Code", "LICENSES/UPSTREAM-LICENSE-Code.txt"),
    )


def package_specs() -> tuple[PackageSpec, ...]:
    common = common_package_files()
    return (
        PackageSpec(
            output_name=SOURCE_ZIP_NAME,
            role="translated_source",
            media_type="application/zip",
            roots=(
                (LANE / "source" / "Intro-Math-Programming", "source/Intro-Math-Programming"),
                (
                    LANE / "source" / "open-optimization-bibliography",
                    "source/open-optimization-bibliography",
                ),
                (LANE / "source" / "visualizations", "source/visualizations"),
            ),
            files=common,
        ),
        PackageSpec(
            output_name=LAB_ZIP_NAME,
            role="o018_open_solver_labs",
            media_type="application/zip",
            roots=(
                (
                    LANE / "source" / "o018-open-solver-lab",
                    "source/o018-open-solver-lab",
                ),
                (
                    LANE / "authority" / "runtime-licenses",
                    "authority/runtime-licenses",
                ),
            ),
            files=common,
        ),
        PackageSpec(
            output_name=BACKEND_ZIP_NAME,
            role="modular_backend",
            media_type="application/zip",
            roots=(
                (LANE / "backend" / "input", "backend/input"),
                (LANE / "backend" / "schema", "backend/schema"),
                (LANE / "backend" / "dist", "backend/dist"),
                (
                    LANE / "authority" / "runtime-licenses",
                    "authority/runtime-licenses",
                ),
            ),
            files=(
                *common,
                (LANE / "backend" / "README.md", "backend/README.md"),
                (
                    LANE / "qa" / "backend-full-final-report.json",
                    "qa/backend-full-final-report.json",
                ),
                (
                    LANE / "00_control" / "MACHINE_BACKEND_EVIDENCE.json",
                    "00_control/MACHINE_BACKEND_EVIDENCE.json",
                ),
                (LANE / "scripts" / "export_backend.py", "scripts/export_backend.py"),
                (
                    LANE / "scripts" / "build_machine_backend_evidence.py",
                    "scripts/build_machine_backend_evidence.py",
                ),
                (
                    LANE / "scripts" / "update_backend_full_book.py",
                    "scripts/update_backend_full_book.py",
                ),
                (
                    LANE / "scripts" / "verify_csv_artifact_tool.mjs",
                    "scripts/verify_csv_artifact_tool.mjs",
                ),
                (
                    LANE
                    / "authority"
                    / "archives"
                    / "open-optimization-bibliography-f8516c2c252fda30a8d3239da05cd07c55d2631b.zip",
                    "authority/archives/open-optimization-bibliography-f8516c2c252fda30a8d3239da05cd07c55d2631b.zip",
                ),
                (
                    LANE
                    / "authority"
                    / "archives"
                    / "open-optimization-common-dee882b717018318689f4b373ea1bfc82ddaed6c.zip",
                    "authority/archives/open-optimization-common-dee882b717018318689f4b373ea1bfc82ddaed6c.zip",
                ),
                (
                    LANE
                    / "authority"
                    / "archives"
                    / "open-optimization-or-examples-dc866da8b04bc89289c87afbea649da2044c7799.zip",
                    "authority/archives/open-optimization-or-examples-dc866da8b04bc89289c87afbea649da2044c7799.zip",
                ),
            ),
        ),
    )


def artifact_record(path: Path, *, role: str, media_type: str) -> dict[str, object]:
    return {
        "file_name": path.name,
        "role": role,
        "media_type": media_type,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def assemble_pass(
    target: Path,
    *,
    pdf_identity: dict[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    target.mkdir(parents=True, exist_ok=False)
    copy_fixed(PDF_SOURCE, target / PDF_NAME)
    artifacts: list[dict[str, object]] = [
        artifact_record(
            target / PDF_NAME,
            role="book1_pdf",
            media_type="application/pdf",
        )
    ]
    skipped: list[str] = []
    for spec in package_specs():
        entries, package_skipped = collect_package(spec)
        zip_record = build_zip(target / spec.output_name, entries)
        zip_record.update({"role": spec.role, "media_type": spec.media_type})
        artifacts.append(zip_record)
        skipped.extend(package_skipped)

    support_records: list[dict[str, object]] = []
    for output_name, source in SUPPORT_OUTPUTS.items():
        destination = target / output_name
        copy_fixed(source, destination)
        support_records.append(
            artifact_record(
                destination,
                role="release_documentation",
                media_type=(
                    "text/x-cff"
                    if output_name.endswith(".cff")
                    else "application/json"
                    if output_name.endswith(".json")
                    else "text/markdown"
                ),
            )
        )

    manifest = {
        "schema_version": "1.0.0",
        "edition_id": EDITION_ID,
        "version": EDITION_VERSION,
        "title": RELEASE_TITLE,
        "language": "id-ID",
        "generated_at": FIXED_ISO_TIMESTAMP,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "upstream": {
            "repository": "https://github.com/open-optimization/open-optimization-or-book",
            "official_reader": "https://open-optimization.github.io/open-optimization-or-book/",
            "commit": UPSTREAM_COMMIT,
            "tree": UPSTREAM_TREE,
            "archive_sha256": UPSTREAM_ARCHIVE_SHA256,
        },
        "corpora": {
            "r017": "Buku 1 dan edisi Bahasa Indonesia",
            "o018": "laboratorium Pyomo+HiGHS yang diatribusikan terpisah",
        },
        "translation_provenance": {
            "assistant": "OpenAI Codex gpt-5.6-sol, Ultra",
            "requester": "the user",
            "role": "translation and production assistance",
            "authorship": "not an author",
        },
        "licenses": {
            "book_content_and_translation": "CC-BY-SA-4.0",
            "upstream_code": "MIT",
            "new_o018_and_release_code": "MIT",
            "third_party": "see LICENSES-README.md and component notices",
        },
        "accessibility": {
            "language": "id-ID",
            "unicode_text": True,
            "actual_text_and_alt_text": True,
            "bookmarks_and_links": True,
            "tagged_pdf": False,
            "pdf_ua_claim": False,
        },
        "canonical_pdf": pdf_identity,
        "artifacts": sorted(artifacts, key=lambda row: str(row["file_name"])),
        "supporting_files": sorted(
            support_records, key=lambda row: str(row["file_name"])
        ),
    }
    (target / MANIFEST_NAME).write_bytes(stable_json_bytes(manifest))
    os.utime(target / MANIFEST_NAME, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))

    checksum_targets = sorted(
        [*PRIMARY_OUTPUT_NAMES, *SUPPORT_OUTPUTS, MANIFEST_NAME]
    )
    checksum_text = "".join(
        f"{sha256_file(target / name)}  {name}\n" for name in checksum_targets
    )
    (target / CHECKSUM_NAME).write_text(checksum_text, encoding="utf-8", newline="\n")
    os.utime(target / CHECKSUM_NAME, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))
    return sorted(artifacts, key=lambda row: str(row["file_name"])), sorted(set(skipped))


def compare_passes(first: Path, second: Path) -> list[dict[str, object]]:
    verified: list[dict[str, object]] = []
    for name in sorted(ALL_OUTPUT_NAMES):
        left = first / name
        right = second / name
        if not left.is_file() or not right.is_file():
            raise ValueError(f"release replay missing output: {name}")
        left_hash = sha256_file(left)
        right_hash = sha256_file(right)
        if left.stat().st_size != right.stat().st_size or left_hash != right_hash:
            raise ValueError(f"release replay is not byte-identical: {name}")
        verified.append(
            {"file_name": name, "bytes": left.stat().st_size, "sha256": left_hash}
        )
    return verified


def reject_unknown_generated_entries(directory: Path) -> None:
    if not directory.exists():
        return
    if not directory.is_dir() or is_link_or_junction(directory):
        raise ValueError(f"generated output root is not a regular directory: {directory}")
    unknown = sorted(
        child.name for child in directory.iterdir() if child.name not in ALL_OUTPUT_NAMES
    )
    if unknown:
        raise ValueError(
            f"unknown entries in generated output root {directory}: {unknown}"
        )


def promote_outputs(stage: Path) -> None:
    reject_unknown_generated_entries(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ALL_OUTPUT_NAMES:
        source = stage / name
        destination = OUT_DIR / name
        os.replace(source, destination)
        os.utime(destination, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))


def publish_docs_downloads() -> None:
    reject_unknown_generated_entries(DOCS_DOWNLOADS)
    DOCS_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for name in ALL_OUTPUT_NAMES:
        source = OUT_DIR / name
        destination = DOCS_DOWNLOADS / name
        if destination.exists():
            if destination.is_dir() or is_link_or_junction(destination):
                raise ValueError(f"unexpected generated docs target: {destination}")
            destination.unlink()
        try:
            os.link(source, destination)
        except OSError:
            shutil.copyfile(source, destination)
        os.utime(destination, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-pdf-bytes",
        type=int,
        help="required exact final PDF byte count",
    )
    parser.add_argument(
        "--expected-pdf-sha256",
        type=str,
        help="required lowercase SHA-256 of the final PDF",
    )
    parser.add_argument(
        "--validate-static-only",
        action="store_true",
        help="validate authored release pages without assembling generated downloads",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    static_report = validate_static_files()
    if args.validate_static_only:
        print(json.dumps({"status": "ok", "docs": static_report}, sort_keys=True))
        return 0

    if args.expected_pdf_bytes is None or args.expected_pdf_bytes <= 0:
        raise ValueError("--expected-pdf-bytes is required and must be positive")
    expected_hash = (args.expected_pdf_sha256 or "").strip()
    if len(expected_hash) != 64 or any(char not in "0123456789abcdef" for char in expected_hash):
        raise ValueError("--expected-pdf-sha256 must be 64 lowercase hexadecimal characters")

    pdf_identity = verify_pdf(args.expected_pdf_bytes, expected_hash)
    backend = verify_backend()
    safe_remove_scratch(STAGE_DIR)
    safe_remove_scratch(REPLAY_DIR)
    skipped: list[str] = []
    try:
        first_artifacts, first_skipped = assemble_pass(
            STAGE_DIR, pdf_identity=pdf_identity
        )
        _, replay_skipped = assemble_pass(REPLAY_DIR, pdf_identity=pdf_identity)
        skipped.extend(first_skipped)
        skipped.extend(replay_skipped)
        deterministic_outputs = compare_passes(STAGE_DIR, REPLAY_DIR)
        backend_after = verify_backend()
        if (
            backend_after["manifest_sha256"] != backend["manifest_sha256"]
            or backend_after["manifest_bytes"] != backend["manifest_bytes"]
        ):
            raise ValueError("backend identity changed during release assembly")
        backend["post_assembly_check_passed"] = True
        backend["post_assembly_output_sha256"] = backend_after["output_sha256"]
        promote_outputs(STAGE_DIR)
        publish_docs_downloads()
        docs = validate_docs_links(allow_missing_generated=False)

        report = {
            "schema_version": "release-package-report-v1",
            "edition_id": EDITION_ID,
            "generated_at": FIXED_ISO_TIMESTAMP,
            "source_date_epoch": SOURCE_DATE_EPOCH,
            "status": "passed",
            "pdf": pdf_identity,
            "backend": backend,
            "artifacts": first_artifacts,
            "deterministic_replay": {
                "passed": True,
                "output_count": len(deterministic_outputs),
                "outputs": deterministic_outputs,
            },
            "docs": docs,
            "excluded_cache_files": sorted(set(skipped)),
            "credentials_read": False,
            "git_invoked": False,
        }
        QA_REPORT.parent.mkdir(parents=True, exist_ok=True)
        QA_REPORT.write_bytes(stable_json_bytes(report))
        os.utime(QA_REPORT, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        safe_remove_scratch(STAGE_DIR)
        safe_remove_scratch(REPLAY_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
