#!/usr/bin/env python3
"""Publish the frozen R017/O018 edition to one bounded GitHub repository.

The publication tree is reconstructed from the three deterministic release
ZIPs plus an explicit small overlay.  It never scans the workspace, never runs
Git, and never places a credential in a URL, file, or user-visible output.

Run --plan-only while GitHub access is unavailable.  The mutating mode is for
the already-authorized publication after the account suspension is lifted.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import quote, urlparse

import requests


API = "https://api.github.com"
LANE = Path(__file__).resolve().parents[1]
RELEASE_OUT = LANE / "release" / "out"
METADATA_PATH = LANE / "release" / "github-repository-metadata.json"
PLAN_PATH = LANE / "qa" / "github-publication-plan.json"
RECEIPT_PATH = LANE / "release" / "receipts" / "github-publication-receipt.json"
STATE_PATH = LANE / "release" / "receipts" / "github-publication-state.json"
VERSION = "2026.08.23-id.5"
TAG = f"v{VERSION}"
REQUEST_TIMEOUT = 120
MAX_FILE_BYTES = 100 * 1024 * 1024

PACKAGE_NAMES = (
    "pemrograman-matematis-dan-riset-operasi-buku-1-source-id-ID.zip",
    "pemrograman-matematis-dan-riset-operasi-buku-1-o018-open-solver-labs-id-ID.zip",
    "pemrograman-matematis-dan-riset-operasi-buku-1-modular-backend-v0.zip",
)
RELEASE_ASSET_ORDER = (
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
LIVE_OVERLAYS = {
    "README.md": LANE / "README.md",
    "CITATION.cff": LANE / "CITATION.cff",
    "LICENSE": LANE / "LICENSE",
    ".gitignore": LANE / ".gitignore",
    "qa/book1-final-verify.py": LANE / "qa" / "book1-final-verify.py",
    "qa/book1-final-qa-report.json": LANE / "qa" / "book1-final-qa-report.json",
    "qa/backend-full-final-report.json": LANE / "qa" / "backend-full-final-report.json",
    "qa/release-package-report.json": LANE / "qa" / "release-package-report.json",
    "release/publish_zenodo.py": LANE / "release" / "publish_zenodo.py",
    "release/publish_github.py": Path(__file__).resolve(),
    "release/receipts/zenodo-publication-receipt.json": (
        LANE
        / "release"
        / "receipts"
        / "zenodo-publication-receipt-2026.08.23-id.5.json"
    ),
    "release/receipts/zenodo-publication-receipt-2026.08.23-id.5.json": (
        LANE
        / "release"
        / "receipts"
        / "zenodo-publication-receipt-2026.08.23-id.5.json"
    ),
    "output/book1-pdf/book1-id.pdf": LANE / "output" / "book1-pdf" / "book1-id.pdf",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def safe_repo_path(raw: str) -> str:
    if "\\" in raw or raw.startswith("/"):
        raise ValueError(f"unsafe repository path: {raw!r}")
    path = PurePosixPath(raw)
    if not path.parts or any(part in ("", ".", "..", ".git") for part in path.parts):
        raise ValueError(f"unsafe repository path: {raw!r}")
    return path.as_posix()


def add_bytes(
    inventory: dict[str, bytes],
    path: str,
    data: bytes,
    *,
    replace: bool = False,
) -> None:
    path = safe_repo_path(path)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"GitHub file exceeds 100 MiB: {path} ({len(data)} bytes)")
    prior = inventory.get(path)
    if prior is not None and prior != data and not replace:
        raise ValueError(f"deterministic package collision at {path}")
    inventory[path] = data


def zip_union() -> dict[str, bytes]:
    inventory: dict[str, bytes] = {}
    for package_name in PACKAGE_NAMES:
        package = RELEASE_OUT / package_name
        if not package.is_file():
            raise FileNotFoundError(package)
        with zipfile.ZipFile(package) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise ValueError(f"corrupt release ZIP entry: {package_name}:{bad}")
            for info in sorted(archive.infolist(), key=lambda item: item.filename):
                if info.is_dir():
                    continue
                path = safe_repo_path(info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise ValueError(f"symlink rejected from release ZIP: {path}")
                add_bytes(inventory, path, archive.read(info))
    return inventory


def publication_inventory() -> dict[str, bytes]:
    inventory = zip_union()
    for path, local in LIVE_OVERLAYS.items():
        if not local.is_file():
            raise FileNotFoundError(local)
        add_bytes(inventory, path, local.read_bytes(), replace=True)
    for name in RELEASE_ASSET_ORDER:
        artifact = RELEASE_OUT / name
        if not artifact.is_file():
            raise FileNotFoundError(artifact)
        add_bytes(
            inventory,
            f"docs/downloads/{name}",
            artifact.read_bytes(),
            replace=True,
        )
    return dict(sorted(inventory.items()))


def inventory_records(inventory: dict[str, bytes]) -> list[dict[str, Any]]:
    return [
        {
            "path": path,
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "git_blob_sha1": git_blob_sha1(data),
        }
        for path, data in inventory.items()
    ]


def inventory_aggregate(records: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(canonical)


def exact_release_assets() -> list[dict[str, Any]]:
    actual = {path.name for path in RELEASE_OUT.iterdir() if path.is_file()}
    expected = set(RELEASE_ASSET_ORDER)
    if actual != expected:
        raise ValueError(
            "release/out differs from the exact 13-file release: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    return [
        {
            "name": name,
            "path": RELEASE_OUT / name,
            "bytes": (RELEASE_OUT / name).stat().st_size,
            "sha256": sha256_bytes((RELEASE_OUT / name).read_bytes()),
        }
        for name in RELEASE_ASSET_ORDER
    ]


def build_plan(
    expected_owner: str, *, write: bool = True
) -> tuple[dict[str, bytes], dict[str, Any]]:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    inventory = publication_inventory()
    records = inventory_records(inventory)
    release_assets = exact_release_assets()
    plan = {
        "schema": "github-publication-plan-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "ready_for_publication",
        "network_access": False,
        "git_invoked": False,
        "expected_owner": expected_owner,
        "repository_name": metadata["repository_name"],
        "repository_visibility": "public",
        "default_branch": "main",
        "pages_source": metadata["pages"]["source"],
        "release_tag": TAG,
        "repository_inventory": {
            "file_count": len(records),
            "checkout_bytes": sum(record["bytes"] for record in records),
            "unique_blob_count": len({record["git_blob_sha1"] for record in records}),
            "unique_blob_bytes": sum(
                len(inventory[next(path for path, data in inventory.items() if git_blob_sha1(data) == blob)])
                for blob in {record["git_blob_sha1"] for record in records}
            ),
            "aggregate_sha256": inventory_aggregate(records),
            "files": records,
            "largest_files": sorted(
                (
                    {"path": record["path"], "bytes": record["bytes"], "sha256": record["sha256"]}
                    for record in records
                    if record["bytes"] >= 10 * 1024 * 1024
                ),
                key=lambda item: (-item["bytes"], item["path"]),
            ),
        },
        "release_assets": [
            {key: value for key, value in item.items() if key != "path"}
            for item in release_assets
        ],
        "transaction": [
            "Authenticate the exact expected owner with a header-only token.",
            "Create or update only the named public repository.",
            "Create one exact main-branch tree from the deterministic package union.",
            "Apply description, topics, issue/project/wiki settings, and Pages /docs source.",
            "Create or update one release tag and upload the exact 13 frozen assets.",
            "Anonymously verify the repository tree, release assets, Pages HTML, and all 13 Pages downloads.",
            "Write a sanitized local receipt containing no credential material.",
        ],
        "explicitly_excluded": [
            "00_control/",
            "authority archives/upstream/external/submodules/runtime wheels",
            "backend/dist-candidate/",
            "output trees other than the exact canonical Book 1 PDF alias",
            "qa render/replay/scratch trees",
            "release/out/ as a directory (its exact bytes are published under docs/downloads and as release assets)",
            "tmp/",
            "credentials and transient publication-state files",
            "symlinks, caches, and unknown paths",
        ],
    }
    if write:
        PLAN_PATH.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return inventory, plan


def candidate_tokens(path: Path) -> Iterable[str]:
    raw = path.read_text(encoding="utf-8-sig")
    seen: set[str] = set()
    for candidate in re.findall(
        r"(?<![A-Za-z0-9._-])[A-Za-z0-9._-]{40,}(?![A-Za-z0-9._-])",
        raw,
    ):
        if candidate not in seen:
            seen.add(candidate)
            yield candidate


def authenticated_session(
    token_file: Path, expected_owner: str
) -> tuple[requests.Session, dict[str, Any]]:
    for candidate in candidate_tokens(token_file):
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {candidate}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "interlanguage-r017-o018-release/1.0",
            }
        )
        response = session.get(f"{API}/user", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            user = response.json()
            if str(user.get("login", "")).casefold() == expected_owner.casefold():
                return session, user
        session.close()
    raise RuntimeError(
        f"No credential authenticated as the exact expected owner {expected_owner}."
    )


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
            f"GitHub {method} {urlparse(url).path} returned "
            f"HTTP {response.status_code}: {detail}"
        )
    if not response.content:
        return {}
    return response.json()


def get_optional(
    session: requests.Session, url: str
) -> dict[str, Any] | list[Any] | None:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        detail = response.text[:1000].replace("\r", " ").replace("\n", " ")
        raise RuntimeError(
            f"GitHub GET {urlparse(url).path} returned "
            f"HTTP {response.status_code}: {detail}"
        )
    return response.json()


def ensure_repository(
    session: requests.Session,
    owner: str,
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    name = metadata["repository_name"]
    repo_url = f"{API}/repos/{owner}/{name}"
    repo = get_optional(session, repo_url)
    created_now = False
    if repo is None:
        created = request_json(
            session,
            "POST",
            f"{API}/user/repos",
            expected=(201,),
            json={
                "name": name,
                "description": metadata["description"],
                "private": False,
                "has_issues": metadata["has_issues"],
                "has_projects": metadata["has_projects"],
                "has_wiki": metadata["has_wiki"],
                "has_discussions": metadata["has_discussions"],
                "auto_init": True,
            },
        )
        assert isinstance(created, dict)
        repo = created
        created_now = True
    assert isinstance(repo, dict)
    if str(repo.get("owner", {}).get("login", "")).casefold() != owner.casefold():
        raise RuntimeError("Resolved repository does not belong to expected owner.")
    if bool(repo.get("private")):
        raise RuntimeError("The dedicated publication repository is unexpectedly private.")
    return repo, created_now


def ensure_main_seed(
    session: requests.Session,
    owner: str,
    repository: str,
    repo: dict[str, Any],
) -> None:
    for _ in range(12):
        main = get_optional(
            session,
            f"{API}/repos/{owner}/{repository}/git/ref/heads/main",
        )
        if main is not None:
            return
        default_branch = str(repo.get("default_branch") or "")
        if default_branch and default_branch != "main":
            seed = get_optional(
                session,
                f"{API}/repos/{owner}/{repository}/git/ref/heads/{quote(default_branch, safe='')}",
            )
            if seed is not None:
                assert isinstance(seed, dict)
                request_json(
                    session,
                    "POST",
                    f"{API}/repos/{owner}/{repository}/git/refs",
                    expected=(201,),
                    json={
                        "ref": "refs/heads/main",
                        "sha": seed["object"]["sha"],
                    },
                )
                return
        time.sleep(2)
    raise RuntimeError("GitHub repository did not acquire an initial branch.")


def branch_state(
    session: requests.Session,
    owner: str,
    repository: str,
) -> tuple[str | None, str | None, dict[str, str]]:
    ref = get_optional(
        session,
        f"{API}/repos/{owner}/{repository}/git/ref/heads/main",
    )
    if ref is None:
        return None, None, {}
    assert isinstance(ref, dict)
    commit_sha = str(ref["object"]["sha"])
    commit = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/git/commits/{commit_sha}",
    )
    assert isinstance(commit, dict)
    tree_sha = str(commit["tree"]["sha"])
    tree = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/git/trees/{tree_sha}",
        params={"recursive": "1"},
    )
    assert isinstance(tree, dict)
    if tree.get("truncated"):
        raise RuntimeError("Existing GitHub tree response was truncated.")
    files = {
        str(item["path"]): str(item["sha"])
        for item in tree.get("tree", [])
        if item.get("type") == "blob"
    }
    return commit_sha, tree_sha, files


def publish_tree(
    session: requests.Session,
    owner: str,
    repository: str,
    inventory: dict[str, bytes],
    *,
    allow_created_seed: bool,
) -> tuple[str, str]:
    records = inventory_records(inventory)
    expected_tree = {record["path"]: record["git_blob_sha1"] for record in records}
    parent_sha, parent_tree_sha, existing_tree = branch_state(
        session, owner, repository
    )
    if existing_tree == expected_tree and parent_sha and parent_tree_sha:
        return parent_sha, parent_tree_sha
    state = (
        json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if STATE_PATH.is_file()
        else {}
    )
    allowed_prior = {
        str(state.get("baseline_commit_sha") or ""),
        str(state.get("publication_commit_sha") or ""),
    }
    receipt_prior = (
        json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        if RECEIPT_PATH.is_file()
        else {}
    )
    allowed_prior.add(str(receipt_prior.get("commit_sha") or ""))
    if existing_tree and not (
        (allow_created_seed and bool(state.get("created_repository")))
        or (
            bool(state.get("created_repository"))
            and not state.get("publication_commit_sha")
            and (
                not state.get("baseline_commit_sha")
                or parent_sha == state.get("baseline_commit_sha")
            )
        )
        or (parent_sha and parent_sha in allowed_prior)
    ):
        raise RuntimeError(
            "Existing repository head is not bound to this transaction or a prior "
            "verified receipt; refusing to replace its tree."
        )
    if parent_sha and not state.get("baseline_commit_sha"):
        state["baseline_commit_sha"] = parent_sha
        STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    existing_blob_shas = set(existing_tree.values())
    unique_blobs: dict[str, bytes] = {}
    for data in inventory.values():
        unique_blobs.setdefault(git_blob_sha1(data), data)
    for expected_sha, data in sorted(unique_blobs.items()):
        if expected_sha in existing_blob_shas:
            continue
        blob = request_json(
            session,
            "POST",
            f"{API}/repos/{owner}/{repository}/git/blobs",
            expected=(201,),
            json={
                "content": base64.b64encode(data).decode("ascii"),
                "encoding": "base64",
            },
        )
        assert isinstance(blob, dict)
        if blob.get("sha") != expected_sha:
            raise RuntimeError("GitHub blob SHA does not match the local Git object.")

    tree = request_json(
        session,
        "POST",
        f"{API}/repos/{owner}/{repository}/git/trees",
        expected=(201,),
        json={
            "tree": [
                {
                    "path": record["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha": record["git_blob_sha1"],
                }
                for record in records
            ]
        },
    )
    assert isinstance(tree, dict)
    tree_sha = str(tree["sha"])
    commit_payload: dict[str, Any] = {
        "message": (
            "Publish complete Bahasa Indonesia Book 1 edition "
            f"{VERSION}\n\nCodex, acting on the user's request."
        ),
        "tree": tree_sha,
    }
    if parent_sha:
        commit_payload["parents"] = [parent_sha]
    commit = request_json(
        session,
        "POST",
        f"{API}/repos/{owner}/{repository}/git/commits",
        expected=(201,),
        json=commit_payload,
    )
    assert isinstance(commit, dict)
    commit_sha = str(commit["sha"])
    if parent_sha:
        request_json(
            session,
            "PATCH",
            f"{API}/repos/{owner}/{repository}/git/refs/heads/main",
            json={"sha": commit_sha, "force": False},
        )
    else:
        request_json(
            session,
            "POST",
            f"{API}/repos/{owner}/{repository}/git/refs",
            expected=(201,),
            json={"ref": "refs/heads/main", "sha": commit_sha},
        )
    state["publication_commit_sha"] = commit_sha
    state["publication_tree_sha"] = tree_sha
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return commit_sha, tree_sha


def configure_repository(
    session: requests.Session,
    owner: str,
    metadata: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    repository = metadata["repository_name"]
    pages_url = f"https://{owner.lower()}.github.io/{repository}/"
    request_json(
        session,
        "PATCH",
        f"{API}/repos/{owner}/{repository}",
        json={
            "description": metadata["description"],
            "homepage": pages_url,
            "private": False,
            "default_branch": "main",
            "has_issues": metadata["has_issues"],
            "has_projects": metadata["has_projects"],
            "has_wiki": metadata["has_wiki"],
            "has_discussions": metadata["has_discussions"],
        },
    )
    request_json(
        session,
        "PUT",
        f"{API}/repos/{owner}/{repository}/topics",
        json={"names": metadata["topics"]},
    )
    pages_endpoint = f"{API}/repos/{owner}/{repository}/pages"
    pages = get_optional(session, pages_endpoint)
    source = metadata["pages"]["source"]
    if pages is None:
        request_json(
            session,
            "POST",
            pages_endpoint,
            expected=(201,),
            json={"source": source},
        )
    else:
        request_json(
            session,
            "PUT",
            pages_endpoint,
            expected=(204,),
            json={"source": source},
        )
    configured: dict[str, Any] | None = None
    for attempt in range(15):
        observed = get_optional(session, pages_endpoint)
        if isinstance(observed, dict):
            configured = observed
            break
        if attempt < 14:
            time.sleep(2)
    if configured is None:
        raise RuntimeError("GitHub Pages configuration did not become readable.")
    configured_source = configured.get("source", {})
    if (
        configured_source.get("branch") != source["branch"]
        or configured_source.get("path") != source["path"]
    ):
        raise RuntimeError("GitHub Pages source differs from the required main:/docs.")
    return pages_url, configured


def media_type(name: str) -> str:
    known = {
        ".cff": "text/x-cff",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
    }
    return known.get(Path(name).suffix.lower()) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def ensure_release(
    session: requests.Session,
    owner: str,
    repository: str,
    commit_sha: str,
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    tag_ref = get_optional(
        session,
        f"{API}/repos/{owner}/{repository}/git/ref/tags/{quote(TAG, safe='')}",
    )
    if tag_ref is not None:
        assert isinstance(tag_ref, dict)
        if (
            tag_ref.get("object", {}).get("type") != "commit"
            or tag_ref.get("object", {}).get("sha") != commit_sha
        ):
            raise RuntimeError("Existing release tag points to a different object.")
    endpoint = f"{API}/repos/{owner}/{repository}/releases/tags/{quote(TAG, safe='')}"
    release = get_optional(session, endpoint)
    body = (
        "Rilis lengkap Buku 1 edisi Bahasa Indonesia (id-ID), termasuk PDF, "
        "sumber, laboratorium O018 Pyomo+HiGHS, backend modular, hak komponen, "
        "manifest, dan checksum.\n\n"
        "Zenodo DOI: https://doi.org/10.5281/zenodo.22070653\n\n"
        "Terjemahan dan lapisan produksi disiapkan dengan bantuan Codex (AI) "
        "atas permintaan pengguna.\n\nCodex, acting on the user's request."
    )
    if release is None:
        created = request_json(
            session,
            "POST",
            f"{API}/repos/{owner}/{repository}/releases",
            expected=(201,),
            json={
                "tag_name": TAG,
                "target_commitish": commit_sha,
                "name": f"Book 1 Bahasa Indonesia — {VERSION}",
                "body": body,
                "draft": True,
                "prerelease": False,
            },
        )
        assert isinstance(created, dict)
        release = created
    else:
        assert isinstance(release, dict)
        if not bool(release.get("draft")):
            if (
                release.get("name")
                != f"Book 1 Bahasa Indonesia — {VERSION}"
                or str(release.get("body") or "") != body
                or bool(release.get("prerelease"))
            ):
                raise RuntimeError(
                    "Existing public release metadata differs; published releases "
                    "are verification-only."
                )
            remote_assets = {
                str(item["name"]): item for item in release.get("assets", [])
            }
            if set(remote_assets) != {item["name"] for item in assets}:
                raise RuntimeError(
                    "Existing public release has a different asset inventory; "
                    "published releases are verification-only."
                )
            for asset in assets:
                remote = remote_assets[asset["name"]]
                count, observed_hash = download_and_hash(
                    session, str(remote["browser_download_url"])
                )
                if count != asset["bytes"] or observed_hash != asset["sha256"]:
                    raise RuntimeError(
                        f"Existing public release asset differs: {asset['name']}"
                    )
            return release
        updated = request_json(
            session,
            "PATCH",
            f"{API}/repos/{owner}/{repository}/releases/{release['id']}",
            json={
                "tag_name": TAG,
                "target_commitish": commit_sha,
                "name": f"Book 1 Bahasa Indonesia — {VERSION}",
                "body": body,
                "draft": True,
                "prerelease": False,
            },
        )
        assert isinstance(updated, dict)
        release = updated

    remote_assets = {str(item["name"]): item for item in release.get("assets", [])}
    for asset in assets:
        remote = remote_assets.get(asset["name"])
        digest = str(remote.get("digest", "")) if remote else ""
        if remote and int(remote.get("size", 0)) == asset["bytes"]:
            if digest == f"sha256:{asset['sha256']}":
                continue
            count, observed_hash = download_and_hash(
                session, str(remote["browser_download_url"])
            )
            if count == asset["bytes"] and observed_hash == asset["sha256"]:
                continue
        if remote:
            request_json(
                session,
                "DELETE",
                f"{API}/repos/{owner}/{repository}/releases/assets/{remote['id']}",
                expected=(204,),
            )
        upload_url = str(release["upload_url"]).split("{", 1)[0]
        with asset["path"].open("rb") as stream:
            response = session.post(
                upload_url,
                params={"name": asset["name"]},
                headers={"Content-Type": media_type(asset["name"])},
                data=stream,
                timeout=REQUEST_TIMEOUT,
            )
        if response.status_code != 201:
            raise RuntimeError(
                f"GitHub release upload for {asset['name']} returned "
                f"HTTP {response.status_code}: {response.text[:500]}"
            )
    refreshed = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/releases/{release['id']}",
    )
    assert isinstance(refreshed, dict)
    names = {str(item["name"]) for item in refreshed.get("assets", [])}
    expected_names = {item["name"] for item in assets}
    if names != expected_names:
        raise RuntimeError(
            "GitHub release asset inventory mismatch: "
            f"expected={sorted(expected_names)}, observed={sorted(names)}"
        )
    published = request_json(
        session,
        "PATCH",
        f"{API}/repos/{owner}/{repository}/releases/{release['id']}",
        json={
            "tag_name": TAG,
            "target_commitish": commit_sha,
            "name": f"Book 1 Bahasa Indonesia — {VERSION}",
            "body": body,
            "draft": False,
            "prerelease": False,
            "make_latest": "true",
        },
    )
    assert isinstance(published, dict)
    return published


def download_and_hash(
    session: requests.Session, url: str
) -> tuple[int, str]:
    response = session.get(url, stream=True, timeout=REQUEST_TIMEOUT)
    if response.status_code != 200:
        raise RuntimeError(
            f"Anonymous download {urlparse(url).path} returned "
            f"HTTP {response.status_code}."
        )
    hasher = hashlib.sha256()
    count = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if chunk:
            hasher.update(chunk)
            count += len(chunk)
    return count, hasher.hexdigest()


def verify_public(
    owner: str,
    repository: str,
    commit_sha: str,
    tree_sha: str,
    inventory: dict[str, bytes],
    assets: list[dict[str, Any]],
    pages_url: str,
    pages_config: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "interlanguage-r017-o018-public-readback/1.0",
        }
    )
    repo = request_json(session, "GET", f"{API}/repos/{owner}/{repository}")
    assert isinstance(repo, dict)
    expected_homepage = metadata["homepage_template"].format(
        owner=owner.lower()
    )
    if (
        bool(repo.get("private"))
        or repo.get("default_branch") != metadata["default_branch"]
        or repo.get("description") != metadata["description"]
        or str(repo.get("homepage", "")).rstrip("/") != expected_homepage.rstrip("/")
        or bool(repo.get("has_issues")) != bool(metadata["has_issues"])
        or bool(repo.get("has_projects")) != bool(metadata["has_projects"])
        or bool(repo.get("has_wiki")) != bool(metadata["has_wiki"])
        or bool(repo.get("has_discussions")) != bool(metadata["has_discussions"])
    ):
        raise RuntimeError("Public repository metadata is not in the required state.")
    topics = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/topics",
    )
    assert isinstance(topics, dict)
    if sorted(topics.get("names", [])) != sorted(metadata["topics"]):
        raise RuntimeError("Public repository topics differ from the release metadata.")
    main_ref = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/git/ref/heads/main",
    )
    assert isinstance(main_ref, dict)
    if main_ref.get("object", {}).get("sha") != commit_sha:
        raise RuntimeError("Public main branch does not point to the release commit.")
    public_commit = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/git/commits/{commit_sha}",
    )
    assert isinstance(public_commit, dict)
    if public_commit.get("tree", {}).get("sha") != tree_sha:
        raise RuntimeError("Public release commit does not point to the release tree.")

    tree = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/git/trees/{tree_sha}",
        params={"recursive": "1"},
    )
    assert isinstance(tree, dict)
    if tree.get("truncated"):
        raise RuntimeError("Public GitHub tree response was truncated.")
    observed_tree = {
        str(item["path"]): str(item["sha"])
        for item in tree.get("tree", [])
        if item.get("type") == "blob"
    }
    expected_tree = {
        path: git_blob_sha1(data) for path, data in inventory.items()
    }
    if observed_tree != expected_tree:
        raise RuntimeError("Public GitHub tree differs from the exact local inventory.")

    repository_readback: list[dict[str, Any]] = []
    for path, data in inventory.items():
        encoded_path = "/".join(quote(part, safe="") for part in PurePosixPath(path).parts)
        raw_url = (
            f"https://raw.githubusercontent.com/{owner}/{repository}/"
            f"{commit_sha}/{encoded_path}"
        )
        count, observed_hash = download_and_hash(session, raw_url)
        expected_hash = sha256_bytes(data)
        if count != len(data) or observed_hash != expected_hash:
            raise RuntimeError(f"Public repository byte mismatch: {path}")
        repository_readback.append(
            {
                "path": path,
                "bytes": count,
                "sha256": observed_hash,
                "url": raw_url,
            }
        )

    release = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/releases/tags/{quote(TAG, safe='')}",
    )
    assert isinstance(release, dict)
    tag_ref = request_json(
        session,
        "GET",
        f"{API}/repos/{owner}/{repository}/git/ref/tags/{quote(TAG, safe='')}",
    )
    assert isinstance(tag_ref, dict)
    if (
        tag_ref.get("object", {}).get("type") != "commit"
        or tag_ref.get("object", {}).get("sha") != commit_sha
        or bool(release.get("draft"))
        or bool(release.get("prerelease"))
    ):
        raise RuntimeError("Public release/tag state differs from the frozen commit.")
    remote_assets = {str(item["name"]): item for item in release.get("assets", [])}
    if set(remote_assets) != {item["name"] for item in assets}:
        raise RuntimeError("Public release has missing or extra assets.")
    release_readback: list[dict[str, Any]] = []
    for local in assets:
        remote = remote_assets.get(local["name"])
        if remote is None:
            raise RuntimeError(f"Public release asset missing: {local['name']}")
        count, observed_hash = download_and_hash(
            session, str(remote["browser_download_url"])
        )
        if count != local["bytes"] or observed_hash != local["sha256"]:
            raise RuntimeError(f"Public release asset mismatch: {local['name']}")
        release_readback.append(
            {
                "name": local["name"],
                "bytes": count,
                "sha256": observed_hash,
                "url": remote["browser_download_url"],
            }
        )

    html_bytes = b""
    expected_html = inventory["docs/index.html"]
    for attempt in range(60):
        response = session.get(pages_url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            html_bytes = response.content
            if html_bytes == expected_html:
                break
        if attempt < 59:
            time.sleep(5)
    if html_bytes != expected_html:
        raise RuntimeError("GitHub Pages HTML differs from the committed id-ID reader.")

    css_data = inventory["docs/assets/site.css"]
    css_url = f"{pages_url.rstrip('/')}/assets/site.css"
    css_count, css_hash = download_and_hash(session, css_url)
    if css_count != len(css_data) or css_hash != sha256_bytes(css_data):
        raise RuntimeError("GitHub Pages CSS differs from the committed reader.")

    pages_readback: list[dict[str, Any]] = []
    for local in assets:
        url = f"{pages_url.rstrip('/')}/downloads/{quote(local['name'], safe='')}"
        count, observed_hash = download_and_hash(session, url)
        if count != local["bytes"] or observed_hash != local["sha256"]:
            raise RuntimeError(f"GitHub Pages download mismatch: {local['name']}")
        pages_readback.append(
            {
                "name": local["name"],
                "bytes": count,
                "sha256": observed_hash,
                "url": url,
            }
        )
    session.close()
    return {
        "repository_url": str(repo["html_url"]),
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "repository_file_count": len(expected_tree),
        "repository_tree_exact": True,
        "repository_files": repository_readback,
        "release_url": str(release["html_url"]),
        "release_assets": release_readback,
        "pages_url": pages_url,
        "pages_html_id_id": True,
        "pages_html": {
            "bytes": len(html_bytes),
            "sha256": sha256_bytes(html_bytes),
            "url": pages_url,
        },
        "pages_source": pages_config.get("source"),
        "pages_build_type": pages_config.get("build_type"),
        "pages_css": {
            "bytes": css_count,
            "sha256": css_hash,
            "url": css_url,
        },
        "pages_downloads": pages_readback,
    }


def write_state(owner: str, repository: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    prior: dict[str, Any] = {}
    if STATE_PATH.is_file():
        parsed = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if (
            parsed.get("owner") == owner
            and parsed.get("repository") == repository
            and not parsed.get("credential_material")
        ):
            prior = parsed
    prior.update(
        {
            "schema": "github-publication-state-v1",
            "owner": owner,
            "repository": repository,
            "credential_material": False,
        }
    )
    STATE_PATH.write_text(
        json.dumps(prior, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def publish(token_file: Path, expected_owner: str) -> dict[str, Any]:
    inventory, plan = build_plan(expected_owner, write=False)
    if not PLAN_PATH.is_file():
        raise RuntimeError("Reviewed GitHub publication plan is missing; run --plan-only.")
    reviewed_plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if (
        reviewed_plan.get("expected_owner") != expected_owner
        or reviewed_plan.get("repository_name") != plan["repository_name"]
        or reviewed_plan.get("repository_inventory", {}).get("aggregate_sha256")
        != plan["repository_inventory"]["aggregate_sha256"]
        or reviewed_plan.get("repository_inventory", {}).get("files")
        != plan["repository_inventory"]["files"]
        or reviewed_plan.get("release_assets") != plan["release_assets"]
    ):
        raise RuntimeError(
            "Live publication bytes differ from the reviewed GitHub plan; "
            "rerun --plan-only and review the new aggregate before publishing."
        )
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    if str(metadata.get("owner", "")).casefold() != expected_owner.casefold():
        raise RuntimeError("Expected owner differs from pinned GitHub metadata.")
    if metadata.get("visibility") != "public":
        raise RuntimeError("GitHub metadata does not require public visibility.")
    if metadata.get("release_assets") != list(RELEASE_ASSET_ORDER):
        raise RuntimeError("GitHub metadata release-asset inventory drift.")
    assets = exact_release_assets()
    session, user = authenticated_session(token_file, expected_owner)
    owner = str(user["login"])
    repository = str(metadata["repository_name"])
    write_state(owner, repository)
    repo, created_now = ensure_repository(session, owner, metadata)
    if created_now:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        state["created_repository"] = True
        STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    ensure_main_seed(session, owner, repository, repo)
    commit_sha, tree_sha = publish_tree(
        session,
        owner,
        repository,
        inventory,
        allow_created_seed=created_now,
    )
    pages_url, pages_config = configure_repository(session, owner, metadata)
    ensure_release(session, owner, repository, commit_sha, assets)
    session.close()

    public = verify_public(
        owner,
        repository,
        commit_sha,
        tree_sha,
        inventory,
        assets,
        pages_url,
        pages_config,
        metadata,
    )
    receipt = {
        "schema": "github-publication-receipt-v1",
        "status": "published_and_anonymously_verified",
        "verified_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "owner": owner,
        "repository": repository,
        "version": VERSION,
        "tag": TAG,
        "inventory_aggregate_sha256": plan["repository_inventory"]["aggregate_sha256"],
        **public,
        "checks": {
            "public_repository": True,
            "exact_repository_tree": True,
            "exact_release_asset_inventory": True,
            "all_release_asset_bytes_match": True,
            "pages_id_id": True,
            "all_pages_download_bytes_match": True,
            "credential_in_url": False,
            "credential_material_persisted": False,
            "git_invoked": False,
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
        "repository_url": receipt["repository_url"],
        "release_url": receipt["release_url"],
        "pages_url": receipt["pages_url"],
        "commit_sha": commit_sha,
        "file_count": receipt["repository_file_count"],
        "release_asset_count": len(receipt["release_assets"]),
        "receipt": RECEIPT_PATH.relative_to(LANE).as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-owner", default="KokunoYumeto")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.plan_only:
        _, plan = build_plan(args.expected_owner)
        print(
            json.dumps(
                {
                    "status": plan["status"],
                    "repository": (
                        f"{plan['expected_owner']}/{plan['repository_name']}"
                    ),
                    "file_count": plan["repository_inventory"]["file_count"],
                    "checkout_bytes": plan["repository_inventory"]["checkout_bytes"],
                    "unique_blob_count": plan["repository_inventory"]["unique_blob_count"],
                    "aggregate_sha256": plan["repository_inventory"]["aggregate_sha256"],
                    "release_asset_count": len(plan["release_assets"]),
                    "plan": PLAN_PATH.relative_to(LANE).as_posix(),
                    "network_access": False,
                    "git_invoked": False,
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.token_file is None:
        parser.error("--token-file is required unless --plan-only is used")
    summary = publish(args.token_file.resolve(), args.expected_owner)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
