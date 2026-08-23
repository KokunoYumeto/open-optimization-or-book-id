#!/usr/bin/env python3
"""Publish the exact R017/O018 release payload and verify public bytes.

The credential is read only from the supplied local file and is sent only in
the Authorization header.  It is never written to disk, placed in a URL, or
included in output/receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlparse

import requests


API = "https://zenodo.org/api"
LANE = Path(__file__).resolve().parents[1]
OUTPUT = LANE / "release" / "out"
METADATA_PATH = LANE / "release" / "zenodo-metadata.json"
MANIFEST_PATH = OUTPUT / "RELEASE-MANIFEST.json"
CHECKSUM_PATH = OUTPUT / "SHA256SUMS.txt"
RECEIPT_PATH = (
    LANE
    / "release"
    / "receipts"
    / "zenodo-publication-receipt-2026.08.23-id.5.json"
)
STATE_PATH = (
    LANE / "release" / "receipts" / "zenodo-deposition-state-2026.08.23-id.5.json"
)
REQUEST_TIMEOUT = 120
EXPECTED_PREDECESSOR_RECORD_ID = 22070484
EXPECTED_PREDECESSOR_VERSION = "2026.08.23-id.4"
EXPECTED_CONCEPT_RECORD_ID = "22059794"
EXPECTED_CONCEPT_DOI = "10.5281/zenodo.22059794"
EXPECTED_EDITION_ID = "r017-o018.book1.id-ID.2026.08.23-id.5"
EXPECTED_VERSION = "2026.08.23-id.5"
EXPECTED_TITLE = "Pemrograman Matematis dan Riset Operasi — Buku 1, Edisi Bahasa Indonesia"
EXPECTED_LANGUAGE = "ind"
EXPECTED_LICENSE = "other-open"

UPLOAD_ORDER = (
    "pemrograman-matematis-dan-riset-operasi-buku-1-id-ID.pdf",
    "pemrograman-matematis-dan-riset-operasi-buku-1-source-id-ID.zip",
    "pemrograman-matematis-dan-riset-operasi-buku-1-o018-open-solver-labs-id-ID.zip",
    "pemrograman-matematis-dan-riset-operasi-buku-1-modular-backend-v0.zip",
    "README.md",
    "CITATION.cff",
    "LICENSES-README.md",
    "NOTICE-EDITION.md",
    "RELEASE-NOTES.md",
    "MIT-NEW-CODE.txt",
    "MIT-UPSTREAM-CODE.txt",
    "RELEASE-MANIFEST.json",
    "SHA256SUMS.txt",
)


def digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def identifier_values(value: Any) -> set[str]:
    """Normalize identifier-shaped metadata without accepting a missing value."""
    if value is None:
        return set()
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(identifier_values(item))
        return result
    if isinstance(value, dict):
        for key in ("id", "identifier", "value"):
            if value.get(key) is not None:
                return {str(value[key])}
        return set()
    return {str(value)}


def concept_identity(record: dict[str, Any]) -> tuple[str, str]:
    metadata = record.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    conceptrecid = str(
        record.get("conceptrecid")
        or record.get("concept_record_id")
        or metadata.get("conceptrecid")
        or metadata.get("concept_record_id")
        or ""
    )
    conceptdoi = str(
        record.get("conceptdoi")
        or record.get("concept_doi")
        or metadata.get("conceptdoi")
        or metadata.get("concept_doi")
        or ""
    )
    return conceptrecid, conceptdoi


def assert_concept_identity(record: dict[str, Any], *, label: str) -> None:
    conceptrecid, conceptdoi = concept_identity(record)
    if conceptrecid != EXPECTED_CONCEPT_RECORD_ID or conceptdoi != EXPECTED_CONCEPT_DOI:
        raise RuntimeError(
            f"{label} is outside the frozen Zenodo concept lineage: "
            f"conceptrecid={conceptrecid!r}, conceptdoi={conceptdoi!r}"
        )


def assert_deposition_concept_identity(record: dict[str, Any], *, label: str) -> None:
    """Require the concept record ID; tolerate an omitted draft concept DOI only."""
    conceptrecid, conceptdoi = concept_identity(record)
    if (
        conceptrecid != EXPECTED_CONCEPT_RECORD_ID
        or conceptdoi not in {"", EXPECTED_CONCEPT_DOI}
    ):
        raise RuntimeError(
            f"{label} is outside the frozen Zenodo concept lineage: "
            f"conceptrecid={conceptrecid!r}, conceptdoi={conceptdoi!r}"
        )


def record_doi(record: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    direct = str(metadata.get("doi") or record.get("doi") or "")
    if direct:
        return direct
    pids = record.get("pids", {})
    if isinstance(pids, dict):
        doi = pids.get("doi", {})
        if isinstance(doi, dict):
            return str(doi.get("identifier") or "")
    return ""


def validate_authored_metadata(wrapper: Any) -> dict[str, Any]:
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get("metadata"), dict):
        raise RuntimeError("zenodo-metadata.json must contain one metadata object.")
    metadata = wrapper["metadata"]
    required = {
        "title": EXPECTED_TITLE,
        "version": EXPECTED_VERSION,
        "language": EXPECTED_LANGUAGE,
        "license": EXPECTED_LICENSE,
        "access_right": "open",
        "upload_type": "publication",
        "publication_type": "book",
    }
    drift = {
        key: metadata.get(key)
        for key, expected in required.items()
        if metadata.get(key) != expected
    }
    if drift:
        raise RuntimeError(f"Zenodo authored metadata drift: {drift}")
    return metadata


def candidate_tokens(path: Path) -> Iterable[str]:
    raw = path.read_text(encoding="utf-8-sig")
    seen: set[str] = set()
    for candidate in re.findall(r"(?<![A-Za-z0-9._-])[A-Za-z0-9._-]{40,}(?![A-Za-z0-9._-])", raw):
        if candidate not in seen:
            seen.add(candidate)
            yield candidate


def authenticated_session(token_file: Path) -> requests.Session:
    for candidate in candidate_tokens(token_file):
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {candidate}",
                "User-Agent": "interlanguage-r017-o018-release/1.0",
            }
        )
        response = session.get(
            f"{API}/deposit/depositions",
            params={"size": 1},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return session
        session.close()
    raise RuntimeError("No credential in the supplied file authenticated with Zenodo.")


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    expected: tuple[int, ...] = (200,),
    **kwargs: Any,
) -> dict[str, Any] | list[Any]:
    response = session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    if response.status_code not in expected:
        detail = response.text[:1000].replace("\r", " ").replace("\n", " ")
        raise RuntimeError(
            f"Zenodo {method} {urlparse(url).path} returned "
            f"HTTP {response.status_code}: {detail}"
        )
    if not response.content:
        return {}
    return response.json()


def exact_local_files() -> list[dict[str, Any]]:
    if not OUTPUT.is_dir() or OUTPUT.is_symlink():
        raise RuntimeError("release/out is not a regular release directory.")
    entries = list(OUTPUT.iterdir())
    actual_names = {path.name for path in entries}
    expected_names = set(UPLOAD_ORDER)
    if actual_names != expected_names:
        raise RuntimeError(
            "release/out inventory differs from the exact 13-file Zenodo payload: "
            f"missing={sorted(expected_names - actual_names)}, "
            f"extra={sorted(actual_names - expected_names)}"
        )
    records: list[dict[str, Any]] = []
    for name in UPLOAD_ORDER:
        path = OUTPUT / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"release payload entry is not a regular file: {name}")
        records.append(
            {
                "name": name,
                "path": path,
                "bytes": path.stat().st_size,
                "sha256": digest(path),
                "md5": digest(path, "md5"),
            }
        )

    by_name = {str(record["name"]): record for record in records}
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("RELEASE-MANIFEST.json is unreadable.") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("RELEASE-MANIFEST.json must contain one object.")
    manifest_required = {
        "edition_id": EXPECTED_EDITION_ID,
        "version": EXPECTED_VERSION,
        "title": EXPECTED_TITLE,
        "language": "id-ID",
    }
    manifest_drift = {
        key: manifest.get(key)
        for key, expected in manifest_required.items()
        if manifest.get(key) != expected
    }
    if manifest_drift:
        raise RuntimeError(f"Release manifest identity drift: {manifest_drift}")

    bound_rows: list[dict[str, Any]] = []
    for field in ("artifacts", "supporting_files"):
        rows = manifest.get(field)
        if not isinstance(rows, list):
            raise RuntimeError(f"Release manifest {field} must be a list.")
        if any(not isinstance(row, dict) for row in rows):
            raise RuntimeError(f"Release manifest {field} contains a non-object record.")
        bound_rows.extend(rows)
    bound_names = [str(row.get("file_name") or "") for row in bound_rows]
    expected_bound_names = set(UPLOAD_ORDER) - {"RELEASE-MANIFEST.json", "SHA256SUMS.txt"}
    if (
        any(not name for name in bound_names)
        or len(bound_names) != len(set(bound_names))
        or set(bound_names) != expected_bound_names
    ):
        raise RuntimeError("Release manifest does not bind the exact 11 represented payload files.")
    for row in bound_rows:
        name = str(row["file_name"])
        local = by_name[name]
        if row.get("bytes") != local["bytes"] or row.get("sha256") != local["sha256"]:
            raise RuntimeError(f"Release manifest byte identity drift for {name}.")

    checksum_rows: dict[str, str] = {}
    try:
        checksum_lines = CHECKSUM_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError("SHA256SUMS.txt is unreadable.") from exc
    for line in checksum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\\/]+)", line)
        if not match or match.group(2) in checksum_rows:
            raise RuntimeError("SHA256SUMS.txt is malformed or contains duplicates.")
        checksum_rows[match.group(2)] = match.group(1)
    expected_checksum_names = set(UPLOAD_ORDER) - {"SHA256SUMS.txt"}
    if set(checksum_rows) != expected_checksum_names:
        raise RuntimeError("SHA256SUMS.txt does not bind the exact other 12 payload files.")
    for name, expected_sha256 in checksum_rows.items():
        if by_name[name]["sha256"] != expected_sha256:
            raise RuntimeError(f"SHA256SUMS.txt byte identity drift for {name}.")

    canonical_pdf = manifest.get("canonical_pdf")
    pdf = by_name[UPLOAD_ORDER[0]]
    if (
        not isinstance(canonical_pdf, dict)
        or canonical_pdf.get("bytes") != pdf["bytes"]
        or canonical_pdf.get("sha256") != pdf["sha256"]
    ):
        raise RuntimeError("Release manifest canonical PDF identity drift.")
    return records


def normalize_depositions(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        hits = data.get("hits", {}).get("hits", [])
        if isinstance(hits, list):
            return [item for item in hits if isinstance(item, dict)]
    return []


def normalize_record_files(data: dict[str, Any]) -> list[dict[str, Any]]:
    files = data.get("files", [])
    if isinstance(files, list):
        return [item for item in files if isinstance(item, dict)]
    if isinstance(files, dict):
        entries = files.get("entries", [])
        if isinstance(entries, list):
            return [item for item in entries if isinstance(item, dict)]
    return []


def filename_of(record: dict[str, Any]) -> str:
    return str(record.get("key") or record.get("filename") or "")


def size_of(record: dict[str, Any]) -> int:
    value = record.get("size")
    if value is None:
        value = record.get("filesize")
    return int(value or 0)


def md5_of(record: dict[str, Any]) -> str:
    checksum = str(record.get("checksum") or "")
    if checksum.startswith("md5:"):
        checksum = checksum[4:]
    return checksum.lower()


def unique_file_map(record: dict[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    rows = normalize_record_files(record)
    names = [filename_of(row) for row in rows]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise RuntimeError(f"{label} has empty or duplicate filenames.")
    return {name: row for name, row in zip(names, rows, strict=True)}


def exact_metadata(record: dict[str, Any], title: str, version: str) -> bool:
    metadata = record.get("metadata", {})
    return (
        isinstance(metadata, dict)
        and metadata.get("title") == title
        and metadata.get("version") == version
    )


def assert_final_public_metadata(
    record: dict[str, Any], *, record_id: int, title: str, version: str
) -> None:
    if int(record.get("id") or 0) != record_id:
        raise RuntimeError("Public Zenodo record ID drifted during readback.")
    if not exact_metadata(record, title, version):
        raise RuntimeError("Public Zenodo title or version drifted.")
    metadata = record.get("metadata", {})
    if not isinstance(metadata, dict):
        raise RuntimeError("Public Zenodo metadata is not an object.")
    languages = identifier_values(metadata.get("language"))
    if not languages:
        languages = identifier_values(metadata.get("languages"))
    licenses = identifier_values(metadata.get("license"))
    if not licenses:
        licenses = identifier_values(metadata.get("rights"))
    if languages != {EXPECTED_LANGUAGE}:
        raise RuntimeError(f"Public Zenodo language drift: {sorted(languages)}")
    if licenses != {EXPECTED_LICENSE}:
        raise RuntimeError(f"Public Zenodo license drift: {sorted(licenses)}")
    assert_concept_identity(record, label="Public Zenodo record")
    expected_doi = f"10.5281/zenodo.{record_id}"
    if record_doi(record) != expected_doi:
        raise RuntimeError(
            f"Public Zenodo DOI drift: expected {expected_doi!r}, observed {record_doi(record)!r}"
        )


def public_hits(title: str, version: str) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": "interlanguage-r017-o018-readback/1.0"})
    data = request_json(
        session,
        "GET",
        f"{API}/records",
        params={
            "q": f'metadata.title:"{title}" AND metadata.version:"{version}"',
            "size": 25,
        },
    )
    session.close()
    return [
        item
        for item in normalize_depositions(data)
        if exact_metadata(item, title, version)
    ]


def verify_predecessor_record(predecessor_record_id: int) -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "interlanguage-r017-o018-lineage-check/1.0"})
    try:
        record = request_json(
            session,
            "GET",
            f"{API}/records/{predecessor_record_id}",
        )
    finally:
        session.close()
    if not isinstance(record, dict):
        raise RuntimeError("Zenodo predecessor readback is not an object.")
    if int(record.get("id") or 0) != EXPECTED_PREDECESSOR_RECORD_ID:
        raise RuntimeError("Zenodo predecessor record ID drifted.")
    if not exact_metadata(record, EXPECTED_TITLE, EXPECTED_PREDECESSOR_VERSION):
        raise RuntimeError("Zenodo predecessor title or version drifted.")
    assert_concept_identity(record, label="Zenodo predecessor")
    expected_doi = f"10.5281/zenodo.{EXPECTED_PREDECESSOR_RECORD_ID}"
    if record_doi(record) != expected_doi:
        raise RuntimeError("Zenodo predecessor DOI drifted.")


def deposition_id_from_url(value: Any) -> int:
    path = urlparse(str(value or "")).path.rstrip("/")
    match = re.search(r"/(\d+)$", path)
    return int(match.group(1)) if match else 0


def assert_direct_draft_lineage(
    session: requests.Session,
    deposition: dict[str, Any],
    predecessor_record_id: int,
) -> None:
    if bool(deposition.get("submitted")):
        raise RuntimeError("Zenodo draft lineage check received a submitted record.")
    assert_deposition_concept_identity(deposition, label="Zenodo draft")
    draft_id = int(deposition.get("id") or 0)
    if draft_id <= 0:
        raise RuntimeError("Zenodo draft has no valid deposition ID.")
    draft_links = deposition.get("links", {})
    if not isinstance(draft_links, dict):
        raise RuntimeError("Zenodo draft links are not an object.")
    if deposition_id_from_url(draft_links.get("self")) != draft_id:
        raise RuntimeError("Zenodo draft self-link does not bind its deposition ID.")
    if deposition_id_from_url(draft_links.get("latest_draft")) != draft_id:
        raise RuntimeError("Zenodo draft latest_draft link does not bind itself.")

    predecessor = request_json(
        session,
        "GET",
        f"{API}/records/{predecessor_record_id}",
    )
    if not isinstance(predecessor, dict):
        raise RuntimeError("Zenodo predecessor readback is not an object.")
    if int(predecessor.get("id") or 0) != predecessor_record_id:
        raise RuntimeError("Zenodo predecessor ID drifted during draft validation.")
    if not exact_metadata(predecessor, EXPECTED_TITLE, EXPECTED_PREDECESSOR_VERSION):
        raise RuntimeError("Zenodo predecessor metadata drifted during draft validation.")
    assert_concept_identity(predecessor, label="Zenodo predecessor")

    latest = request_json(
        session,
        "GET",
        f"{API}/records/{predecessor_record_id}/versions/latest",
    )
    if not isinstance(latest, dict) or int(latest.get("id") or 0) != predecessor_record_id:
        raise RuntimeError(
            "The frozen predecessor is no longer the latest public version in its concept."
        )
    assert_concept_identity(latest, label="Latest public Zenodo version")

    drafts = same_concept_drafts(session)
    if len(drafts) != 1 or int(drafts[0].get("id") or 0) != draft_id:
        raise RuntimeError(
            "Zenodo concept does not have exactly this one unpublished next-version draft."
        )


def own_drafts(
    session: requests.Session, title: str, version: str
) -> list[dict[str, Any]]:
    data = request_json(
        session,
        "GET",
        f"{API}/deposit/depositions",
        params={"q": f'title:"{title}"', "size": 100},
    )
    return [
        item
        for item in normalize_depositions(data)
        if exact_metadata(item, title, version) and not bool(item.get("submitted"))
    ]


def same_concept_drafts(session: requests.Session) -> list[dict[str, Any]]:
    data = request_json(
        session,
        "GET",
        f"{API}/deposit/depositions",
        params={"q": f"conceptrecid:{EXPECTED_CONCEPT_RECORD_ID}", "size": 100},
    )
    drafts = [
        item
        for item in normalize_depositions(data)
        if not bool(item.get("submitted"))
    ]
    for draft in drafts:
        assert_deposition_concept_identity(draft, label="Zenodo concept draft")
    return drafts


def write_state(
    deposition_id: int,
    title: str,
    version: str,
    predecessor_record_id: int,
    manifest_sha256: str,
) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "schema": "zenodo-deposition-state-v2",
        "deposition_id": deposition_id,
        "title": title,
        "version": version,
        "predecessor_record_id": predecessor_record_id,
        "concept_record_id": EXPECTED_CONCEPT_RECORD_ID,
        "concept_doi": EXPECTED_CONCEPT_DOI,
        "release_manifest_sha256": manifest_sha256,
        "credential_material": False,
    }
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def resume_state(
    session: requests.Session,
    title: str,
    version: str,
    predecessor_record_id: int,
    manifest_sha256: str,
) -> dict[str, Any] | None:
    if not STATE_PATH.is_file():
        return None
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if (
        state.get("schema") != "zenodo-deposition-state-v2"
        or state.get("title") != title
        or state.get("version") != version
        or int(state.get("predecessor_record_id", 0)) != predecessor_record_id
        or str(state.get("concept_record_id") or "") != EXPECTED_CONCEPT_RECORD_ID
        or str(state.get("concept_doi") or "") != EXPECTED_CONCEPT_DOI
        or str(state.get("release_manifest_sha256") or "") != manifest_sha256
    ):
        raise RuntimeError("Zenodo deposition state belongs to another release.")
    deposition_id = int(state["deposition_id"])
    deposition = request_json(
        session, "GET", f"{API}/deposit/depositions/{deposition_id}"
    )
    assert isinstance(deposition, dict)
    if bool(deposition.get("submitted")):
        raise RuntimeError("Saved Zenodo state unexpectedly points to a published record.")
    assert_direct_draft_lineage(session, deposition, predecessor_record_id)
    return deposition


def new_version_draft(
    session: requests.Session, predecessor_record_id: int
) -> dict[str, Any]:
    result = request_json(
        session,
        "POST",
        f"{API}/deposit/depositions/{predecessor_record_id}/actions/newversion",
        expected=(201, 202),
    )
    assert isinstance(result, dict)
    links = result.get("links", {})
    latest_draft = links.get("latest_draft") if isinstance(links, dict) else None
    if not latest_draft:
        raise RuntimeError("Zenodo new-version response omitted links.latest_draft.")
    draft = request_json(session, "GET", str(latest_draft))
    assert isinstance(draft, dict)
    if bool(draft.get("submitted")):
        raise RuntimeError("Zenodo latest_draft is already submitted.")
    return draft


def delete_deposition_file(
    session: requests.Session,
    deposition: dict[str, Any],
    file_record: dict[str, Any],
) -> None:
    links = file_record.get("links", {})
    file_url = links.get("self") if isinstance(links, dict) else None
    if file_url:
        response = session.delete(file_url, timeout=REQUEST_TIMEOUT)
    else:
        bucket = str(deposition.get("links", {}).get("bucket", "")).rstrip("/")
        if not bucket:
            raise RuntimeError("Cannot locate Zenodo draft file deletion endpoint.")
        response = session.delete(
            f"{bucket}/{quote(filename_of(file_record), safe='')}",
            timeout=REQUEST_TIMEOUT,
        )
    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"Zenodo draft file deletion returned HTTP {response.status_code}."
        )


def upload_files(
    session: requests.Session,
    deposition: dict[str, Any],
    local_files: list[dict[str, Any]],
) -> dict[str, Any]:
    deposition_id = int(deposition["id"])
    deposit_url = f"{API}/deposit/depositions/{deposition_id}"
    refreshed = request_json(session, "GET", deposit_url)
    assert isinstance(refreshed, dict)
    existing = unique_file_map(refreshed, label="Zenodo draft inventory")
    expected_names = {item["name"] for item in local_files}

    for name, record in list(existing.items()):
        expected = next((item for item in local_files if item["name"] == name), None)
        checksum = md5_of(record)
        if (
            expected is None
            or size_of(record) != expected["bytes"]
            or checksum != expected["md5"]
        ):
            delete_deposition_file(session, refreshed, record)
            existing.pop(name, None)

    bucket = str(refreshed.get("links", {}).get("bucket", "")).rstrip("/")
    if not bucket:
        raise RuntimeError("Zenodo draft did not provide a bucket URL.")

    for local in local_files:
        if local["name"] in existing:
            continue
        with local["path"].open("rb") as stream:
            response = session.put(
                f"{bucket}/{quote(local['name'], safe='')}",
                data=stream,
                timeout=REQUEST_TIMEOUT,
            )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Zenodo upload for {local['name']} returned "
                f"HTTP {response.status_code}: {response.text[:500]}"
            )

    verified = request_json(session, "GET", deposit_url)
    assert isinstance(verified, dict)
    remote = unique_file_map(verified, label="Verified Zenodo draft inventory")
    if set(remote) != expected_names:
        raise RuntimeError(
            "Zenodo draft inventory mismatch after upload: "
            f"expected={sorted(expected_names)}, observed={sorted(remote)}"
        )
    for local in local_files:
        record = remote[local["name"]]
        checksum = md5_of(record)
        if size_of(record) != local["bytes"]:
            raise RuntimeError(f"Zenodo draft byte count mismatch for {local['name']}.")
        if checksum != local["md5"]:
            raise RuntimeError(f"Zenodo draft checksum mismatch for {local['name']}.")
    return verified


def download_url(file_record: dict[str, Any]) -> str:
    links = file_record.get("links", {})
    if not isinstance(links, dict):
        return ""
    return str(
        links.get("content")
        or links.get("download")
        or links.get("self")
        or ""
    )


def verify_public_record(
    record_id: int,
    local_files: list[dict[str, Any]],
    *,
    title: str,
    version: str,
    attempts: int = 18,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session = requests.Session()
    session.headers.update({"User-Agent": "interlanguage-r017-o018-readback/1.0"})
    record: dict[str, Any] | None = None
    for attempt in range(attempts):
        response = session.get(
            f"{API}/records/{record_id}",
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            parsed = response.json()
            if isinstance(parsed, dict) and normalize_record_files(parsed):
                record = parsed
                break
        if attempt + 1 < attempts:
            time.sleep(5)
    if record is None:
        session.close()
        raise RuntimeError("Published Zenodo record did not become anonymously readable.")

    try:
        assert_final_public_metadata(
            record,
            record_id=record_id,
            title=title,
            version=version,
        )
        remote = unique_file_map(record, label="Public Zenodo inventory")
    except Exception:
        session.close()
        raise
    expected_names = {item["name"] for item in local_files}
    if set(remote) != expected_names:
        session.close()
        raise RuntimeError(
            "Public Zenodo inventory mismatch: "
            f"expected={sorted(expected_names)}, observed={sorted(remote)}"
        )

    readback: list[dict[str, Any]] = []
    for local in local_files:
        file_record = remote[local["name"]]
        url = download_url(file_record)
        if not url:
            session.close()
            raise RuntimeError(f"No public download URL for {local['name']}.")
        response = session.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            session.close()
            raise RuntimeError(
                f"Anonymous download for {local['name']} returned "
                f"HTTP {response.status_code}."
            )
        hasher = hashlib.sha256()
        count = 0
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                hasher.update(chunk)
                count += len(chunk)
        observed_hash = hasher.hexdigest()
        if count != local["bytes"] or observed_hash != local["sha256"]:
            session.close()
            raise RuntimeError(
                f"Anonymous byte readback mismatch for {local['name']}: "
                f"{count}/{observed_hash}"
            )
        readback.append(
            {
                "name": local["name"],
                "bytes": count,
                "sha256": observed_hash,
                "download_url": url,
                "anonymous_readback": True,
            }
        )
    session.close()
    return record, readback


def publish(token_file: Path, predecessor_record_id: int) -> dict[str, Any]:
    if predecessor_record_id != EXPECTED_PREDECESSOR_RECORD_ID:
        raise RuntimeError(
            "This release is bound to Zenodo predecessor record "
            f"{EXPECTED_PREDECESSOR_RECORD_ID}, not {predecessor_record_id}."
        )
    try:
        metadata_wrapper = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("zenodo-metadata.json is unreadable.") from exc
    metadata = validate_authored_metadata(metadata_wrapper)
    title = str(metadata["title"])
    version = str(metadata["version"])
    local_files = exact_local_files()
    manifest_sha256 = next(
        str(row["sha256"])
        for row in local_files
        if row["name"] == "RELEASE-MANIFEST.json"
    )
    verify_predecessor_record(predecessor_record_id)

    existing_public = public_hits(title, version)
    if len(existing_public) > 1:
        raise RuntimeError("More than one exact public Zenodo record already exists.")
    if existing_public:
        assert_concept_identity(existing_public[0], label="Existing public Zenodo record")
        record_id = int(existing_public[0]["id"])
        record, readback = verify_public_record(
            record_id,
            local_files,
            title=title,
            version=version,
        )
    else:
        session = authenticated_session(token_file)
        deposition = resume_state(
            session,
            title,
            version,
            predecessor_record_id,
            manifest_sha256,
        )
        if deposition is None:
            drafts = same_concept_drafts(session)
            if len(drafts) > 1:
                session.close()
                raise RuntimeError("More than one unpublished draft exists in the concept.")
            deposition = (
                drafts[0]
                if drafts
                else new_version_draft(session, predecessor_record_id)
            )

        assert_direct_draft_lineage(session, deposition, predecessor_record_id)
        deposition_id = int(deposition["id"])
        write_state(
            deposition_id,
            title,
            version,
            predecessor_record_id,
            manifest_sha256,
        )
        updated = request_json(
            session,
            "PUT",
            f"{API}/deposit/depositions/{deposition_id}",
            json=metadata_wrapper,
        )
        assert isinstance(updated, dict)
        if not exact_metadata(updated, title, version):
            session.close()
            raise RuntimeError("Zenodo draft title or version drifted after metadata update.")
        updated_metadata = updated.get("metadata", {})
        if not isinstance(updated_metadata, dict):
            session.close()
            raise RuntimeError("Zenodo draft metadata is not an object after update.")
        if identifier_values(updated_metadata.get("language")) != {EXPECTED_LANGUAGE}:
            session.close()
            raise RuntimeError("Zenodo draft language drifted after metadata update.")
        if identifier_values(updated_metadata.get("license")) != {EXPECTED_LICENSE}:
            session.close()
            raise RuntimeError("Zenodo draft license drifted after metadata update.")
        assert_direct_draft_lineage(session, updated, predecessor_record_id)
        upload_files(session, updated, local_files)
        published = request_json(
            session,
            "POST",
            f"{API}/deposit/depositions/{deposition_id}/actions/publish",
            expected=(201, 202),
        )
        assert isinstance(published, dict)
        record_id = int(published.get("record_id") or published.get("id") or deposition_id)
        session.close()
        record, readback = verify_public_record(
            record_id,
            local_files,
            title=title,
            version=version,
        )

    doi = record_doi(record)
    conceptrecid, conceptdoi = concept_identity(record)
    record_id = int(record["id"])
    assert_final_public_metadata(
        record,
        record_id=record_id,
        title=title,
        version=version,
    )
    receipt = {
        "schema": "zenodo-publication-receipt-v1",
        "status": "published_and_anonymously_verified",
        "verified_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "record_id": record_id,
        "concept_record_id": conceptrecid,
        "doi": doi,
        "concept_doi": conceptdoi,
        "record_url": f"https://zenodo.org/records/{record_id}",
        "title": title,
        "version": version,
        "predecessor_record_id": predecessor_record_id,
        "release_manifest_sha256": manifest_sha256,
        "file_count": len(readback),
        "files": readback,
        "checks": {
            "exact_inventory": True,
            "all_public_bytes_match_local_sha256": True,
            "anonymous_readback": True,
            "credential_in_url": False,
            "credential_material_persisted": False,
            "concept_lineage_exact": True,
            "direct_predecessor_exact": True,
            "title_version_language_license_exact": True,
            "release_manifest_and_checksums_exact": True,
        },
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    return {
        "status": receipt["status"],
        "record_id": record_id,
        "doi": doi,
        "concept_doi": conceptdoi,
        "record_url": receipt["record_url"],
        "file_count": len(readback),
        "receipt": RECEIPT_PATH.relative_to(LANE).as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--new-version-of", type=int, required=True)
    args = parser.parse_args()
    summary = publish(args.token_file.resolve(), args.new_version_of)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
