"""Regression tests for the exact reviewed Fabric Git/archive identities."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_vendor_bundle", ROOT / "scripts/validate-vendor-bundle.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def _copy_vendor(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(ROOT / "vendor", root / "vendor")
    return root


def test_vendor_validator_accepts_exact_upstream_lf_git_archive(tmp_path: Path) -> None:
    root = _copy_vendor(tmp_path)
    validator.validate(root)


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
