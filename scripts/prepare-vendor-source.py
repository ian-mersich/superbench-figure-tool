from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request
from collections import defaultdict
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
LOCK_RELATIVE = Path("vendor/source-lock.json")
SCHEMA = "figureStudio.vendorSourceLock.v1"
INDEX_SCHEMA = "figureStudio.vendorSourceIndex.v2"
HEX = re.compile(r"^[0-9a-f]{64}$")


def _filesystem_path(path: Path | str) -> Path:
    """Return an OS-facing path that can address deep Windows source trees."""
    path = Path(path)
    if os.name != "nt":
        return path
    raw = os.path.abspath(os.fspath(path))
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw.lstrip("\\"))
    return Path("\\\\?\\" + raw)


def _absolute_path(path: Path | str) -> Path:
    """Make an absolute path without resolving components through Windows MAX_PATH APIs."""
    return Path(os.path.abspath(os.fspath(path)))


def _digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with _filesystem_path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _sha512_sri(path: Path) -> str:
    digest = hashlib.sha512(_filesystem_path(path).read_bytes()).digest()
    return "sha512-" + base64.b64encode(digest).decode("ascii")


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "_", value).strip("._")
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"unsafe source identifier: {value!r}")
    return cleaned


def _npm_slug(name: str, version: str) -> str:
    """Use an npm-readable package/version path while replacing its scope slash."""
    slug = f"{name.replace('/', '_')}@{version}"
    if not re.fullmatch(r"@?[A-Za-z0-9._+-]+@[0-9A-Za-z][0-9A-Za-z.+_-]*", slug):
        raise ValueError(f"unsafe npm package output path: {name}@{version}")
    return slug


def _load_lock(repository_root: Path) -> tuple[dict, bytes]:
    lock_path = _filesystem_path(repository_root / LOCK_RELATIVE)
    raw = lock_path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError(f"unsupported source lock: {lock_path}")
    repositories = payload.get("source_packages")
    npm_packages = payload.get("npm_packages")
    if not isinstance(repositories, list) or not isinstance(npm_packages, list):
        raise ValueError("source lock requires source_packages and npm_packages lists")
    if any(not isinstance(item, dict) for item in repositories + npm_packages):
        raise ValueError("source lock package rows must be objects")
    ids = [item.get("id") for item in repositories]
    package_keys = [(item.get("name"), item.get("version")) for item in npm_packages]
    if len(ids) != len(repositories) or len(ids) != len(set(ids)):
        raise ValueError("source repository ids must be unique objects")
    if len(package_keys) != len(npm_packages) or len(package_keys) != len(set(package_keys)):
        raise ValueError("npm source packages must be unique by name and version")
    return payload, raw


def _validate_archive_row(row: dict, *, npm: bool) -> None:
    required = ("name", "version", "integrity") if npm else (
        "id", "name", "version", "commit", "archive_url", "archive_bytes", "archive_sha256", "archive_root"
    )
    if any(not isinstance(row.get(key), str) or not row.get(key) for key in required if key not in {"archive_bytes"}):
        raise ValueError(f"malformed {'npm' if npm else 'repository'} source row: {row}")
    if npm:
        if not isinstance(row["integrity"], str) or not re.fullmatch(r"sha512-[A-Za-z0-9+/]{86}==", row["integrity"]):
            raise ValueError(f"npm integrity must be SHA-512 SRI for {row['name']}@{row['version']}")
        if not re.fullmatch(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*", row["name"]):
            raise ValueError(f"invalid npm package name: {row['name']!r}")
        if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+_-]*", row["version"]):
            raise ValueError(f"invalid npm package version: {row['version']!r}")
    else:
        if not isinstance(row.get("archive_bytes"), int) or row["archive_bytes"] < 1:
            raise ValueError(f"invalid source archive size for {row['id']}")
        if not HEX.fullmatch(str(row["archive_sha256"])):
            raise ValueError(f"invalid source archive digest for {row['id']}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(row["commit"])):
            raise ValueError(f"source repository commit must be a full Git SHA for {row['id']}")
        if not row["archive_url"].endswith("/" + row["commit"]):
            raise ValueError(f"repository archive URL must end with the pinned commit for {row['id']}")
        _safe_member_path(row["archive_root"])


def _fetch(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "FigureTool-vendor-source-preparer/1"})
    with urllib.request.urlopen(request, timeout=180) as response, _filesystem_path(target).open("wb") as stream:
        shutil.copyfileobj(response, stream, length=1024 * 1024)


def _get_archive(row: dict, cache: Path, *, npm: bool) -> Path:
    if npm:
        package_key = _safe_id(f"{row['name']}@{row['version']}")
        suffix = ".tgz"
        url = "https://registry.npmjs.org/" + row["name"] + "/-/" + row["name"].split("/")[-1] + f"-{row['version']}.tgz"
        expected_integrity = row["integrity"]
        archive_path = cache / f"npm-{package_key}{suffix}"
    else:
        package_key = _safe_id(row["id"])
        suffix = ".tar.gz"
        url = row["archive_url"]
        expected_integrity = None
        archive_path = cache / f"git-{package_key}{suffix}"

    if not _filesystem_path(archive_path).is_file():
        _filesystem_path(archive_path.parent).mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="vendor-source-", suffix=".tmp", dir=_filesystem_path(cache), delete=False) as temp:
            temp_path = Path(temp.name)
        try:
            last_error = None
            for attempt in range(3):
                try:
                    _fetch(url, temp_path)
                    last_error = None
                    break
                except (OSError, urllib.error.URLError) as error:
                    last_error = error
                    _filesystem_path(temp_path).unlink(missing_ok=True)
                    if attempt < 2:
                        time.sleep(1 + attempt)
                        _filesystem_path(temp_path).touch()
            if last_error is not None:
                raise last_error
            os.replace(_filesystem_path(temp_path), _filesystem_path(archive_path))
        except Exception:
            _filesystem_path(temp_path).unlink(missing_ok=True)
            raise

    if npm:
        actual = _sha512_sri(archive_path)
        if actual != expected_integrity:
            raise ValueError(f"npm tarball integrity mismatch for {row['name']}@{row['version']}: {actual}")
    else:
        actual_bytes = _filesystem_path(archive_path).stat().st_size
        actual_hash = _digest(archive_path, "sha256")
        if actual_bytes != row["archive_bytes"] or actual_hash != row["archive_sha256"]:
            raise ValueError(f"source archive identity mismatch for {row['id']}: {actual_bytes} {actual_hash}")
    return archive_path


def _safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if "\\" in name or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe archive member path: {name!r}")
    if any(":" in part for part in path.parts):
        raise ValueError(f"drive-qualified archive path: {name!r}")
    return path


def _extract(archive: Path, destination: Path | None, *, expected_root: str) -> list[dict]:
    if destination is not None:
        destination = _filesystem_path(destination)
        destination.mkdir(parents=True, exist_ok=False)
    inventory: list[dict] = []
    seen: set[str] = set()
    casefolded: set[str] = set()
    try:
        tf = tarfile.open(_filesystem_path(archive), mode="r:*")
    except tarfile.TarError as error:
        raise ValueError(f"not a readable tar archive: {archive}") from error
    with tf:
        members = tf.getmembers()
        by_member = {member.name: member for member in members}
        for member in members:
            path = _safe_member_path(member.name)
            if not path.parts or path.parts[0] != expected_root:
                raise ValueError(f"unexpected archive root in {archive.name}: {member.name}")
            relative_parts = path.parts[1:]
            if not relative_parts:
                continue
            relative = PurePosixPath(*relative_parts)
            relative_name = relative.as_posix()
            if relative_name in seen:
                raise ValueError(f"duplicate archive member: {relative_name}")
            if relative_name.casefold() in casefolded:
                raise ValueError(f"case-equivalent archive members are not portable: {relative_name}")
            seen.add(relative_name)
            casefolded.add(relative_name.casefold())
            target = destination.joinpath(*relative.parts) if destination is not None else None
            if member.isdir():
                if target is not None:
                    target.mkdir(parents=True, exist_ok=True)
                continue
            if member.issym() or member.islnk():
                link = PurePosixPath(member.linkname)
                if link.is_absolute() or any(part in {"", ".", ".."} for part in link.parts):
                    raise ValueError(f"unsafe archive link target: {member.name} -> {member.linkname}")
                link_path = link if member.islnk() else path.parent / link
                if link_path.parts[0] != expected_root:
                    link_path = PurePosixPath(expected_root, *link_path.parts)
                target_member = by_member.get(link_path.as_posix())
                if target_member is None or not target_member.isfile():
                    raise ValueError(f"archive link target is missing or not a regular file: {member.name} -> {member.linkname}")
                source = tf.extractfile(target_member)
            elif member.isfile():
                source = tf.extractfile(member)
            else:
                raise ValueError(f"special files are not accepted in vendor source archives: {member.name}")
            if source is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            if target is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
                file_bytes = target.stat().st_size
                file_hash = _digest(target, "sha256")
            else:
                hasher = hashlib.sha256()
                file_bytes = 0
                with source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        hasher.update(block)
                        file_bytes += len(block)
                file_hash = hasher.hexdigest()
            inventory.append({
                "path": relative_name,
                "bytes": file_bytes,
                "sha256": file_hash,
            })
    return sorted(inventory, key=lambda row: row["path"])


def _notice_files(package_root: Path, package_name: str = "") -> list[str]:
    names = ("license", "licence", "copying", "unlicense", "notice")
    found = []
    package_root_fs = _filesystem_path(package_root)
    for path in package_root_fs.rglob("*"):
        if path.is_file() and any(path.name.casefold().startswith(name) for name in names):
            found.append(path.relative_to(package_root_fs).as_posix())
    if package_name == "splaytree":
        readme = next((path for path in package_root_fs.iterdir() if path.is_file() and path.name.casefold() == "readme.md"), None)
        if readme is not None:
            found.append(readme.relative_to(package_root_fs).as_posix())
    return sorted(found)


def _jspdf_module_comments(package_root: Path) -> list[tuple[str, str]]:
    """Return license/attribution comment blocks mapped to jsPDF source files."""
    map_path = _filesystem_path(package_root / "dist" / "jspdf.umd.min.js.map")
    payload = json.loads(map_path.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    contents = payload.get("sourcesContent")
    if not isinstance(sources, list) or not isinstance(contents, list) or len(sources) != len(contents):
        raise ValueError("jsPDF source map must include aligned sources and sourcesContent")
    marker = re.compile(
        r"license|copyright|permission|redistribution|software license agreement|additional ip rights grant|no particular license",
        re.IGNORECASE,
    )
    comment_pattern = re.compile(r"/\*.*?\*/|^\s*//[^\n]*", re.DOTALL | re.MULTILINE)
    comments = []
    seen = set()
    for source, content in zip(sources, contents):
        if not isinstance(source, str) or not isinstance(content, str):
            continue
        for match in comment_pattern.finditer(content):
            comment = match.group(0).replace("\r\n", "\n").replace("\r", "\n").strip()
            if marker.search(comment):
                identity = (source, comment)
                if identity not in seen:
                    comments.append(identity)
                    seen.add(identity)
    if not comments:
        raise ValueError("no attributable jsPDF module comments found in pinned source map")
    return comments


def _write_notices(output: Path, lock: dict, npm_roots: dict[tuple[str, str], Path]) -> None:
    full_texts: dict[str, dict] = {}
    lines = [
        "# Third-party vendor source and notice index",
        "",
        "This index is generated from `vendor/source-lock.json` by `scripts/prepare-vendor-source.py`.",
        "Each npm package is pinned by registry SHA-512 integrity; each upstream repository archive is pinned by commit and SHA-256.",
        "The upstream source archives are provided for inspection and modification. Their presence does not claim that compiling their source reproduces the published npm bundle.",
        "",
        "## Package and bundled component notices",
        "",
        "| Component | Version | Declared license | Embedded in | Full package notices/source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in lock["npm_packages"]:
        key = (row["name"], row["version"])
        package_root = npm_roots[key]
        notices = _notice_files(package_root, row["name"])
        slug = _npm_slug(row["name"], row["version"])
        notice_links = [f"[`{p}`](npm/{slug}/{p})" for p in notices]
        if not notice_links:
            notice_links = [f"[`package.json`](npm/{slug}/package.json)"]
        embedded = "; ".join(row.get("embedded_in", []))
        for notice_path in notices:
            content = _filesystem_path(package_root / PurePosixPath(notice_path)).read_bytes()
            if row["name"] == "splaytree" and PurePosixPath(notice_path).name.casefold() == "readme.md":
                readme_text = content.decode("utf-8")
                marker = "The MIT License (MIT)"
                start = readme_text.find(marker)
                if start < 0:
                    raise ValueError("pinned splaytree README does not contain its declared MIT license text")
                content = readme_text[start:].encode("utf-8")
            digest = hashlib.sha256(content).hexdigest()
            record = full_texts.setdefault(digest, {
                "path": f"npm/{slug}/{notice_path}",
                "bytes": content,
                "packages": [],
            })
            record["packages"].append(f"{row['name']}@{row['version']}")
        lines.append(
            f"| `{row['name']}` | `{row['version']}` | {row.get('license', 'see package metadata')} | "
            f"{embedded} | {', '.join(notice_links)} |"
        )
    lines += [
        "",
        "## jsPDF module-level attribution and license comments",
        "",
        "The following comment blocks are copied from the source files identified by the pinned jsPDF 4.2.1 npm source map. They are reproduced as notices, without treating informal or unspecified statements as a license grant.",
        "",
    ]
    jspdf_root = npm_roots[("jspdf", "4.2.1")]
    for source, comment in _jspdf_module_comments(jspdf_root):
        fence = "`" * max(3, max((len(match.group(0)) for match in re.finditer(r"`+", comment)), default=0) + 1)
        lines += [f"### `{source}`", "", fence + "text", comment, fence, ""]
    lines += [
        "## Font terms",
        "",
        "The DejaVu font source repository and its license are included. The shipped four TTF files were copied from Matplotlib 3.10.9 `mpl-data/fonts/ttf`; the source repository is not claimed to regenerate the exact TTF bytes. The DejaVu/Bitstream Vera/Arev terms remain separately applicable.",
        "",
        "## Coverage boundary",
        "",
        "The package set reflects code identified in the vendored runtime bundles and their source maps, plus each direct npm distribution. It excludes development-only, optional runtime, and platform-specific dependencies unless the listed bundle source maps show their code embedded. Re-audit when vendor versions or bundle bytes change.",
        "",
        "## Full package license and notice texts",
        "",
        "The texts below are copied verbatim from the pinned npm package archives. Their original files remain in the extracted package trees above.",
        "",
    ]
    for digest, record in sorted(full_texts.items(), key=lambda item: item[1]["path"]):
        references = ", ".join(f"`{package}`" for package in sorted(set(record["packages"])))
        lines += [
            f"### `{record['path']}`",
            "",
            f"SHA-256 `{digest}`; {references}.",
            "",
            "```text",
            record["bytes"].decode("utf-8", errors="replace").rstrip(),
            "```",
            "",
        ]
    _filesystem_path(output / "THIRD_PARTY_NOTICES.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _prepare(repository_root: Path, output: Path, cache: Path) -> None:
    lock, raw_lock = _load_lock(repository_root)
    output_fs = _filesystem_path(output)
    if output_fs.exists():
        raise ValueError(f"output already exists: {output}")
    output_fs.parent.mkdir(parents=True, exist_ok=True)
    _filesystem_path(cache).mkdir(parents=True, exist_ok=True)
    output_fs.mkdir()
    repositories_root = output_fs / "repositories"
    npm_root = output_fs / "npm"
    archives_root = output_fs / "archives"
    repositories_root.mkdir()
    npm_root.mkdir()
    (archives_root / "repositories").mkdir(parents=True)
    (archives_root / "npm").mkdir(parents=True)
    artifacts = []
    npm_roots: dict[tuple[str, str], Path] = {}

    for row in lock["source_packages"]:
        _validate_archive_row(row, npm=False)
        archive = _get_archive(row, cache, npm=False)
        archive_output = archives_root / "repositories" / archive.name
        shutil.copyfile(_filesystem_path(archive), _filesystem_path(archive_output))
        dest = repositories_root / _safe_id(row["id"])
        file_inventory = _extract(archive, dest, expected_root=row["archive_root"])
        artifacts.append({
            "kind": "repository-source",
            "id": row["id"],
            "name": row["name"],
            "version": row["version"],
            "repository": row["repository"],
            "commit": row["commit"],
            "archive_url": row["archive_url"],
            "archive_bytes": row["archive_bytes"],
            "archive_sha256": row["archive_sha256"],
            "archive_root": row["archive_root"],
            "archive_path": f"archives/repositories/{archive.name}",
            "extracted_path": f"repositories/{_safe_id(row['id'])}",
            "files": file_inventory,
        })

    for row in lock["npm_packages"]:
        _validate_archive_row(row, npm=True)
        archive = _get_archive(row, cache, npm=True)
        slug = _npm_slug(row["name"], row["version"])
        archive_output = archives_root / "npm" / archive.name
        shutil.copyfile(_filesystem_path(archive), _filesystem_path(archive_output))
        dest = npm_root / slug
        file_inventory = _extract(archive, dest, expected_root="package")
        npm_roots[(row["name"], row["version"])] = dest
        artifacts.append({
            "kind": "npm-distribution-and-source-map",
            "name": row["name"],
            "version": row["version"],
            "url": "https://registry.npmjs.org/" + row["name"] + "/-/" + row["name"].split("/")[-1] + f"-{row['version']}.tgz",
            "integrity": row["integrity"],
            "archive_path": f"archives/npm/{archive.name}",
            "license": row.get("license"),
            "extracted_path": f"npm/{slug}",
            "files": file_inventory,
        })

    _write_notices(output, lock, npm_roots)
    readme = (
        "# Vendor source materials\n\n"
        "This directory contains upstream source archives and extracted editable trees. Repository snapshots are pinned to Git commits and SHA-256; exact npm package distributions are pinned by SHA-512 integrity. "
        "Repository snapshots include the original project build files; npm packages preserve the published distribution, source maps, package metadata, and license files.\n\n"
        "The existence of source and build files does not mean an upstream build was reproduced. Exact npm bundle identity is checked separately where the vendor manifest records a byte receipt. "
        "The locally patched svg2pdf runtime is reconstructed from the exact upstream npm bundle by `scripts/rebuild-svg2pdf-vendor.py`; that check proves byte-level patch reconstruction, not upstream compilation from source.\n\n"
        "Run `python scripts/prepare-vendor-source.py --verify <this-directory>` to check the extracted file inventories against `source-index.json`. "
        "The lock is `vendor/source-lock.json` in the source tree.\n"
    )
    _filesystem_path(output_fs / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    generated_files = []
    for name in ("README.md", "THIRD_PARTY_NOTICES.md"):
        generated = output_fs / name
        generated_files.append({
            "path": name,
            "bytes": _filesystem_path(generated).stat().st_size,
            "sha256": _digest(generated, "sha256"),
        })
    index = {
        "schema": INDEX_SCHEMA,
        "source_lock_path": "vendor/source-lock.json",
        "source_lock_sha256": hashlib.sha256(raw_lock).hexdigest(),
        "generated_files": generated_files,
        "artifacts": sorted(artifacts, key=lambda item: (item["kind"], item.get("id", item.get("name", "")), item["version"])),
    }
    _filesystem_path(output_fs / "source-index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _verify(repository_root: Path, output: Path) -> None:
    lock, raw_lock = _load_lock(repository_root)
    output = _filesystem_path(output)
    if output.is_symlink() or not output.is_dir():
        raise ValueError(f"source material root is missing or is a symlink: {output}")
    index_path = output / "source-index.json"
    if not index_path.is_file():
        raise ValueError(f"source index is missing: {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("schema") != INDEX_SCHEMA or index.get("source_lock_sha256") != hashlib.sha256(raw_lock).hexdigest():
        raise ValueError("source index does not match the source lock")
    artifacts = index.get("artifacts")
    if not isinstance(artifacts, list) or any(not isinstance(a, dict) for a in artifacts):
        raise ValueError("source index artifacts must be a list of objects")
    expected = {(a["kind"], a.get("id", a.get("name")), a["version"]): a for a in artifacts}
    lock_expected = {("repository-source", row["id"], row["version"]) for row in lock["source_packages"]}
    lock_expected |= {("npm-distribution-and-source-map", row["name"], row["version"]) for row in lock["npm_packages"]}
    if set(expected) != lock_expected:
        raise ValueError("source index artifact set does not match the source lock")
    for row in lock["source_packages"]:
        artifact = expected[("repository-source", row["id"], row["version"])]
        if any(artifact.get(key) != row[key] for key in ("commit", "archive_url", "archive_bytes", "archive_sha256", "archive_root")):
            raise ValueError(f"source index repository identity differs from lock: {row['id']}")
        if artifact.get("extracted_path") != f"repositories/{_safe_id(row['id'])}":
            raise ValueError(f"source index repository path differs from lock: {row['id']}")
        if artifact.get("archive_path") != f"archives/repositories/git-{_safe_id(row['id'])}.tar.gz":
            raise ValueError(f"source index repository archive path differs from lock: {row['id']}")
    for row in lock["npm_packages"]:
        artifact = expected[("npm-distribution-and-source-map", row["name"], row["version"])]
        if artifact.get("integrity") != row["integrity"] or artifact.get("license") != row.get("license"):
            raise ValueError(f"source index npm identity differs from lock: {row['name']}@{row['version']}")
        slug = _npm_slug(row["name"], row["version"])
        archive_slug = _safe_id(f"{row['name']}@{row['version']}")
        if artifact.get("extracted_path") != f"npm/{slug}":
            raise ValueError(f"source index npm path differs from lock: {row['name']}@{row['version']}")
        if artifact.get("archive_path") != f"archives/npm/npm-{archive_slug}.tgz":
            raise ValueError(f"source index npm archive path differs from lock: {row['name']}@{row['version']}")
    indexed_paths = {"source-index.json"}
    generated_files = index.get("generated_files")
    if not isinstance(generated_files, list):
        raise ValueError("source index generated_files must be a list")
    generated_map = {}
    for record in generated_files:
        if not isinstance(record, dict) or record.get("path") not in {"README.md", "THIRD_PARTY_NOTICES.md"}:
            raise ValueError("source index generated file record is malformed")
        if record["path"] in generated_map:
            raise ValueError(f"duplicate generated source document: {record['path']}")
        if not isinstance(record.get("bytes"), int) or record["bytes"] < 0 or not HEX.fullmatch(str(record.get("sha256", ""))):
            raise ValueError(f"invalid generated source document identity: {record['path']}")
        generated_map[record["path"]] = record
        path = output / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or _digest(path, "sha256") != record["sha256"]:
            raise ValueError(f"generated source document identity mismatch: {record['path']}")
        indexed_paths.add(record["path"])
    if set(generated_map) != {"README.md", "THIRD_PARTY_NOTICES.md"}:
        raise ValueError("source index must identify README.md and THIRD_PARTY_NOTICES.md")
    for artifact in expected.values():
        if artifact["kind"] == "repository-source":
            source_row = next(row for row in lock["source_packages"] if row["id"] == artifact["id"])
            prefix = f"git-{_safe_id(source_row['id'])}.tar.gz"
            if artifact.get("archive_path") != f"archives/repositories/{prefix}":
                raise ValueError(f"source archive path differs from lock: {artifact['id']}")
        else:
            npm_row = next(row for row in lock["npm_packages"] if row["name"] == artifact["name"] and row["version"] == artifact["version"])
            slug = _npm_slug(npm_row["name"], npm_row["version"])
            archive_slug = _safe_id(f"{npm_row['name']}@{npm_row['version']}")
            if artifact.get("archive_path") != f"archives/npm/npm-{archive_slug}.tgz":
                raise ValueError(f"npm source archive path differs from lock: {artifact['name']}@{artifact['version']}")
        archive = output / artifact["archive_path"]
        if not archive.is_file():
            raise ValueError(f"source archive is missing: {artifact['archive_path']}")
        indexed_paths.add(artifact["archive_path"])
        if artifact["kind"] == "repository-source":
            if archive.stat().st_size != artifact["archive_bytes"] or _digest(archive, "sha256") != artifact["archive_sha256"]:
                raise ValueError(f"source archive identity mismatch: {artifact['id']}")
        elif _sha512_sri(archive) != artifact["integrity"]:
            raise ValueError(f"npm source archive integrity mismatch: {artifact['name']}@{artifact['version']}")
        base = output / artifact["extracted_path"]
        file_rows = artifact.get("files")
        if not isinstance(file_rows, list) or any(not isinstance(row, dict) for row in file_rows):
            raise ValueError(f"source file index is malformed: {artifact['extracted_path']}")
        expected_files = {}
        casefolded_files = set()
        for row in file_rows:
            relative = row.get("path")
            if not isinstance(relative, str) or _safe_member_path(relative).as_posix() != relative:
                raise ValueError(f"unsafe indexed source file path: {relative!r}")
            if relative in expected_files:
                raise ValueError(f"duplicate indexed source file: {relative}")
            if relative.casefold() in casefolded_files:
                raise ValueError(f"case-equivalent indexed source files: {relative}")
            if not isinstance(row.get("bytes"), int) or row["bytes"] < 0 or not HEX.fullmatch(str(row.get("sha256", ""))):
                raise ValueError(f"invalid indexed source file identity: {artifact['extracted_path']}/{relative}")
            expected_files[relative] = row
            casefolded_files.add(relative.casefold())
        actual_files = {
            path.relative_to(base).as_posix()
            for path in base.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        if actual_files != set(expected_files):
            missing = sorted(set(expected_files) - actual_files)
            extra = sorted(actual_files - set(expected_files))
            raise ValueError(f"extracted file set differs at {artifact['extracted_path']}: missing={missing[:5]} extra={extra[:5]}")
        for relative, record in expected_files.items():
            path = base / PurePosixPath(relative)
            if path.is_symlink() or path.stat().st_size != record["bytes"] or _digest(path, "sha256") != record["sha256"]:
                raise ValueError(f"source file identity mismatch: {artifact['extracted_path']}/{relative}")
        archive_root = artifact.get("archive_root", "package")
        archive_files = _extract(archive, None, expected_root=archive_root)
        if archive_files != sorted(file_rows, key=lambda row: row["path"]):
            raise ValueError(f"extracted source index does not match pinned archive contents: {artifact['extracted_path']}")
        indexed_paths.update(f"{artifact['extracted_path']}/{relative}" for relative in expected_files)
    expected_root_files = {"source-index.json", "README.md", "THIRD_PARTY_NOTICES.md"}
    actual_root_files = {p.name for p in output.iterdir() if p.is_file()}
    if actual_root_files != expected_root_files:
        raise ValueError(f"unexpected source material root files: {sorted(actual_root_files)}")
    actual_dirs = {p.relative_to(output).as_posix() for p in output.iterdir() if p.is_dir()}
    if actual_dirs != {"repositories", "npm", "archives"}:
        raise ValueError(f"unexpected source material directories: {sorted(actual_dirs)}")
    if any(path.is_symlink() for path in output.rglob("*")):
        raise ValueError("source materials contain a symlink")
    actual_files = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    if actual_files != indexed_paths:
        missing = sorted(indexed_paths - actual_files)
        extra = sorted(actual_files - indexed_paths)
        raise ValueError(f"source material file set differs from index: missing={missing[:5]} extra={extra[:5]}")
    print(f"Vendor source materials verified: {len(expected)} pinned artifacts")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch and verify exact upstream source for vendored Figure Tool dependencies.")
    parser.add_argument("--repository-root", type=Path, default=ROOT, help="Repository root containing vendor/source-lock.json")
    parser.add_argument("--output", type=Path, help="New output directory for extracted source materials")
    parser.add_argument("--cache-dir", type=Path, help="Archive cache; defaults to qa_artifacts/vendor-source-cache")
    parser.add_argument("--verify", type=Path, help="Verify an already prepared source materials directory without network access")
    args = parser.parse_args(argv)
    repository_root = args.repository_root.resolve()
    if args.output and args.verify:
        parser.error("choose --output or --verify")
    if args.verify:
        _verify(repository_root, _absolute_path(args.verify))
        return 0
    if not args.output:
        parser.error("--output is required unless --verify is used")
    cache = _absolute_path(args.cache_dir) if args.cache_dir else repository_root / "qa_artifacts" / "vendor-source-cache"
    try:
        output = _absolute_path(args.output)
        _prepare(repository_root, output, cache)
    except (OSError, ValueError, json.JSONDecodeError, tarfile.TarError) as error:
        print(f"vendor source preparation failed: {error}", file=sys.stderr)
        return 1
    print(f"Vendor source materials prepared at {_absolute_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
