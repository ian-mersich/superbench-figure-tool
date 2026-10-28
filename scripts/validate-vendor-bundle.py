from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
POLICY = "figure_studio_curated_local_vendor.v1"
SCHEMA = "figureStudio.vendorManifest.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FABRIC_SOURCE_RECEIPT = {
    "package": "fabric",
    "version": "7.3.1",
    "retrieved_on": "2026-07-22",
    "registry": "npm",
    "tarball_url": "https://registry.npmjs.org/fabric/-/fabric-7.3.1.tgz",
    "tarball_integrity_sha512": "sha512-RoLAQzUX+/3RNMYKliuN0P2HXdSDEGzyjS7FnmEbo3nhb8LFh59T+l3f6ApIu5LT4YB49YfMNrEajeIbutmD7Q==",
    "tarball_shasum_sha1": "1dee1b68bb793aca68c0d31936b3897f330ef47b",
    "tarball_bytes": 4_934_943,
    "tarball_sha256": "1c8402379b356934b921fc90bc8d6e3d0d28166480649e31c1618c7d231a7a39",
    "release_tag": "v731",
    "release_tag_url": "https://github.com/fabricjs/fabric.js/releases/tag/v731",
    "release_commit": "b305406837c50b5638ce32c7558fc83e9c8c4159",
    "upstream_runtime_path": "package/dist/index.min.js",
    "upstream_runtime_bytes": 298_256,
    "upstream_runtime_sha256": "fd2ef30a5b5fa361bc00d4ee56dd57afc4b07f640eeea6764a99123f984be805",
    "upstream_license_path": "package/LICENSE",
    "upstream_license_url": "https://raw.githubusercontent.com/fabricjs/fabric.js/b305406837c50b5638ce32c7558fc83e9c8c4159/LICENSE",
    "upstream_license_bytes": 1_243,
    "upstream_license_sha256": "eda412692b7398293a049ecf913319da26eb8f7fe27f10709821dd187b517e0b",
    "checkout_materialization": "crlf",
    "identity_receipt_not_ownership_determination": True,
}
POLYGON_CLIPPING_SOURCE_RECEIPT = {
    "package": "polygon-clipping",
    "version": "0.15.7",
    "retrieved_on": "2026-08-08",
    "registry": "npm",
    "tarball_url": "https://registry.npmjs.org/polygon-clipping/-/polygon-clipping-0.15.7.tgz",
    "tarball_integrity_sha512": "sha512-nhfdr83ECBg6xtqOAJab1tbksbBAOMUltN60bU+llHVOL0e5Onm1WpAXXWXVB39L8AJFssoIhEVuy/S90MmotA==",
    "tarball_shasum_sha1": "3823ca1e372566f350795ce9dd9a7b19e97bdaad",
    "tarball_bytes": 91_226,
    "tarball_sha256": "23bdea671a65011107d91536881f527c8e2e6820f59e4bc1408a94d7cc11d5b7",
    "release_tag": "v0.15.7",
    "release_tag_url": "https://github.com/mfogel/polygon-clipping/releases/tag/v0.15.7",
    "release_commit": "25f2a460ca7bd750d958d3d83b0037a32fcf75f6",
    "upstream_runtime_path": "package/dist/polygon-clipping.umd.min.js",
    "upstream_runtime_bytes": 29_106,
    "upstream_runtime_sha256": "7f8619e84a86ce8dd400c9b50430e9c8cf8f26027b19eeb479f109f5c1a9d688",
    "upstream_license_path": "package/LICENSE.md",
    "upstream_license_url": "https://raw.githubusercontent.com/mfogel/polygon-clipping/25f2a460ca7bd750d958d3d83b0037a32fcf75f6/LICENSE.md",
    "upstream_license_bytes": 1_327,
    "upstream_license_sha256": "864ae9e4ed75e1571a3bcf5dc9070264213445b32e7e2af5bf60eba46fb656d0",
    "checkout_materialization": "exact-npm-package-bytes",
    "identity_receipt_not_ownership_determination": True,
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_path(value: object, *, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SystemExit(f"{field} must be a non-empty canonical path")
    if "\\" in value:
        raise SystemExit(f"{field} must use forward slashes: {value}")
    relative = PurePosixPath(value)
    if relative.is_absolute() or relative.parts[0] != "vendor" or any(part in {"", ".", ".."} for part in relative.parts):
        raise SystemExit(f"invalid manifest path in {field}: {value}")
    return relative


def _exact_file(root: Path, relative: PurePosixPath) -> Path:
    current = root
    for part in relative.parts:
        if current.is_symlink():
            raise SystemExit(f"symlinked manifest path is not allowed: {relative.as_posix()}")
        if not current.is_dir():
            raise SystemExit(f"manifest path parent is not a directory: {relative.as_posix()}")
        names = {child.name for child in current.iterdir()}
        if part not in names:
            if any(name.casefold() == part.casefold() for name in names):
                raise SystemExit(f"case-drifted manifest path: {relative.as_posix()}")
            raise SystemExit(f"manifest file is missing: {relative.as_posix()}")
        current = current / part
    if current.is_symlink():
        raise SystemExit(f"symlinked manifest file is not allowed: {relative.as_posix()}")
    if not current.is_file():
        raise SystemExit(f"manifest path is not a regular file: {relative.as_posix()}")
    return current


def _require_list(payload: dict, key: str) -> list:
    values = payload.get(key)
    if not isinstance(values, list):
        raise SystemExit(f"{key} must be a list")
    return values


def _manifest_entries(payload: dict) -> list[dict]:
    entries: list[dict] = []
    for key in ("runtime_files", "license_files", "notice_files", "native_artifact_files"):
        values = payload.get(key, []) if key == "native_artifact_files" else _require_list(payload, key)
        if not isinstance(values, list):
            raise SystemExit("native_artifact_files must be a list")
        for entry in values:
            if not isinstance(entry, dict):
                raise SystemExit(f"{key} entries must be objects")
            entries.append(entry)
    return entries


def _validate_unique_paths(entries: list[dict]) -> dict[str, dict]:
    by_path: dict[str, dict] = {}
    casefolded: dict[str, str] = {}
    for index, entry in enumerate(entries):
        path = _canonical_path(entry.get("path"), field=f"manifest entry {index} path").as_posix()
        if path in by_path:
            raise SystemExit(f"duplicate manifest path: {path}")
        previous = casefolded.get(path.casefold())
        if previous is not None:
            raise SystemExit(f"case-equivalent duplicate manifest paths: {previous} and {path}")
        by_path[path] = entry
        casefolded[path.casefold()] = path
    return by_path


def _validate_file_identity(root: Path, relative: str, entry: dict) -> bytes:
    path = _exact_file(root, PurePosixPath(relative))
    expected_bytes = entry.get("bytes")
    expected_hash = entry.get("sha256")
    if not isinstance(expected_bytes, int) or expected_bytes < 0:
        raise SystemExit(f"bytes must be a non-negative integer for {relative}")
    if not isinstance(expected_hash, str) or not SHA256.fullmatch(expected_hash):
        raise SystemExit(f"sha256 must be a lowercase 64-character digest for {relative}")
    data = path.read_bytes()
    matches_materialization = len(data) == expected_bytes and _sha256_bytes(data) == expected_hash
    matches_fabric_upstream = (
        relative == "vendor/fabric/index.min.js"
        and entry.get("upstream_lf_bytes") == FABRIC_SOURCE_RECEIPT["upstream_runtime_bytes"]
        and entry.get("upstream_lf_sha256") == FABRIC_SOURCE_RECEIPT["upstream_runtime_sha256"]
        and len(data) == FABRIC_SOURCE_RECEIPT["upstream_runtime_bytes"]
        and _sha256_bytes(data) == FABRIC_SOURCE_RECEIPT["upstream_runtime_sha256"]
    )
    if not (matches_materialization or matches_fabric_upstream):
        if len(data) != expected_bytes:
            raise SystemExit(f"byte count mismatch for {relative}")
        raise SystemExit(f"sha256 mismatch for {relative}")
    return data


def _matches_reviewed_fabric_bytes(
    data: bytes,
    *,
    materialized_bytes: int,
    materialized_sha256: str,
    upstream_lf_bytes: int,
    upstream_lf_sha256: str,
) -> str | None:
    """Identify only the reviewed CRLF materialization or exact upstream LF bytes."""
    if len(data) == materialized_bytes and _sha256_bytes(data) == materialized_sha256:
        return "windows-materialization"
    if len(data) == upstream_lf_bytes and _sha256_bytes(data) == upstream_lf_sha256:
        return "upstream-lf"
    return None


def _validate_fabric_receipt(receipt: dict, entries: dict[str, dict], root: Path) -> None:
    for key, expected in FABRIC_SOURCE_RECEIPT.items():
        if receipt.get(key) != expected:
            raise SystemExit(f"Fabric source receipt field {key} does not match the reviewed upstream identity")
    verification = receipt.get("verification")
    if not isinstance(verification, str) or "439 CRLF" not in verification or "exact npm package bytes" not in verification:
        raise SystemExit("Fabric source receipt must describe the reviewed Windows materialization")

    relative = "vendor/fabric/index.min.js"
    entry = entries.get(relative)
    if entry is None:
        raise SystemExit("Fabric runtime entry is missing")
    if entry.get("package") != "fabric" or entry.get("version") != "7.3.1":
        raise SystemExit("Fabric runtime entry must bind package fabric version 7.3.1")
    expected_fields = {
        "bytes": 298_695,
        "sha256": "6aa6f34043486b265c89347f59df9f1c28489269694bd93f6a4915b77e811bfe",
        "crlf_count": 439,
        "upstream_lf_bytes": 298_256,
        "upstream_lf_sha256": "fd2ef30a5b5fa361bc00d4ee56dd57afc4b07f640eeea6764a99123f984be805",
    }
    for key, expected in expected_fields.items():
        if entry.get(key) != expected:
            raise SystemExit(f"Fabric runtime field {key} does not match the reviewed Windows materialization")
    data = _exact_file(root, PurePosixPath(relative)).read_bytes()
    identity = _matches_reviewed_fabric_bytes(
        data,
        materialized_bytes=expected_fields["bytes"],
        materialized_sha256=expected_fields["sha256"],
        upstream_lf_bytes=int(receipt["upstream_runtime_bytes"]),
        upstream_lf_sha256=str(receipt["upstream_runtime_sha256"]),
    )
    if identity == "windows-materialization":
        if data.count(b"\r\n") != 439 or data.count(b"\n") != 439:
            raise SystemExit("Fabric runtime line endings do not match the reviewed Windows materialization")
        normalized = data.replace(b"\r\n", b"\n")
        if len(normalized) != receipt["upstream_runtime_bytes"] or _sha256_bytes(normalized) != receipt["upstream_runtime_sha256"]:
            raise SystemExit("Fabric runtime does not normalize to the authenticated npm 7.3.1 bytes")
    elif identity != "upstream-lf":
        raise SystemExit("Fabric runtime matches neither its reviewed Windows materialization nor upstream LF bytes")

    license_entry = entries.get("vendor/licenses/fabric-LICENSE")
    if license_entry is None:
        raise SystemExit("Fabric license entry is missing")
    if license_entry.get("bytes") != receipt["upstream_license_bytes"] or license_entry.get("sha256") != receipt["upstream_license_sha256"]:
        raise SystemExit("Fabric license entry does not match the authenticated upstream license")


def _validate_polygon_clipping_receipt(receipt: dict, entries: dict[str, dict]) -> None:
    for key, expected in POLYGON_CLIPPING_SOURCE_RECEIPT.items():
        if receipt.get(key) != expected:
            raise SystemExit(f"polygon-clipping source receipt field {key} does not match the reviewed upstream identity")
    verification = receipt.get("verification")
    if not isinstance(verification, str) or "exact members" not in verification or "pinned npm 0.15.7 tarball" not in verification:
        raise SystemExit("polygon-clipping source receipt must bind the checked-in files to the pinned npm tarball")

    runtime_entry = entries.get("vendor/polygon-clipping/polygon-clipping.umd.min.js")
    if runtime_entry is None or runtime_entry.get("package") != "polygon-clipping" or runtime_entry.get("version") != "0.15.7":
        raise SystemExit("polygon-clipping runtime entry must bind package polygon-clipping version 0.15.7")
    if runtime_entry.get("bytes") != receipt["upstream_runtime_bytes"] or runtime_entry.get("sha256") != receipt["upstream_runtime_sha256"]:
        raise SystemExit("polygon-clipping runtime does not match the authenticated npm tarball member")

    license_entry = entries.get("vendor/licenses/polygon-clipping-LICENSE.md")
    if license_entry is None:
        raise SystemExit("polygon-clipping license entry is missing")
    if license_entry.get("bytes") != receipt["upstream_license_bytes"] or license_entry.get("sha256") != receipt["upstream_license_sha256"]:
        raise SystemExit("polygon-clipping license does not match the authenticated npm tarball member")


def _validate_source_receipts(payload: dict, entries: dict[str, dict], root: Path) -> None:
    receipts = _require_list(payload, "source_receipts")
    if len(receipts) != 2 or any(not isinstance(receipt, dict) for receipt in receipts):
        raise SystemExit("source_receipts must contain exactly the reviewed Fabric and polygon-clipping receipts")
    by_package = {str(receipt.get("package") or ""): receipt for receipt in receipts}
    if set(by_package) != {"fabric", "polygon-clipping"}:
        raise SystemExit("source_receipts must contain exactly one Fabric and one polygon-clipping receipt")
    _validate_fabric_receipt(by_package["fabric"], entries, root)
    _validate_polygon_clipping_receipt(by_package["polygon-clipping"], entries)


EXPECTED_PDFIUM_NOTICE_COMPONENTS = set(['abseil.txt', 'agg23.txt', 'dragonbox-Apache2-LLVM.txt', 'dragonbox-Boost.txt', 'emscripten-compiler-rt-license.txt', 'emscripten-dlmalloc-source.txt', 'emscripten-libcxx-license.txt', 'emscripten-libcxxabi-license.txt', 'emscripten-license.txt', 'emscripten-musl-copyright.txt', 'fast_float.txt', 'freetype.txt', 'harfbuzz.txt', 'highway.txt', 'icu.txt', 'lcms.txt', 'libjpeg_turbo.ijg', 'libjpeg_turbo.md', 'libopenjpeg.txt', 'libpng.txt', 'libyuv-LICENSE.txt', 'pdfium.txt', 'simdutf.txt', 'supplier-mit', 'zlib.txt'])


def _validate_binary_artifacts(payload: dict, lock: dict, entries: dict, root: Path) -> None:
    rows = lock.get("binary_artifacts", [])
    if not isinstance(rows, list) or len(rows) > 1:
        raise SystemExit("Only the reviewed PDFium binary-artifact record is supported")
    if not rows:
        if payload.get("native_artifact_files"):
            raise SystemExit("Native inventory requires its source-lock binary artifact")
        return
    row = rows[0]
    if row.get("id") != "pdfium-wasm-158.0.8111.0" or row.get("kind") != "supplier-binary-release" or row.get("publisher") != "bblanchon/pdfium-binaries":
        raise SystemExit("Unreviewed native binary artifact")
    if row.get("notice_admission") != "supplier-release-and-explicit-supplements" or row.get("legal_clearance") is not False:
        raise SystemExit("Native artifact notice authority must remain explicit")
    if payload["packages"].get(row["package"]) != row["version"]:
        raise SystemExit("Native artifact package identity differs")
    archive = row.get("archive", {})
    if not str(archive.get("url", "")).startswith("https://github.com/bblanchon/pdfium-binaries/releases/download/") or not SHA256.fullmatch(str(archive.get("sha256", ""))) or not isinstance(archive.get("bytes"), int):
        raise SystemExit("Native artifact origin/digest is missing")
    if {x.get("path") for x in row.get("runtime_files", [])} != {"vendor/pdfium/pdfium.esm.js", "vendor/pdfium/pdfium.js", "vendor/pdfium/pdfium.wasm"}:
        raise SystemExit("Native artifact must bind supplier module, WASM and isolated factory")
    expected_components = EXPECTED_PDFIUM_NOTICE_COMPONENTS
    notices = row.get("notices", [])
    if {x.get("component") for x in notices} != expected_components or len(notices) != len(expected_components):
        raise SystemExit("Native artifact supplier/runtime notice set is incomplete")
    native_paths = {x["path"] for x in payload.get("native_artifact_files", [])}
    expected_native = {x["path"] for x in notices + row.get("historical_inputs", [])} - {"vendor/pdfium/notices/supplier/LICENSE"}
    if native_paths != expected_native:
        raise SystemExit("Native metadata/notice inventory differs from its binary artifact")
    for item in row["runtime_files"] + notices + row.get("historical_inputs", []):
        entry = entries.get(item["path"])
        if not entry or any(entry.get(k) != item[k] for k in ("bytes", "sha256")):
            raise SystemExit("Native artifact file identity differs: " + item["path"])
    vendor_notice = (root / "vendor/NOTICE").read_text(encoding="utf-8")
    for item in notices:
        if item.get("text_encoding") not in ("utf-8", "latin-1"):
            raise SystemExit("Native notice text encoding is undeclared")
        text = (root / item["path"]).read_bytes().decode(item["text_encoding"]).replace("\r\n", "\n").replace("\r", "\n").rstrip()
        if not text or text not in vendor_notice:
            raise SystemExit("Generated vendor notice omits native terms: " + item["path"])
    app_notice = (root / "app/legal/NOTICE").read_text(encoding="utf-8")
    if app_notice != (root / "NOTICE").read_text(encoding="utf-8"):
        raise SystemExit("Root/app first-party notices must match")
    for credit in ("based in part on the work of the FreeType Team", "based in part on the work of the Independent JPEG Group"):
        if credit not in vendor_notice or credit not in app_notice:
            raise SystemExit("Native FreeType/IJG distribution acknowledgement missing")


def validate(root: Path = ROOT) -> None:
    root = root.resolve()
    vendor_root = root / "vendor"
    manifest = vendor_root / "manifest.json"
    if manifest.is_symlink():
        raise SystemExit("vendor/manifest.json must not be a symlink")
    if not manifest.is_file():
        raise SystemExit("vendor/manifest.json is missing")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"vendor/manifest.json is invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise SystemExit("vendor manifest must be an object")
    if payload.get("schema") != SCHEMA:
        raise SystemExit(f"vendor manifest schema must be {SCHEMA}")
    if payload.get("installed") is not True:
        raise SystemExit("vendor manifest must declare installed=true")
    if payload.get("policy") != POLICY:
        raise SystemExit(f"vendor manifest policy must be {POLICY}")
    if payload.get("hosted_external_scripts_allowed") is not False:
        raise SystemExit("hosted_external_scripts_allowed must be false")

    source_lock_path = vendor_root / "source-lock.json"
    source_guide_path = vendor_root / "SOURCE_MATERIALS.md"
    for path in (source_lock_path, source_guide_path):
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"vendor source metadata file is missing or not a regular file: {path.relative_to(root).as_posix()}")
    try:
        source_lock = json.loads(source_lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"vendor/source-lock.json is invalid JSON: {error}") from error
    if (
        not isinstance(source_lock, dict)
        or source_lock.get("schema") != "figureStudio.vendorSourceLock.v1"
        or not isinstance(source_lock.get("source_packages"), list)
        or not isinstance(source_lock.get("npm_packages"), list)
    ):
        raise SystemExit("vendor/source-lock.json has an invalid source lock schema")
    metadata_entries = _require_list(payload, "source_metadata_files")
    metadata_paths = set()
    for index, entry in enumerate(metadata_entries):
        if not isinstance(entry, dict):
            raise SystemExit("source_metadata_files entries must be objects")
        relative = _canonical_path(entry.get("path"), field=f"source metadata entry {index} path").as_posix()
        if relative in metadata_paths:
            raise SystemExit(f"duplicate source metadata path: {relative}")
        metadata_paths.add(relative)
        _validate_file_identity(root, relative, entry)
    if metadata_paths != {"vendor/source-lock.json", "vendor/SOURCE_MATERIALS.md"}:
        raise SystemExit("source_metadata_files must hash source-lock.json and SOURCE_MATERIALS.md exactly")

    packages = payload.get("packages")
    if not isinstance(packages, dict) or not packages or not all(isinstance(key, str) and isinstance(value, str) and key and value for key, value in packages.items()):
        raise SystemExit("packages must be a non-empty string-to-version mapping")
    entries = _manifest_entries(payload)
    by_path = _validate_unique_paths(entries)

    runtime_entries = _require_list(payload, "runtime_files")
    runtime_ids = [entry.get("id") for entry in runtime_entries]
    if any(not isinstance(value, str) or not value for value in runtime_ids) or len(runtime_ids) != len(set(runtime_ids)):
        raise SystemExit("runtime_files must have unique non-empty ids")
    runtime_packages = [entry.get("package") for entry in runtime_entries]
    if set(runtime_packages) != set(packages):
        raise SystemExit("runtime_files package names must exactly match packages")
    for entry in runtime_entries:
        if entry.get("version") != packages.get(entry.get("package")):
            raise SystemExit(f"runtime version mismatch for package {entry.get('package')}")

    license_entries = _require_list(payload, "license_files")
    license_packages = [entry.get("package") for entry in license_entries]
    if len(license_packages) != len(set(license_packages)) or set(license_packages) != set(packages):
        raise SystemExit("license_files must contain exactly one license for every package")

    notice_entries = _require_list(payload, "notice_files")
    if len(notice_entries) != 1 or notice_entries[0].get("path") != "vendor/NOTICE":
        raise SystemExit("notice_files must hash the standalone vendor/NOTICE file exactly")

    required = [_canonical_path(value, field="required_core_files entry").as_posix() for value in _require_list(payload, "required_core_files")]
    optional = [_canonical_path(value, field="optional_pdf_files entry").as_posix() for value in _require_list(payload, "optional_pdf_files")]
    declared_runtime = {str(entry["path"]) for entry in runtime_entries}
    if len(required + optional) != len(set(path.casefold() for path in required + optional)):
        raise SystemExit("required_core_files and optional_pdf_files contain duplicate or case-equivalent paths")
    if set(required + optional) != declared_runtime:
        raise SystemExit("required_core_files and optional_pdf_files must exactly partition runtime_files")

    for relative, entry in by_path.items():
        _validate_file_identity(root, relative, entry)

    for path in vendor_root.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"symlinked vendor content is not allowed: {path.relative_to(root).as_posix()}")
    actual_files = {
        path.relative_to(root).as_posix()
        for path in vendor_root.rglob("*")
        if path.is_file() and path not in {manifest, source_lock_path, source_guide_path}
        and path.relative_to(vendor_root).parts[:1] != ("source-materials",)
    }
    declared_files = set(by_path)
    missing = sorted(declared_files - actual_files)
    extra = sorted(actual_files - declared_files)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise SystemExit("vendor inventory does not exactly match manifest: " + "; ".join(details))

    _validate_source_receipts(payload, by_path, root)
    _validate_binary_artifacts(payload, source_lock, by_path, root)
    source_materials = vendor_root / "source-materials"
    if source_materials.exists():
        verifier = root / "scripts" / "prepare-vendor-source.py"
        if verifier.is_symlink() or not verifier.is_file():
            raise SystemExit("vendor source materials are present but scripts/prepare-vendor-source.py is missing")
        result = subprocess.run(
            [sys.executable, str(verifier), "--repository-root", str(root), "--verify", str(source_materials)],
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit("vendor/source-materials failed its pinned source inventory verification")


def main() -> int:
    validate()
    print("Figure Tool vendor bundle ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
