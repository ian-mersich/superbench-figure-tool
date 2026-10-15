from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping

try:
    from scripts.windows_suite_json import load_json_strict
except ModuleNotFoundError:  # Direct execution adds scripts/ rather than the repository root.
    from windows_suite_json import load_json_strict  # type: ignore[no-redef]


FIGURE_STUDIO_CORE_SCHEMA = "figureStudio.coreBundleIdentity.v1"
FIGURE_STUDIO_CORE_ROOTS = (
    "app",
    "vendor",
    "assets/scientific-packs",
    "assets/scientific-scenes",
)
CANONICAL_PACKAGE_NAME = "@superbench/figure-tool"
LEGACY_PACKAGE_IDENTITIES = {("@bsd-studio/figure-studio", "1.0.0-beta.3")}


@dataclass(frozen=True)
class FigureStudioCoreFile:
    relative_path: str
    size: int
    sha256: str
    source_path: Path


@dataclass(frozen=True)
class FigureStudioCoreSnapshot:
    source_root: Path
    files: tuple[FigureStudioCoreFile, ...]
    identity: dict[str, object]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _core_version(source_root: Path) -> str:
    package_path = source_root / "package.json"
    if not package_path.is_file():
        raise FileNotFoundError(f"Figure Studio package metadata is missing: {package_path}")
    package = load_json_strict(package_path)
    version = str(package.get("version") or "").strip()
    if (package.get("name") != CANONICAL_PACKAGE_NAME and (package.get("name"), version) not in LEGACY_PACKAGE_IDENTITIES) or not version:
        raise ValueError(
            "Figure Studio package metadata does not define the canonical core version"
        )
    return version


def capture_figure_studio_core(
    source_root: Path,
    *,
    core_version: str | None = None,
) -> FigureStudioCoreSnapshot:
    """Capture the one canonical Figure Studio editor/runtime bundle identity."""

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"Figure Studio core root is missing: {source_root}")

    files: list[FigureStudioCoreFile] = []
    folded_paths: set[str] = set()
    for relative_root in FIGURE_STUDIO_CORE_ROOTS:
        root = source_root / Path(*relative_root.split("/"))
        if not root.is_dir():
            raise FileNotFoundError(f"Figure Studio core directory is missing: {root}")
        root_file_count = 0
        for candidate in sorted(
            root.rglob("*"), key=lambda value: value.as_posix().casefold()
        ):
            if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
                raise ValueError(
                    f"Links and junctions are forbidden in the Figure Studio core: {candidate}"
                )
            if not candidate.is_file():
                continue
            try:
                relative = candidate.resolve().relative_to(source_root).as_posix()
            except ValueError as exc:
                raise ValueError(
                    f"Figure Studio core file escaped its source root: {candidate}"
                ) from exc
            folded = relative.casefold()
            if folded in folded_paths:
                raise ValueError(
                    f"Case-insensitive Figure Studio core path collision: {relative}"
                )
            folded_paths.add(folded)
            payload = candidate.read_bytes()
            files.append(
                FigureStudioCoreFile(
                    relative_path=relative,
                    size=len(payload),
                    sha256=_sha256_bytes(payload),
                    source_path=candidate,
                )
            )
            root_file_count += 1
        if root_file_count == 0:
            raise ValueError(f"Figure Studio core directory is empty: {relative_root}")

    files.sort(key=lambda entry: entry.relative_path.casefold())
    version = str(core_version or "").strip() or _core_version(source_root)
    tree_basis = "".join(
        f"{entry.relative_path}\0{entry.sha256}\n" for entry in files
    ).encode("utf-8")
    identity: dict[str, object] = {
        "schema": FIGURE_STUDIO_CORE_SCHEMA,
        "core_version": version,
        "included_roots": list(FIGURE_STUDIO_CORE_ROOTS),
        "file_count": len(files),
        "total_bytes": sum(entry.size for entry in files),
        "tree_sha256": _sha256_bytes(tree_basis),
    }
    return FigureStudioCoreSnapshot(source_root=source_root, files=tuple(files), identity=identity)


def verify_figure_studio_core(
    staged_root: Path,
    expected_identity: Mapping[str, object],
) -> dict[str, object]:
    """Fail unless a staged core is byte-for-byte identical to the canonical snapshot."""

    version = str(expected_identity.get("core_version") or "").strip()
    if not version:
        raise ValueError("Expected Figure Studio core identity has no core version")
    observed = capture_figure_studio_core(staged_root, core_version=version).identity
    expected = dict(expected_identity)
    if observed != expected:
        differing = sorted(
            key for key in set(expected) | set(observed) if expected.get(key) != observed.get(key)
        )
        raise ValueError(
            "Staged Figure Studio core differs from the canonical source identity: "
            + ", ".join(differing)
        )
    return observed


def copy_figure_studio_core(
    snapshot: FigureStudioCoreSnapshot,
    destination_root: Path,
) -> dict[str, object]:
    """Copy a captured core and immediately verify the complete staged tree."""

    destination_root = destination_root.resolve()
    for entry in snapshot.files:
        payload = entry.source_path.read_bytes()
        if len(payload) != entry.size or _sha256_bytes(payload) != entry.sha256:
            raise ValueError(
                "Canonical Figure Studio core changed while staging: " + entry.relative_path
            )
        destination = destination_root / Path(*entry.relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    return verify_figure_studio_core(destination_root, snapshot.identity)
