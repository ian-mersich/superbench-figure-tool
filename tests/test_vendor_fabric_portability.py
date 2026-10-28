"""Regression tests for the exact reviewed Fabric Git/archive identities."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_vendor_bundle", ROOT / "scripts/validate-vendor-bundle.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def _copy_vendor(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(ROOT / "vendor", root / "vendor")
    for relative in ("NOTICE", "app/legal/NOTICE"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return root


def test_vendor_validator_accepts_current_working_vendor_bytes(tmp_path: Path) -> None:
    root = _copy_vendor(tmp_path)
    validator.validate(root)


def test_git_archive_preserves_hashed_pdfium_provenance(tmp_path: Path) -> None:
    from scripts.figure_tool_package_producer import extract_git_archive

    relative = "vendor/pdfium/PROVENANCE.json"
    manifest = json.loads((ROOT / "vendor/manifest.json").read_text(encoding="utf-8"))
    entry = next(row for row in manifest["native_artifact_files"] if row["path"] == relative)
    retained = validator._validate_file_identity(ROOT, relative, entry)
    repository = tmp_path / "source"
    target = repository / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(retained)
    shutil.copyfile(ROOT / ".gitattributes", repository / ".gitattributes")
    hooks = tmp_path / "no-hooks"
    hooks.mkdir()

    def git(*arguments: str) -> bytes:
        return subprocess.check_output(
            ["git", "-C", str(repository), "-c", "core.autocrlf=true",
             "-c", f"core.hooksPath={hooks}", "-c", "commit.gpgSign=false", *arguments],
            stderr=subprocess.PIPE,
        )

    git("init", "--quiet")
    git("add", "--", ".gitattributes", relative)
    git("-c", "user.name=Figure provenance test", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "-m", "Exact provenance fixture")
    commit = git("rev-parse", "HEAD").decode("ascii").strip()
    archived = extract_git_archive(repository, commit, tmp_path / "archived")
    assert validator._validate_file_identity(archived, relative, entry) == retained

    # The historical record's raw-byte binding remains strict. Arbitrary
    # normalization must not inherit its accepted digest or change its meaning.
    normalized = retained.replace(b"\r\n", b"\n")
    assert normalized != retained
    (archived / relative).write_bytes(normalized)
    with pytest.raises(SystemExit, match="byte count mismatch|sha256 mismatch"):
        validator._validate_file_identity(archived, relative, entry)


def test_vendor_validator_accepts_only_exact_reviewed_crlf_materialization(tmp_path: Path) -> None:
    root = _copy_vendor(tmp_path)
    runtime = root / "vendor/fabric/index.min.js"
    runtime.write_bytes(runtime.read_bytes().replace(b"\n", b"\r\n"))
    validator.validate(root)


def test_vendor_validator_rejects_changed_fabric_bytes(tmp_path: Path) -> None:
    root = _copy_vendor(tmp_path)
    runtime = root / "vendor/fabric/index.min.js"
    runtime.write_bytes(runtime.read_bytes() + b"\n")
    with pytest.raises(SystemExit, match="byte count mismatch|sha256 mismatch"):
        validator.validate(root)


@pytest.mark.parametrize("relative", ["NOTICE", "app/legal/NOTICE"])
def test_vendor_validator_rejects_mismatched_native_notices(tmp_path: Path, relative: str) -> None:
    root = _copy_vendor(tmp_path)
    (root / relative).write_text("First-party terms without native runtime credits.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="Root/app first-party notices must match"):
        validator.validate(root)


def test_vendor_validator_rejects_matching_notices_without_native_credits(tmp_path: Path) -> None:
    root = _copy_vendor(tmp_path)
    for relative in ("NOTICE", "app/legal/NOTICE"):
        (root / relative).write_text("Matching first-party terms without native runtime credits.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="FreeType|IJG|acknowledgement"):
        validator.validate(root)


def test_vendor_validator_rejects_changed_upstream_identity_metadata(tmp_path: Path) -> None:
    root = _copy_vendor(tmp_path)
    manifest_path = root / "vendor/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fabric = next(row for row in manifest["runtime_files"] if row.get("package") == "fabric")
    fabric["upstream_lf_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SystemExit, match="byte count mismatch|sha256 mismatch|upstream_lf_sha256"):
        validator.validate(root)


def test_reviewed_fabric_identity_helper_rejects_arbitrary_normalization() -> None:
    receipt = validator.FABRIC_SOURCE_RECEIPT
    lf = b"line one\nline two\n"
    crlf = lf.replace(b"\n", b"\r\n")
    assert validator._matches_reviewed_fabric_bytes(
        lf,
        materialized_bytes=298_695,
        materialized_sha256="6aa6f34043486b265c89347f59df9f1c28489269694bd93f6a4915b77e811bfe",
        upstream_lf_bytes=receipt["upstream_runtime_bytes"],
        upstream_lf_sha256=receipt["upstream_runtime_sha256"],
    ) is None  # different bytes cannot inherit the audited identity
    assert validator._matches_reviewed_fabric_bytes(
        lf,
        materialized_bytes=len(lf),
        materialized_sha256=validator._sha256_bytes(lf),
        upstream_lf_bytes=298_256,
        upstream_lf_sha256=receipt["upstream_runtime_sha256"],
    ) == "windows-materialization"
    assert validator._matches_reviewed_fabric_bytes(
        crlf,
        materialized_bytes=len(crlf),
        materialized_sha256=validator._sha256_bytes(crlf),
        upstream_lf_bytes=298_256,
        upstream_lf_sha256=receipt["upstream_runtime_sha256"],
    ) == "windows-materialization"
