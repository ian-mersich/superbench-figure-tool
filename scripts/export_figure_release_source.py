"""Export source beside the producer's unchanged shared payload, without pruning.

Called inside the producer's one committed-source snapshot. Preferred upstream
sources are included only in the full source ZIP, never the web/native payload.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import zipfile

SUPPORT_FILES = (
    "LICENSE", "NOTICE", "LICENSE_POLICY.md", "package.json", "requirements-release.txt", ".gitattributes",
    "assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md", "assets/CC0-1.0.txt",
    "assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md", "assets/LICENSE-STYLE-4-CC0-1.0.md",
    "config/scientific-product-release-2026-10-15.json",
    "config/scientific-product-release-2026-10-15-expansion.json",
    "config/scientific-product-release-2026-10-17-style4.json",
    "config/scientific-product-release-2026-10-17-style4-correction.json",
    "scripts/import-style4-correction.py", "scripts/test-style4-correction.py",
    "tests/test_scientific_product_correction.py",
    "scripts/import-style4-library.py", "scripts/validate-style4-library.py",
    "scripts/test-style4-library-import.py", "tests/scientificAssetStyleFour.test.mjs", "tests/scientificAssetPrewarmStyle.test.cjs",
    "scripts/figure_tool_package_producer.py", "scripts/scientific_product_release.py",
    "scripts/scientific_family_revision.py", "scripts/export_figure_release_source.py",
    "scripts/check_figure_release_sync.py", "tests/test_figure_release_sync.py",
    "scripts/figure_studio_core_bundle.py", "scripts/windows_suite_json.py",
    "scripts/validate-scientific-assets.py", "scripts/validate-vendor-bundle.py",
    "scripts/prepare-vendor-source.py", "scripts/rebuild-svg2pdf-vendor.py",
    "scripts/build-pdfium-factory.py", "scripts/pdfium-factory/factory-prefix.js.txt",
    "scripts/pdfium-factory/factory-suffix.js.txt",
    "scripts/build-vendor-notice.py", "scripts/generate-scientific-asset-license-audit.py",
    "scripts/seed-cell-structure-stress-assets.py", "scripts/cell_structure_stress_renderers.py",
    "scripts/cell_structure_stress_science.json", "scripts/seed-tumor-analysis-assets.py",
    "tests/test_figure_tool_package_producer.py", "tests/test_scientific_product_release.py",
    "tests/test_export_figure_release_source.py",
    "tests/test_cell_structure_stress_assets.py", "tests/test_tumor_analysis_assets.py",
    "tests/test_scientific_contribution_policy.py",
    "tests/test_vendor_fabric_portability.py", "tests/test_vendor_source_tools.py",
    "docs/UNIFIED_FIGURE_RELEASE.md",
    "docs/architecture/FIGURE_HOST_SETTINGS.md",
    "docs/architecture/FIGURE_DRAWING_CHANGES.md",
)


def filesystem(path: Path) -> Path:
    if os.name != "nt":
        return path
    value = str(path.absolute())
    return Path(value if value.startswith("\\\\?\\") else "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with filesystem(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_vendor_materials(source: Path, destination: Path, cache: Path) -> dict:
    subprocess.run([sys.executable, str(source / "scripts/build-pdfium-factory.py"), "--check"],
                   cwd=source, check=True, capture_output=True)
    subprocess.run([sys.executable, str(source / "scripts/prepare-vendor-source.py"), "--repository-root", str(source),
                    "--output", str(destination), "--cache-dir", str(cache)], cwd=source, check=True, capture_output=True)
    subprocess.run([sys.executable, str(source / "scripts/prepare-vendor-source.py"), "--repository-root", str(source),
                    "--verify", str(destination)], cwd=source, check=True, capture_output=True)
    notice_tools = runpy.run_path(str(source / "scripts/build-vendor-notice.py"))
    renderer = notice_tools["render_notice"]
    expected = renderer((filesystem(destination) / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"),
                        (source / "vendor/licenses/dejavu-sans-LICENSE.txt").read_text(encoding="utf-8"),
                        notice_tools["native_notice_section"](source))
    if (source / "vendor/NOTICE").read_bytes() != expected.encode("utf-8"):
        raise ValueError("Verified preferred-source terms differ from the shipped vendor notice")
    subprocess.run([sys.executable, str(source / "scripts/rebuild-svg2pdf-vendor.py"), "--repository-root", str(source),
                    "--upstream", str(destination / "npm/svg2pdf.js@2.7.0/dist/svg2pdf.umd.min.js"), "--check"],
                   cwd=source, check=True, capture_output=True)
    return {"status": "included-and-verified", "index": "preferred-source-materials/source-index.json",
            "index_sha256": sha(destination / "source-index.json"), "upstream_compiler_rebuild_qualified": False}


def verify_payload(tree: Path, manifest: dict) -> None:
    expected = {row["path"]: row for row in manifest["payload_files"]}
    roots = ("app", "vendor", "web", "assets/scientific-packs", "assets/scientific-scenes")
    actual = {path.relative_to(tree).as_posix() for relative in roots for path in (tree / relative).rglob("*") if path.is_file()}
    if actual != set(expected):
        raise ValueError("Public source export changed the shared payload inventory")
    for relative, row in expected.items():
        if (tree / relative).stat().st_size != row["size"] or sha(tree / relative) != row["sha256"]:
            raise ValueError("Public source export changed shared payload bytes: " + relative)


def export_source(source: Path, package: Path, output: Path, *, cache: Path) -> dict:
    manifest = json.loads((package / "tool-package.json").read_text(encoding="utf-8"))
    if (manifest.get("source_provenance", {}).get("distribution_scope") != "public-release"
            or manifest["source_provenance"].get("public_release_eligible") is not True):
        raise ValueError("Public source export requires qualified public-release provenance")
    version, revision, digest = manifest["version"], manifest["source_provenance"]["source_revision"], manifest["package_sha256"]
    repository = output / "source-repository"
    if repository.exists():
        raise ValueError("Source export already exists")
    shutil.copytree(filesystem(package / "payload"), filesystem(repository))
    for relative in SUPPORT_FILES:
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    # Accepted provenance notes stay available with their asset records. No QA,
    # private history, manuscripts, browser profiles or user projects are copied.
    shutil.copytree(source / "docs/scientific-assets", repository / "docs/scientific-assets")
    metadata = {
        "schema": "figureStudio.publicSourceRelease.v2", "product_version": version,
        "tag": "v" + version, "canonical_source_revision": revision, "package_sha256": digest,
        "shared_payload_tree_sha256": manifest["tree_sha256"], "published": False,
        "source_archive": "figure-tool-source.zip", "web_archive": "figure-tool-web.zip",
        "vendor_source_materials": {"status": "fetch-and-verify-from-lock", "lock": "vendor/source-lock.json",
                                    "instructions": "vendor/SOURCE_MATERIALS.md"},
    }
    (repository / "SOURCE_RELEASE.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    exported_library = json.loads((source / "assets/scientific-packs/library.json").read_text(encoding="utf-8"))
    drawing_count = sum(row["asset_count"] for row in exported_library["packs"])
    concept_count = sum(row["concept_count"] for row in exported_library["packs"])
    (repository / "README.md").write_text(
        "# Superbench Figure Tool\n\nCreate editable scientific figures and presentations. "
        "[Open the browser editor](https://imersich.com/superbench/figure_tool/).\n\n"
        f"This is {version}. The browser and Superbench packages use the same app, styles, vendors, "
        f"{drawing_count} Library drawings "
        f"({concept_count} concepts), and 12 scientific scenes. SOURCE_RELEASE.json binds this export "
        "to their committed source and shared payload. Installed native-host qualification is separate.\n\n"
        "Serve this directory over HTTP and open `web/`. Work stays in the current browser profile; download "
        "portable files for backups. First-party code is Apache-2.0 and original artwork is CC0-1.0. "
        "See LICENSE, NOTICE, LICENSE_POLICY.md, assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md, "
        "assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md and vendor/NOTICE.\n\n"
        "The full release source ZIP includes verified preferred upstream sources under preferred-source-materials/. "
        "This slim Git export retains the same lock, complete notices, and fetch/verify instructions in "
        "vendor/SOURCE_MATERIALS.md. Fresh upstream compiler rebuilds are not qualified as byte-identical.\n\n"
        "Run `python scripts/validate-scientific-assets.py --library --require-public-release`, "
        "`python scripts/validate-vendor-bundle.py`, and "
        "`python -m pytest tests/test_figure_tool_package_producer.py tests/test_scientific_product_release.py "
        "tests/test_export_figure_release_source.py tests/test_vendor_source_tools.py tests/test_vendor_fabric_portability.py`. "
        "See docs/UNIFIED_FIGURE_RELEASE.md for packaging and deployment.\n", encoding="utf-8", newline="\n")
    (repository / ".gitignore").write_text("qa_artifacts/\nnode_modules/\n__pycache__/\n.pytest_cache/\n*.py[cod]\n", encoding="utf-8", newline="\n")
    workflow = repository / ".github/workflows/source-ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("""name: Figure source validation
on: [push, pull_request, workflow_dispatch]
permissions:
  contents: read
jobs:
  validate:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: '3.12'
      - run: python -m pip install -r requirements-release.txt
      - run: python scripts/validate-scientific-assets.py --library --require-public-release
      - run: python scripts/validate-vendor-bundle.py
      - run: python -m pytest -q tests/test_figure_tool_package_producer.py tests/test_scientific_product_release.py tests/test_export_figure_release_source.py tests/test_vendor_source_tools.py tests/test_vendor_fabric_portability.py
""", encoding="utf-8", newline="\n")
    verify_payload(repository, manifest)
    materials = output / "preferred-source-materials"
    preferred = prepare_vendor_materials(source, materials, cache)
    archive_path = output / "figure-tool-source.zip"
    full_metadata = {**metadata, "vendor_source_materials": preferred}
    members = {path.relative_to(repository).as_posix(): path for path in repository.rglob("*") if path.is_file()}
    members.update({"preferred-source-materials/" + path.relative_to(filesystem(materials)).as_posix(): path
                    for path in filesystem(materials).rglob("*") if path.is_file()})
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, path in sorted(members.items()):
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type, info.create_system, info.external_attr = zipfile.ZIP_DEFLATED, 3, 0o100644 << 16
            with archive.open(info, "w", force_zip64=True) as target:
                if relative == "SOURCE_RELEASE.json":
                    target.write((json.dumps(full_metadata, indent=2) + "\n").encode("utf-8"))
                else:
                    with filesystem(path).open("rb") as original:
                        shutil.copyfileobj(original, target, 1024 * 1024)
    with zipfile.ZipFile(archive_path) as archive:
        for row in manifest["payload_files"]:
            if hashlib.sha256(archive.read(row["path"])).hexdigest() != row["sha256"]:
                raise ValueError("Full source ZIP changed shared runtime: " + row["path"])
    return {"repository": "source-repository", "archive": archive_path.name, "archive_sha256": sha(archive_path),
            "archive_size": archive_path.stat().st_size, "shared_payload_files": len(manifest["payload_files"]),
            "shared_payload_parity": "passed", "vendor_source_materials": preferred,
            "support_files": list(SUPPORT_FILES), "scientific_review_notes": "docs/scientific-assets/"}
