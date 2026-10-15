"""Build reproducible, source-pinned Figure packages and signed feed catalogs.

The package-manifest fields intentionally match the independent Superbench
consumer contract (tool-package.v1). This module does not import Superbench.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
from typing import Mapping
import uuid
import zipfile
from io import BytesIO

try:
    from . import scientific_product_release
except ImportError:  # Direct script invocation from an archived source tree.
    import scientific_product_release

TOOL_ID = "figure-studio"
CANONICAL_PACKAGE_NAME = "@superbench/figure-tool"
LEGACY_PACKAGE_IDENTITIES = {("@bsd-studio/figure-studio", "1.0.0-beta.3")}
HOST_API = "v1"
PACKAGE_KIND = "static-v1"
PACKAGE_SCHEMA = "superbench.toolPackage.v1"
CATALOG_SCHEMA = "superbench.toolReleaseCatalog.v2"
CATALOG_ID = "figure-studio-release-feed"
CATALOG_KEY_ID = "superbench-figure-release-2026"
TRUSTED_CATALOG_PUBLIC_KEY = bytes.fromhex(
    "f147ec9aa2730a8dc5917c4a965b4e327ca243fcdc9559c17ad922ceb05e6964"
)
HOST_API_CAPABILITIES = ["workspace-project-serializer.v1", "figure-present-bridge.v1"]
OPTIONAL_NATIVE_SERVICES = ["pdf-native-ir-shadow", "pdf-native-compile"]
PAYLOAD_ROOTS = ("app", "vendor", "assets/scientific-packs", "assets/scientific-scenes", "web")
SCENE_ROOT = "assets/scientific-scenes"
PACK_ROOT = "assets/scientific-packs"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FULL_REVISION = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MAX_PREVIOUS_CATALOG_BYTES = 4 * 1024 * 1024
MAX_PREVIOUS_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_CATALOG_RELEASES = 500
WINDOWS_RESERVED = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


class ReleaseBuildError(ValueError):
    """A committed source or candidate failed a release contract."""


def _product_release(source_root: Path) -> dict | None:
    try:
        return scientific_product_release.validate(source_root)
    except (ValueError, KeyError, OSError) as error:
        raise ReleaseBuildError(str(error)) from error


@dataclass(frozen=True)
class BuiltRelease:
    version: str
    source_revision: str
    package_sha256: str
    archive_sha256: str
    web_archive_sha256: str
    package_zip: Path
    web_zip: Path
    receipt_path: Path
    rights_receipt_path: Path
    inventory_path: Path
    distribution_scope: str = "private-review"
    synthetic_version_identity: bool = False
    public_release_eligible: bool = False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ReleaseBuildError(f"Duplicate JSON key in {label}: {key}")
            value[key] = item
        return value

    try:
        result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseBuildError(f"Invalid {label}") from error
    if not isinstance(result, dict):
        raise ReleaseBuildError(f"{label} must be a JSON object")
    return result


def _validate_relative_path(value: str) -> tuple[str, ...]:
    path = PurePosixPath(value)
    parts = value.split("/")
    if not value or "\\" in value or path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise ReleaseBuildError(f"Unsafe package-relative path: {value!r}")
    for part in parts:
        if (
            any(ord(char) < 32 for char in part)
            or any(char in '<>:"|?*' for char in part)
            or part.endswith((".", " "))
            or WINDOWS_RESERVED.match(part)
        ):
            raise ReleaseBuildError(f"Package path is not portable to Windows: {value!r}")
    return tuple(parts)


def _git(repository: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *args], check=True, capture_output=True
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ReleaseBuildError("Git could not resolve the requested Figure commit") from error
    return result.stdout


def resolve_commit(repository: Path, revision: str = "HEAD") -> str:
    repository = Path(repository).resolve()
    if not repository.is_dir():
        raise ReleaseBuildError("Figure repository is unavailable")
    commit = _git(repository, "rev-parse", "--verify", f"{revision}^{{commit}}").decode("ascii").strip()
    if not FULL_REVISION.fullmatch(commit):
        raise ReleaseBuildError("Figure source revision must resolve to a full lowercase Git commit")
    return commit


def extract_git_archive(repository: Path, commit: str, destination: Path) -> Path:
    if not FULL_REVISION.fullmatch(commit):
        raise ReleaseBuildError("A full Git commit is required for source extraction")
    archive = _git(repository, "archive", "--format=tar", commit)
    destination.mkdir(parents=True, exist_ok=False)
    folded: dict[str, str] = {}
    try:
        stream = tarfile.open(fileobj=__import__("io").BytesIO(archive), mode="r:")
        with stream:
            members = stream.getmembers()
            for member in members:
                parts = _validate_relative_path(member.name.rstrip("/"))
                canonical = "/".join(parts)
                key = canonical.casefold()
                if key in folded:
                    raise ReleaseBuildError(f"Duplicate or case-colliding archive path: {canonical}")
                folded[key] = canonical
                if not (member.isfile() or member.isdir()):
                    raise ReleaseBuildError(f"Git archive contains a link or special entry: {canonical}")
                target = destination.joinpath(*parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = stream.extractfile(member)
                    if source is None:
                        raise ReleaseBuildError(f"Unreadable Git archive entry: {canonical}")
                    with source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
    except tarfile.TarError as error:
        raise ReleaseBuildError("Git produced an invalid source archive") from error
    return destination


def _inventory(root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    folded: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ReleaseBuildError(f"Links are forbidden in release payloads: {path.name}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ReleaseBuildError("Unsupported non-file entry in release payload")
        relative = path.relative_to(root).as_posix()
        _validate_relative_path(relative)
        folded_path = relative.casefold()
        if folded_path in folded and folded[folded_path] != relative:
            raise ReleaseBuildError(f"Windows case-colliding payload path: {relative}")
        folded[folded_path] = relative
        data = path.read_bytes()
        entries.append({"path": relative, "size": len(data), "sha256": sha256_bytes(data)})
    return sorted(entries, key=lambda row: str(row["path"]).casefold())


def _tree_digest(files: list[dict[str, object]]) -> str:
    basis = "".join(f"{row['path']}\0{row['sha256']}\n" for row in files).encode("utf-8")
    return sha256_bytes(basis)


def _package_digest(manifest: Mapping[str, object]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "package_sha256"}
    return sha256_bytes(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def build_tool_package(
    source_root: Path,
    output_dir: Path,
    *,
    source_revision: str,
    version_override: str | None = None,
    distribution_scope: str = "private-review",
    public_release_eligible: bool = False,
) -> dict[str, object]:
    """Build the exact Superbench host package contract from an archived source root."""
    source_root = Path(source_root).resolve()
    output_dir = Path(output_dir).absolute()
    if output_dir.exists():
        raise ReleaseBuildError("Package output already exists")
    if output_dir == source_root or source_root in output_dir.parents or output_dir in source_root.parents:
        raise ReleaseBuildError("Package output cannot overlap the source tree")
    if not FULL_REVISION.fullmatch(source_revision):
        raise ReleaseBuildError("source_revision must be a full Git commit")
    if distribution_scope not in {"private-review", "public-release"}:
        raise ReleaseBuildError("Unsupported distribution scope")
    if version_override is not None and distribution_scope != "private-review":
        raise ReleaseBuildError("QA version overrides are allowed only for private-review builds")
    if distribution_scope == "public-release" and not public_release_eligible:
        raise ReleaseBuildError("Public package creation requires passing public rights gates")
    metadata = _read_json(source_root / "package.json", "package metadata")
    if metadata.get("license") == "Apache-2.0":
        for relative in ("LICENSE", "NOTICE", "LICENSE_POLICY.md",
                         "assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md", "assets/CC0-1.0.txt"):
            canonical = source_root / relative
            bundled = source_root / "app/legal" / relative
            if not canonical.is_file() or not bundled.is_file() or canonical.read_bytes() != bundled.read_bytes():
                raise ReleaseBuildError(f"Apache Figure package must carry matching first-party terms: {relative}")
    source_version = str(metadata.get("version") or "")
    version = version_override or source_version
    package_identity = (metadata.get("name"), source_version)
    if (metadata.get("name") != CANONICAL_PACKAGE_NAME and package_identity not in LEGACY_PACKAGE_IDENTITIES) or not SEMVER.fullmatch(source_version) or not SEMVER.fullmatch(version):
        raise ReleaseBuildError("Figure package identity or version is invalid")
    payload = output_dir / "payload"
    payload.mkdir(parents=True)
    try:
        for relative in PAYLOAD_ROOTS:
            source = source_root.joinpath(*relative.split("/"))
            if not source.is_dir():
                raise ReleaseBuildError(f"Required payload root is missing: {relative}")
            if any(path.is_symlink() or getattr(path, "is_junction", lambda: False)() for path in source.rglob("*")):
                raise ReleaseBuildError(f"Links are forbidden under payload root: {relative}")
            shutil.copytree(source, payload.joinpath(*relative.split("/")), symlinks=False)
        files = _inventory(payload)
        allowed_roots = {"app", "vendor", "assets", "web"}
        if {path.name for path in payload.iterdir()} != allowed_roots:
            raise ReleaseBuildError("Payload has missing or extra top-level roots")
        assets = payload / "assets"
        if {path.name for path in assets.iterdir()} != {"scientific-packs", "scientific-scenes"}:
            raise ReleaseBuildError("Payload has missing or extra scientific asset roots")
        if not any(row["path"] == "app/index.html" for row in files):
            raise ReleaseBuildError("Figure entry point is missing")
        if not any(row["path"] == "web/index.html" for row in files):
            raise ReleaseBuildError("Static web editor entry point is missing")
        manifest: dict[str, object] = {
            "schema": PACKAGE_SCHEMA,
            "tool_id": TOOL_ID,
            "version": version,
            "package_kind": PACKAGE_KIND,
            "host_api": HOST_API,
            "host_api_capabilities": list(HOST_API_CAPABILITIES),
            "required_native_services": [],
            "optional_native_services": list(OPTIONAL_NATIVE_SERVICES),
            "entry_point": "app/index.html",
            "payload_roots": list(PAYLOAD_ROOTS),
            "payload_files": files,
            "tree_sha256": _tree_digest(files),
            "source_provenance": {
                "source_revision": source_revision.lower(),
                "source_version": source_version,
                "revision_assertion": "caller-supplied; not independently authenticated",
                "synthetic_version_identity": version_override is not None,
                "distribution_scope": distribution_scope,
                "public_release_eligible": public_release_eligible,
            },
        }
        manifest["package_sha256"] = _package_digest(manifest)
        (output_dir / "tool-package.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        verify_tool_package(output_dir, trusted_package_sha256=str(manifest["package_sha256"]))
        return manifest
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def verify_tool_package(package_root: Path, *, trusted_package_sha256: str) -> dict[str, object]:
    """Independent local parity verifier for the host's semantic package identity."""
    root = Path(package_root).resolve()
    if {path.name for path in root.iterdir()} != {"tool-package.json", "payload"}:
        raise ReleaseBuildError("Package has missing or unlisted top-level files")
    manifest = _read_json(root / "tool-package.json", "tool package manifest")
    if (
        manifest.get("schema") != PACKAGE_SCHEMA
        or manifest.get("tool_id") != TOOL_ID
        or manifest.get("package_kind") != PACKAGE_KIND
        or manifest.get("host_api") != HOST_API
        or manifest.get("host_api_capabilities") != HOST_API_CAPABILITIES
        or manifest.get("required_native_services") != []
        or manifest.get("optional_native_services") != OPTIONAL_NATIVE_SERVICES
        or manifest.get("payload_roots") != list(PAYLOAD_ROOTS)
        or manifest.get("entry_point") != "app/index.html"
    ):
        raise ReleaseBuildError("Package metadata is incompatible with the Figure host")
    payload = root / "payload"
    actual = _inventory(payload)
    if actual != manifest.get("payload_files") or _tree_digest(actual) != manifest.get("tree_sha256"):
        raise ReleaseBuildError("Package payload differs from its signed semantic inventory")
    digest = _package_digest(manifest)
    if manifest.get("package_sha256") != digest or digest != trusted_package_sha256:
        raise ReleaseBuildError("Package does not match its semantic package digest")
    return manifest


def _write_deterministic_zip(root: Path, output: Path, *, package: bool) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ReleaseBuildError("Immutable ZIP output already exists")
    files = [root / "tool-package.json"] if package else []
    payload = root / "payload"
    files.extend(sorted(payload.rglob("*"), key=lambda item: item.relative_to(root).as_posix().casefold()))
    files = [path for path in files if path.is_file()]
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_STORED, strict_timestamps=True) as bundle:
        for path in files:
            relative = path.relative_to(root).as_posix()
            if not package:
                relative = path.relative_to(payload).as_posix()
            _validate_relative_path(relative)
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits = 0
            bundle.writestr(info, path.read_bytes())
    return sha256_bytes(output.read_bytes())


def _source_inventory(source_root: Path) -> list[dict[str, object]]:
    return _prefixed_inventory(source_root, PAYLOAD_ROOTS)


def _prefixed_inventory(source_root: Path, roots: tuple[str, ...]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for relative in roots:
        root = source_root / relative
        for row in _inventory(root):
            entries.append({**row, "path": f"{relative}/{row['path']}"})
    return sorted(entries, key=lambda row: str(row["path"]).casefold())


def validate_scene_release(scene_root: Path, *, distribution_scope: str) -> dict[str, object]:
    """Validate all currently catalogued scenes and report their actual rights state."""
    library = _read_json(scene_root / "library.v1.json", "scientific scene library")
    rights = _read_json(scene_root / "release-rights.v1.json", "scientific scene rights")
    if (
        library.get("schema") != "figureStudio.scientificSceneLibrary.v1"
        or library.get("id") != "figure-studio-scientific-scenes"
        or rights.get("schema") != "figureStudio.scientificSceneRights.v1"
    ):
        raise ReleaseBuildError("Scientific scene registry identity is invalid")
    scenes, releases = library.get("scenes"), rights.get("scenes")
    sources, rights_rows = rights.get("source_records"), rights.get("rights_records")
    if not all(isinstance(value, list) for value in (scenes, releases, sources, rights_rows)):
        raise ReleaseBuildError("Scientific scene registries must be arrays")

    def unique_index(rows: list[object], field: str, label: str) -> dict[str, dict[str, object]]:
        indexed: dict[str, dict[str, object]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ReleaseBuildError(f"{label} contains a malformed row")
            key = str(row.get(field) or "")
            if not key or key in indexed:
                raise ReleaseBuildError(f"{label} contains a missing or duplicate ID")
            indexed[key] = row
        return indexed

    by_id = unique_index(scenes, "id", "Scientific scene library")
    release_by_id = unique_index(releases, "scene_id", "Scientific scene release registry")
    source_by_id = unique_index(sources, "id", "Scientific scene source registry")
    rights_by_id = unique_index(rights_rows, "id", "Scientific scene rights registry")
    if not by_id or set(by_id) != set(release_by_id):
        raise ReleaseBuildError("Scientific scene release IDs must exactly match the library")
    if (
        rights.get("status") != "released"
        or rights.get("selected_public_license") != "CC0-1.0"
        or rights.get("license_notice") != "LICENSE-SCENES-CC0-1.0.md"
        or not (scene_root / "LICENSE-SCENES-CC0-1.0.md").is_file()
    ):
        raise ReleaseBuildError("Scientific scene root rights/CC0 notice are invalid")

    pending: list[str] = []
    for scene_id, scene in by_id.items():
        expected_scene = f"scenes/{scene_id}.scene.json"
        expected_preview = f"previews/{scene_id}.svg"
        if scene.get("scene") != expected_scene or scene.get("preview") != expected_preview:
            raise ReleaseBuildError(f"Scientific scene paths are unsafe or noncanonical: {scene_id}")
        source_id, rights_id = str(scene.get("source_record_id") or ""), str(scene.get("rights_record_id") or "")
        source_record, rights_record = source_by_id.get(source_id), rights_by_id.get(rights_id)
        if source_record is None or rights_record is None:
            raise ReleaseBuildError(f"Scientific scene source or rights record is missing: {scene_id}")
        if (
            not isinstance(source_record.get("creator"), str)
            or not source_record.get("creator")
            or source_record.get("source_type") != "clean_room_original_editable_vector_scene"
            or source_record.get("third_party_material") != "none_declared"
        ):
            raise ReleaseBuildError(f"Scientific scene source record is incomplete: {scene_id}")
        scene_path = scene_root / expected_scene
        preview_path = scene_root / expected_preview
        if not scene_path.is_file() or not preview_path.is_file():
            raise ReleaseBuildError(f"Scientific scene content is missing: {scene_id}")
        definition = _read_json(scene_path, f"scene definition {scene_id}")
        if (
            definition.get("schema") != "figureStudio.scientificScene.v1"
            or definition.get("id") != scene_id
            or definition.get("name") != scene.get("name")
            or definition.get("summary") != scene.get("summary")
            or definition.get("source_record_id") != source_id
            or definition.get("rights_record_id") != rights_id
            or not isinstance(definition.get("layers"), list)
            or not definition.get("layers")
            or not isinstance(definition.get("nodes"), list)
            or not definition.get("nodes")
        ):
            raise ReleaseBuildError(f"Scientific scene definition is incomplete: {scene_id}")
        preview = preview_path.read_bytes()
        if b"<script" in preview.lower() or b"<foreignobject" in preview.lower() or b"<image" in preview.lower():
            raise ReleaseBuildError(f"Scientific scene preview contains active or embedded content: {scene_id}")
        catalog = release_by_id[scene_id]
        for key, expected in {
            "name": scene.get("name"),
            "scene_file": expected_scene,
            "preview_file": expected_preview,
            "source_record_id": source_id,
            "rights_record_id": rights_id,
            "scene_sha256": sha256_bytes(scene_path.read_bytes()),
            "preview_sha256": sha256_bytes(preview),
        }.items():
            if catalog.get(key) != expected:
                raise ReleaseBuildError(f"Scientific scene receipt mismatch for {scene_id}: {key}")
        approved = (
            rights_record.get("license") == "CC0-1.0"
            and rights_record.get("rights_basis") == "owner_attested_original_output"
            and rights_record.get("status") == "released"
            and rights_record.get("public_distribution_authorized") is True
            and catalog.get("release_disposition") == "released_under_cc0_1_0"
        )
        if not approved:
            pending.append(scene_id)
            disposition = catalog.get("release_disposition")
            if disposition == "licensed_under_cc0_1_0_product_release_pending":
                if (rights_record.get("license") != "CC0-1.0"
                        or rights_record.get("public_distribution_authorized") is not True
                        or rights_record.get("product_release_status") != "pending_quality_and_product_review"):
                    raise ReleaseBuildError(f"Rights-cleared draft lacks its permission/product-review evidence: {scene_id}")
            elif disposition != "draft_not_authorized_for_public_distribution":
                raise ReleaseBuildError(f"Unapproved scene is not labelled as a private-review draft: {scene_id}")
    expected_files = {
        "library.v1.json", "release-rights.v1.json", "LICENSE-SCENES-CC0-1.0.md",
        *(str(row["scene"]) for row in scenes), *(str(row["preview"]) for row in scenes),
    }
    actual_files = {path.relative_to(scene_root).as_posix() for path in scene_root.rglob("*") if path.is_file()}
    if actual_files != expected_files:
        raise ReleaseBuildError("Scientific scene payload contains missing or unregistered files")
    approval = _product_release(scene_root.parents[1])
    historical_pending = sorted(pending)
    if approval:
        pending = [scene_id for scene_id in pending if scene_id not in approval["scenes"]]
    if distribution_scope == "public-release" and pending:
        raise ReleaseBuildError("Public distribution is pending scene product release approval: " + ", ".join(sorted(pending)))
    return {
        "scene_count": len(by_id),
        "source_record_count": len(source_by_id),
        "rights_record_count": len(rights_by_id),
        "public_distribution_authorized": not pending and rights.get("public_distribution_authorized") is True,
        "pending_scene_ids": sorted(pending),
        "historical_pending_scene_ids": historical_pending,
        "product_release_record": scientific_product_release.RECORD if approval else None,
        "rights_sha256": sha256_bytes((scene_root / "release-rights.v1.json").read_bytes()),
        "status": "released" if not pending else "private_review_only",
    }


def validate_release_source(source_root: Path, *, distribution_scope: str) -> dict[str, object]:
    if distribution_scope not in {"private-review", "public-release"}:
        raise ReleaseBuildError("Unsupported distribution scope")
    asset_command = [
        os.environ.get("PYTHON", "python"), str(source_root / "scripts/validate-scientific-assets.py"),
        "--library",
    ]
    if distribution_scope == "public-release":
        asset_command.append("--require-public-release")
    try:
        assets = subprocess.run(
            asset_command, cwd=source_root, check=True, capture_output=True, text=True, encoding="utf-8"
        ).stdout.strip()
        vendor = subprocess.run(
            [os.environ.get("PYTHON", "python"), str(source_root / "scripts/validate-vendor-bundle.py")],
            cwd=source_root, check=True, capture_output=True, text=True, encoding="utf-8"
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        output = getattr(error, "stderr", "") or ""
        safe_output = output.strip()[-1200:]
        raise ReleaseBuildError(f"Figure source validation failed: {safe_output or type(error).__name__}") from error
    approval = _product_release(source_root)
    scenes = validate_scene_release(source_root / SCENE_ROOT, distribution_scope=distribution_scope)
    library = _read_json(source_root / PACK_ROOT / "library.json", "scientific pack registry")
    pending_packs = []
    pack_receipts = []
    for row in library.get("packs", []):
        if not isinstance(row, dict):
            raise ReleaseBuildError("Scientific pack registry contains a malformed pack")
        pack_path = source_root / PACK_ROOT / str(row.get("path") or "")
        catalog = _read_json(pack_path, f"scientific pack {row.get('id')}")
        release = catalog.get("release_audit") or {}
        status = str(release.get("status") or "")
        authorized = release.get("public_distribution_authorized") is True
        effective_status = "released" if approval and str(row.get("id")) in approval["packs"] else status
        if effective_status != "released" or not authorized:
            pending_packs.append(str(row.get("id") or ""))
        pack_receipts.append({
            "pack_id": str(row.get("id") or ""),
            "path": str(row.get("path") or ""),
            "status": status,
            "effective_product_release_status": effective_status,
            "public_distribution_authorized": authorized,
            "license": str(release.get("selected_public_license") or ""),
            "catalog_sha256": sha256_bytes(pack_path.read_bytes()),
        })
    if distribution_scope == "public-release" and pending_packs:
        raise ReleaseBuildError("Public release is pending pack rights approval: " + ", ".join(sorted(pending_packs)))
    return {
        "scope": distribution_scope,
        "asset_validator": assets,
        "vendor_validator": vendor,
        "packs": pack_receipts,
        "pending_pack_ids": sorted(pending_packs),
        "product_release_record": scientific_product_release.RECORD if approval else None,
        "product_release_record_sha256": scientific_product_release.canonical(approval) if approval else None,
        "scenes": scenes,
        "public_release_eligible": not pending_packs and not scenes["pending_scene_ids"],
    }


def _rights_receipt(source_root: Path, validation: Mapping[str, object], *, scope: str) -> dict[str, object]:
    library_path = source_root / PACK_ROOT / "library.json"
    scene_rights_path = source_root / SCENE_ROOT / "release-rights.v1.json"
    vendor_manifest_path = source_root / "vendor/manifest.json"
    return {
        "schema": "figureStudio.releaseRightsReceipt.v1",
        "distribution_scope": scope,
        "public_distribution_authorized": scope == "public-release" and validation.get("public_release_eligible") is True,
        "public_release_eligible": validation.get("public_release_eligible") is True,
        "pending_pack_ids": validation.get("pending_pack_ids"),
        "pending_scene_ids": validation.get("scenes", {}).get("pending_scene_ids"),
        "scientific_packs": validation.get("packs"),
        "scientific_scenes": validation.get("scenes"),
        "product_release_record": validation.get("product_release_record"),
        "product_release_record_sha256": validation.get("product_release_record_sha256"),
        "source_digests": {
            "pack_registry_sha256": sha256_bytes(library_path.read_bytes()),
            "scene_rights_sha256": sha256_bytes(scene_rights_path.read_bytes()),
            "vendor_manifest_sha256": sha256_bytes(vendor_manifest_path.read_bytes()),
        },
    }


def verify_archive_payload_parity(package_zip: Path, web_zip: Path) -> dict[str, object]:
    """Read both emitted archives and prove every shared payload byte is identical."""
    with zipfile.ZipFile(package_zip) as native, zipfile.ZipFile(web_zip) as web:
        native_names, web_names = native.namelist(), web.namelist()
        if len(set(native_names)) != len(native_names) or len(set(web_names)) != len(web_names):
            raise ReleaseBuildError("Release archives contain duplicate members")
        manifest = json.loads(native.read("tool-package.json"))
        rows = manifest["payload_files"]
        paths = {str(row["path"]) for row in rows}
        if set(native_names) != {"tool-package.json", *("payload/" + path for path in paths)} or set(web_names) != paths:
            raise ReleaseBuildError("Native and web archives do not contain exactly the shared payload")
        for row in rows:
            path = str(row["path"])
            data = native.read("payload/" + path)
            if (data != web.read(path) or len(data) != row["size"] or sha256_bytes(data) != row["sha256"]):
                raise ReleaseBuildError("Native/web payload byte mismatch: " + path)
        return {"status": "passed", "file_count": len(rows), "package_sha256": manifest["package_sha256"],
                "comparison": "Every decompressed web member equals the matching native payload member and manifest SHA-256."}


def build_release_artifacts(
    repository: Path,
    revision: str,
    output_root: Path,
    *,
    distribution_scope: str = "private-review",
    version_override: str | None = None,
    source_exports: bool = False,
) -> BuiltRelease:
    repository = Path(repository).resolve()
    output_root = Path(output_root).resolve()
    if source_exports and distribution_scope != "public-release":
        raise ReleaseBuildError("Public source exports require fully qualified public-release scope")
    commit = resolve_commit(repository, revision)
    if version_override is not None and distribution_scope != "private-review":
        raise ReleaseBuildError("QA version overrides are allowed only for private-review builds")
    if version_override is not None and not SEMVER.fullmatch(version_override):
        raise ReleaseBuildError("QA version override must be a valid semantic version")
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="figure-release-", dir=output_root) as temp:
        temp_root = Path(temp)
        source = extract_git_archive(repository, commit, temp_root / "source")
        validation = validate_release_source(source, distribution_scope=distribution_scope)
        source_version = str(_read_json(source / "package.json", "Figure package metadata").get("version") or "")
        version = version_override or source_version
        work_package = temp_root / "package"
        manifest = build_tool_package(
            source, work_package, source_revision=commit, version_override=version_override,
            distribution_scope=distribution_scope,
            public_release_eligible=bool(validation.get("public_release_eligible")),
        )
        package_digest = str(manifest["package_sha256"])
        package_relative = Path("archives") / TOOL_ID / f"{version}-{package_digest}.zip"
        web_relative = Path("web") / TOOL_ID / f"{version}-{package_digest}-web.zip"
        package_zip = output_root / package_relative
        web_zip = output_root / web_relative
        for path in (package_zip, web_zip):
            if path.exists():
                raise ReleaseBuildError("A content-addressed Figure release output already exists")
        package_zip.parent.mkdir(parents=True, exist_ok=True)
        web_zip.parent.mkdir(parents=True, exist_ok=True)
        package_archive_sha = _write_deterministic_zip(work_package, package_zip, package=True)
        web_archive_sha = _write_deterministic_zip(work_package, web_zip, package=False)
        archive_parity = verify_archive_payload_parity(package_zip, web_zip)
        source_files = _source_inventory(source)
        core_files = _prefixed_inventory(source, ("app", "vendor", "assets/scientific-packs", "assets/scientific-scenes"))
        web_files = _prefixed_inventory(source, ("web",))
        if sorted(core_files + web_files, key=lambda row: str(row["path"]).casefold()) != source_files:
            raise ReleaseBuildError("Core and web-shell inventories do not exactly partition the Figure source payload")
        inventory = {
            "schema": "figureStudio.sourceInventory.v1",
            "source_revision": commit,
            "package_sha256": package_digest,
            "partitions": {
                "core": {"files": core_files, "file_count": len(core_files),
                         "byte_count": sum(int(row["size"]) for row in core_files),
                         "tree_sha256": _tree_digest(core_files)},
                "web_shell": {"files": web_files, "file_count": len(web_files),
                              "byte_count": sum(int(row["size"]) for row in web_files),
                              "tree_sha256": _tree_digest(web_files)},
            },
            "files": source_files,
        }
        inventory_path = output_root / f"source-inventory-{version}-{package_digest}.json"
        inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        web_inventory = {
            "schema": "figureStudio.webShellInventory.v1",
            "source_revision": commit,
            "package_sha256": package_digest,
            "file_count": len(web_files),
            "byte_count": sum(int(row["size"]) for row in web_files),
            "tree_sha256": _tree_digest(web_files),
            "files": web_files,
        }
        web_inventory_path = output_root / f"web-shell-inventory-{version}-{package_digest}.json"
        web_inventory_path.write_text(json.dumps(web_inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        source_export = None
        if source_exports:
            try:
                from .export_figure_release_source import export_source
            except ImportError:
                from export_figure_release_source import export_source
            source_export = export_source(source, work_package, output_root, cache=repository / "qa_artifacts/vendor-source-cache")
        rights = _rights_receipt(source, validation, scope=distribution_scope)
        rights_path = output_root / f"rights-receipt-{version}-{package_digest}.json"
        rights_path.write_text(json.dumps(rights, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        receipt = {
            "schema": "figureStudio.releaseBuildReceipt.v1",
            "distribution_scope": distribution_scope,
            "public_distribution_authorized": distribution_scope == "public-release" and validation["public_release_eligible"],
            "version": version,
            "source_version": source_version,
            "synthetic_version_identity": version_override is not None,
            "source_revision": commit,
            "host_api": HOST_API,
            "package_sha256": package_digest,
            "package_archive": package_relative.as_posix(),
            "archive_sha256": package_archive_sha,
            "web_archive": web_relative.as_posix(),
            "web_archive_kind": "complete-static-editor-deployment.v1",
            "web_archive_payload_roots": list(PAYLOAD_ROOTS),
            "web_shell_inventory": web_inventory_path.name,
            "web_archive_sha256": web_archive_sha,
            "shared_payload_parity": archive_parity,
            "source_export": source_export,
            "source_inventory": inventory_path.name,
            "rights_receipt": rights_path.name,
            "validation": validation,
        }
        receipt_path = output_root / f"release-receipt-{version}-{package_digest}.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return BuiltRelease(version, commit, package_digest, package_archive_sha, web_archive_sha,
                        package_zip, web_zip, receipt_path, rights_path, inventory_path,
                        distribution_scope, version_override is not None,
                        bool(validation.get("public_release_eligible")))


def catalog_signing_bytes(document: Mapping[str, object]) -> bytes:
    unsigned = dict(document)
    unsigned.pop("signature", None)
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _catalog_public_key(private_key):
    from cryptography.hazmat.primitives import serialization
    return private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _verify_previous_catalog(previous: Mapping[str, object], public_key: bytes) -> None:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if (
        set(previous) != {"schema", "catalog_id", "sequence", "issued_at", "expires_at", "tool_id", "host_api", "releases", "signature"}
        or previous.get("schema") != CATALOG_SCHEMA
        or previous.get("catalog_id") != CATALOG_ID
        or previous.get("tool_id") != TOOL_ID
        or previous.get("host_api") != HOST_API
        or not isinstance(previous.get("releases"), list)
        or len(previous["releases"]) > MAX_CATALOG_RELEASES
        or not isinstance(previous.get("sequence"), int)
        or isinstance(previous.get("sequence"), bool)
        or previous.get("sequence", 0) < 1
    ):
        raise ReleaseBuildError("Previous catalog is not a Figure release-catalog v2 document")
    signature = previous.get("signature")
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "key_id", "value"} or signature.get("algorithm") != "Ed25519" or signature.get("key_id") != CATALOG_KEY_ID:
        raise ReleaseBuildError("Previous catalog signature metadata is unsupported")
    issued_at = _catalog_time(previous.get("issued_at"), "issue")
    expires_at = _catalog_time(previous.get("expires_at"), "expiration")
    now = datetime.now(timezone.utc)
    if expires_at <= issued_at or issued_at > now + timedelta(minutes=5) or expires_at <= now:
        raise ReleaseBuildError("Previous catalog is expired or has invalid UTC validity timestamps")
    import base64
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            base64.b64decode(str(signature.get("value") or ""), validate=True),
            catalog_signing_bytes(previous),
        )
    except (ValueError, TypeError, InvalidSignature) as error:
        raise ReleaseBuildError("Previous catalog signature is invalid") from error
    rows = previous["releases"]
    if not rows:
        raise ReleaseBuildError("Previous catalog must retain at least one release")
    seen_versions: set[str] = set()
    seen_locators: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "version", "source_revision", "host_api", "package_sha256", "archive_sha256", "locator"
        }:
            raise ReleaseBuildError("Previous catalog contains a malformed v2 release row")
        version = str(row["version"])
        revision = str(row["source_revision"])
        locator = str(row["locator"])
        if (
            not SEMVER.fullmatch(version)
            or not FULL_REVISION.fullmatch(revision)
            or row["host_api"] != HOST_API
            or locator != f"archives/{TOOL_ID}/{version}-{row['package_sha256']}.zip"
            or not SHA256.fullmatch(str(row["package_sha256"]))
            or not SHA256.fullmatch(str(row["archive_sha256"]))
            or version in seen_versions
            or locator in seen_locators
        ):
            raise ReleaseBuildError("Previous catalog contains duplicate or malformed release identities")
        seen_versions.add(version)
        seen_locators.add(locator)


def retain_previous_feed(previous_feed: Path, output_root: Path, *, public_key: bytes = TRUSTED_CATALOG_PUBLIC_KEY) -> dict[str, object]:
    """Verify and retain every immutable package archive referenced by a prior feed."""
    previous_feed = Path(previous_feed).resolve()
    output_root = Path(output_root).resolve()
    catalog_path = previous_feed / "catalog.json"
    if catalog_path.is_symlink() or not catalog_path.is_file() or catalog_path.stat().st_size > MAX_PREVIOUS_CATALOG_BYTES:
        raise ReleaseBuildError("Previous feed catalog is missing, linked, or oversized")
    catalog = _read_json(catalog_path, "previous feed catalog")
    _verify_previous_catalog(catalog, public_key)
    for row in catalog["releases"]:
        locator = row["locator"]
        if not isinstance(locator, str) or locator != f"archives/{TOOL_ID}/{row['version']}-{row['package_sha256']}.zip":
            raise ReleaseBuildError("Previous feed locator is not a canonical immutable package path")
        _validate_relative_path(locator)
        source_archive = previous_feed.joinpath(*locator.split("/"))
        if source_archive.is_symlink() or not source_archive.is_file():
            raise ReleaseBuildError(f"Previous feed package archive is missing or linked: {locator}")
        if source_archive.stat().st_size > MAX_PREVIOUS_ARCHIVE_BYTES:
            raise ReleaseBuildError(f"Previous feed package archive exceeds the size limit: {locator}")
        archive_bytes = source_archive.read_bytes()
        if sha256_bytes(archive_bytes) != row["archive_sha256"]:
            raise ReleaseBuildError(f"Previous feed package archive digest is invalid: {locator}")
        _verify_package_zip_bytes(archive_bytes, row)
        destination = output_root.joinpath(*locator.split("/"))
        if destination.exists():
            if destination.read_bytes() != archive_bytes:
                raise ReleaseBuildError("Previous immutable archive collides with new package output")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive_bytes)
    return catalog


def _catalog_time(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReleaseBuildError(f"Previous catalog {label} time must be UTC ISO-8601")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ReleaseBuildError(f"Previous catalog {label} time is invalid") from error
    if parsed.tzinfo != timezone.utc:
        raise ReleaseBuildError(f"Previous catalog {label} time must be UTC")
    return parsed


def _verify_package_zip_bytes(data: bytes, row: Mapping[str, object]) -> None:
    """Bound and safely materialize a prior archive before semantic verification."""
    max_entries, max_total, max_file = 100_000, 1_500_000_000, 250_000_000
    extracted: dict[str, bytes] = {}
    folded: set[str] = set()
    total_size = 0
    try:
        with zipfile.ZipFile(BytesIO(data), "r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > max_entries:
                raise ReleaseBuildError("Previous package archive has an invalid entry count")
            for info in infos:
                relative = "/".join(_validate_relative_path(info.filename))
                key = relative.casefold()
                mode = (info.external_attr >> 16) & 0xFFFF
                file_type = mode & 0o170000
                if key in folded or info.is_dir() or (file_type and file_type != 0o100000):
                    raise ReleaseBuildError("Previous package archive has duplicate, directory, or special entries")
                if info.flag_bits & 0x1 or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise ReleaseBuildError("Previous package archive uses unsupported ZIP features")
                if info.file_size > max_file or info.file_size < 0 or info.compress_size < 0:
                    raise ReleaseBuildError("Previous package archive contains an oversized entry")
                if info.file_size and (not info.compress_size or info.file_size / info.compress_size > 100):
                    raise ReleaseBuildError("Previous package archive has an excessive compression ratio")
                total_size += info.file_size
                if total_size > max_total:
                    raise ReleaseBuildError("Previous package archive exceeds the total size limit")
                folded.add(key)
                extracted[relative] = archive.read(info)
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise ReleaseBuildError("Previous package archive is invalid") from error
    if "tool-package.json" not in extracted:
        raise ReleaseBuildError("Previous package archive has no package manifest")
    with tempfile.TemporaryDirectory(prefix="figure-feed-verify-") as temporary:
        root = Path(temporary)
        for relative, content in extracted.items():
            target = root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        manifest = _read_json(root / "tool-package.json", "previous tool package manifest")
        if (
            manifest.get("version") != row.get("version")
            or manifest.get("package_sha256") != row.get("package_sha256")
            or manifest.get("source_provenance", {}).get("source_revision") != row.get("source_revision")
        ):
            raise ReleaseBuildError("Previous archive metadata differs from its catalog row")
        verify_tool_package(root, trusted_package_sha256=str(row["package_sha256"]))


def signed_catalog_document(
    release: BuiltRelease,
    *,
    private_key,
    previous_catalog: Mapping[str, object] | None,
    initialize_catalog: bool = False,
    allow_private_review_candidate: bool = False,
    trusted_public_key: bytes = TRUSTED_CATALOG_PUBLIC_KEY,
    now: datetime | None = None,
) -> dict[str, object]:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ReleaseBuildError("An Ed25519 catalog signing key is required")
    if release.distribution_scope == "public-release":
        if release.synthetic_version_identity or not release.public_release_eligible:
            raise ReleaseBuildError("Public catalog signing requires an eligible, nonsynthetic public release")
    elif not allow_private_review_candidate or release.distribution_scope != "private-review":
        raise ReleaseBuildError("Private-review catalog signing requires its explicit QA-only opt-in")
    if _catalog_public_key(private_key) != trusted_public_key:
        raise ReleaseBuildError("Catalog signing key does not match the Superbench host trust anchor")
    if previous_catalog is None:
        if not initialize_catalog:
            raise ReleaseBuildError("A prior signed catalog is required; initial catalog creation must be explicit")
        sequence, rows = 1, []
    else:
        _verify_previous_catalog(previous_catalog, trusted_public_key)
        sequence = int(previous_catalog["sequence"]) + 1
        rows = [dict(row) for row in previous_catalog["releases"]]
    locator = f"archives/{TOOL_ID}/{release.version}-{release.package_sha256}.zip"
    new_row = {
        "version": release.version,
        "source_revision": release.source_revision,
        "host_api": HOST_API,
        "package_sha256": release.package_sha256,
        "archive_sha256": release.archive_sha256,
        "locator": locator,
    }
    prior = next((row for row in rows if row.get("version") == release.version), None)
    if prior is not None:
        if prior != new_row:
            raise ReleaseBuildError("An existing Figure version cannot be replaced with another artifact")
    else:
        rows.append(new_row)
    if len(rows) > MAX_CATALOG_RELEASES:
        raise ReleaseBuildError("Figure release catalog exceeds the Core host's supported release limit")
    timestamp = now or datetime.now(timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc).replace(microsecond=0)
    document: dict[str, object] = {
        "schema": CATALOG_SCHEMA,
        "catalog_id": CATALOG_ID,
        "sequence": sequence,
        "issued_at": timestamp.isoformat().replace("+00:00", "Z"),
        "expires_at": (timestamp + timedelta(days=180)).isoformat().replace("+00:00", "Z"),
        "tool_id": TOOL_ID,
        "host_api": HOST_API,
        "releases": rows,
        "signature": {"algorithm": "Ed25519", "key_id": CATALOG_KEY_ID, "value": ""},
    }
    import base64
    document["signature"]["value"] = base64.b64encode(private_key.sign(catalog_signing_bytes(document))).decode("ascii")
    return document


def _load_private_key_from_environment(name: str, *, expected_public_key: bytes = TRUSTED_CATALOG_PUBLIC_KEY):
    value = os.environ.get(name)
    if not value:
        return None
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    try:
        key = load_pem_private_key(value.encode("utf-8"), password=None)
    except (ValueError, TypeError) as error:
        raise ReleaseBuildError("Catalog signing secret is not a valid unencrypted PEM key") from error
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(key, Ed25519PrivateKey):
        raise ReleaseBuildError("Catalog signing secret must be an Ed25519 private key")
    if _catalog_public_key(key) != expected_public_key:
        raise ReleaseBuildError("Catalog signing secret does not match the configured trust anchor")
    return key


def _public_key_from_environment(name: str) -> bytes:
    value = os.environ.get(name, "").strip()
    try:
        key = bytes.fromhex(value)
    except ValueError as error:
        raise ReleaseBuildError("Public release trust anchor must be a 64-character lowercase hex key") from error
    if len(key) != 32 or value != value.lower():
        raise ReleaseBuildError("Public release trust anchor must be a 32-byte lowercase hex key")
    return key


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD", help="Full commit or ref archived by Git")
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parents[1] / "qa_artifacts" / "figure-release")
    parser.add_argument("--distribution-scope", choices=("private-review", "public-release"), default="private-review")
    parser.add_argument("--qa-version-override", help="Private-review-only synthetic package version for compatibility QA")
    parser.add_argument("--sign-private-review-candidate", action="store_true",
                        help="Explicitly sign a private-review QA feed using the separate QA key environment variable")
    parser.add_argument("--public-signing-key-env", default="FIGURE_RELEASE_SIGNING_KEY")
    parser.add_argument("--public-trust-anchor-env", default="FIGURE_RELEASE_PUBLIC_TRUST_ANCHOR")
    parser.add_argument("--qa-signing-key-env", default="FIGURE_RELEASE_QA_SIGNING_KEY")
    parser.add_argument("--previous-feed", type=Path, help="Verified prior feed directory with catalog.json and all referenced ZIPs")
    parser.add_argument("--initialize-catalog", action="store_true")
    parser.add_argument("--artifacts-only", action="store_true",
                        help="Build validated native/static archives and receipts without issuing or signing an update catalog")
    parser.add_argument("--source-exports", action="store_true",
                        help="Also prepare an unchanged-payload public source tree and full preferred-source ZIP from the same snapshot")
    args = parser.parse_args()
    catalog_options = {"--previous-feed", "--initialize-catalog", "--sign-private-review-candidate",
                       "--public-signing-key-env", "--public-trust-anchor-env", "--qa-signing-key-env"}
    if args.artifacts_only and any(token.split("=", 1)[0] in catalog_options for token in __import__("sys").argv[1:]):
        parser.error("--artifacts-only cannot be combined with catalog or signing options")
    repo = args.repository.resolve()
    output = args.output_root.resolve()
    qa_root = (repo / "qa_artifacts").resolve()
    if repo not in qa_root.parents or qa_root not in output.parents:
        raise SystemExit("Release output must stay under this repository's ignored qa_artifacts directory")
    try:
        release = build_release_artifacts(repo, args.revision, output, distribution_scope=args.distribution_scope,
                                          version_override=args.qa_version_override, source_exports=args.source_exports)
        if args.artifacts_only:
            public_trust_anchor = TRUSTED_CATALOG_PUBLIC_KEY
            key = None
        elif args.distribution_scope == "public-release":
            public_trust_anchor = _public_key_from_environment(args.public_trust_anchor_env)
            key = _load_private_key_from_environment(args.public_signing_key_env,
                                                     expected_public_key=public_trust_anchor)
        elif args.sign_private_review_candidate:
            public_trust_anchor = TRUSTED_CATALOG_PUBLIC_KEY
            key = _load_private_key_from_environment(args.qa_signing_key_env)
        else:
            public_trust_anchor = TRUSTED_CATALOG_PUBLIC_KEY
            key = None
        if args.distribution_scope == "public-release" and key is None and not args.artifacts_only:
            raise ReleaseBuildError("Public catalog signing requires a configured production signing key")
        if args.sign_private_review_candidate and key is None:
            raise ReleaseBuildError("Private-review catalog signing was requested but the QA key is unavailable")
        if args.previous_feed and key is None:
            raise ReleaseBuildError("Retaining a prior feed requires an explicitly selected signing key")
        if args.previous_feed and args.initialize_catalog:
            raise ReleaseBuildError("A feed cannot both continue a prior snapshot and initialize a new sequence")
        catalog_path = None
        if key is not None:
            previous = retain_previous_feed(args.previous_feed, output, public_key=public_trust_anchor) if args.previous_feed else None
            document = signed_catalog_document(
                release, private_key=key, previous_catalog=previous,
                initialize_catalog=args.initialize_catalog,
                allow_private_review_candidate=args.sign_private_review_candidate,
                trusted_public_key=public_trust_anchor,
            )
            catalog_path = output / "catalog.json"
            catalog_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({
            "status": "built_private_review_candidate" if args.distribution_scope == "private-review" else "built_public_release_candidate",
            "version": release.version,
            "synthetic_version_identity": release.synthetic_version_identity,
            "source_revision": release.source_revision,
            "package_sha256": release.package_sha256,
            "archive_sha256": release.archive_sha256,
            "web_archive_sha256": release.web_archive_sha256,
            "package_archive": release.package_zip.relative_to(output).as_posix(),
            "web_archive": release.web_zip.relative_to(output).as_posix(),
            "release_receipt": release.receipt_path.relative_to(output).as_posix(),
            "rights_receipt": release.rights_receipt_path.relative_to(output).as_posix(),
            "source_inventory": release.inventory_path.relative_to(output).as_posix(),
            "web_shell_inventory": f"web-shell-inventory-{release.version}-{release.package_sha256}.json",
            "signed_catalog": catalog_path.relative_to(output).as_posix() if catalog_path else None,
            "local_paths_included": False,
        }, indent=2))
    except (ReleaseBuildError, OSError, ValueError) as error:
        print(f"Figure release build failed: {error}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
