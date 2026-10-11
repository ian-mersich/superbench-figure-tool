from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import unittest
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = _load("prepare_vendor_source", ROOT / "scripts" / "prepare-vendor-source.py")
rebuild = _load("rebuild_svg2pdf_vendor", ROOT / "scripts" / "rebuild-svg2pdf-vendor.py")
notice_builder = _load("build_vendor_notice", ROOT / "scripts" / "build-vendor-notice.py")


class VendorSourceLockTests(unittest.TestCase):
    def test_lock_rows_validate_and_include_editable_pdfjs_source(self):
        lock, _ = prepare._load_lock(ROOT)
        self.assertEqual(len(lock["source_packages"]), 8)
        self.assertGreaterEqual(len(lock["npm_packages"]), 20)
        pdfjs_commits = {row["commit"] for row in lock["source_packages"] if row["name"] == "pdfjs-dist"}
        self.assertEqual(pdfjs_commits, {
            "7e5b36c2d572ba82e1e3adeb1c266f0052746c73",
            "ce87167432819f85df49b6b16c7a78556e9a4ee0",
        })
        for row in lock["source_packages"]:
            prepare._validate_archive_row(row, npm=False)
        for row in lock["npm_packages"]:
            prepare._validate_archive_row(row, npm=True)

    def test_bad_npm_integrity_and_unpinned_repository_url_are_rejected(self):
        with self.assertRaises(ValueError):
            prepare._validate_archive_row({"name": "example", "version": "1.0.0", "integrity": "sha512-not-a-digest"}, npm=True)
        lock, _ = prepare._load_lock(ROOT)
        row = dict(lock["source_packages"][0], archive_url="https://example.invalid/source.tar.gz")
        with self.assertRaises(ValueError):
            prepare._validate_archive_row(row, npm=False)

    def test_npm_output_slug_matches_registry_package_identity(self):
        self.assertEqual(prepare._npm_slug("svg2pdf.js", "2.7.0"), "svg2pdf.js@2.7.0")
        self.assertEqual(prepare._npm_slug("@pdf-lib/upng", "1.0.1"), "@pdf-lib_upng@1.0.1")

    def test_splaytree_readme_is_indexed_as_its_license_source(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp)
            (package / "Readme.md").write_text("package docs", encoding="utf-8")
            self.assertIn("Readme.md", prepare._notice_files(package, "splaytree"))
            self.assertNotIn("Readme.md", prepare._notice_files(package, "another-package"))

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "escape.tar"
            with tarfile.open(archive, "w") as tar:
                payload = b"unsafe"
                member = tarfile.TarInfo("root/../outside.txt")
                member.size = len(payload)
                tar.addfile(member, BytesIO(payload))
            with self.assertRaises(ValueError):
                prepare._extract(archive, Path(temp) / "out", expected_root="root")

    def test_archive_can_be_hashed_without_materializing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "source.tar"
            payload = b"editable source"
            with tarfile.open(archive, "w") as tar:
                member = tarfile.TarInfo("root/src/file.ts")
                member.size = len(payload)
                tar.addfile(member, BytesIO(payload))
            inventory = prepare._extract(archive, None, expected_root="root")
            self.assertEqual(inventory, [{
                "path": "src/file.ts",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }])

    def test_long_windows_source_path_extracts_and_verifies(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            repository_root = temp_root / "repo"
            (repository_root / "vendor").mkdir(parents=True)
            long_parent = temp_root
            for index in range(4):
                long_parent /= f"candidate-path-segment-{index}-" + ("x" * 26)
            output = long_parent / "source-materials"
            cache = temp_root / "cache"
            cache.mkdir()

            deep_relative = "/".join([f"directory-{index}-" + ("d" * 22) for index in range(5)] + ["editable-source.ts"])
            repo_archive = cache / "git-long-source.tar.gz"
            with tarfile.open(repo_archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
                contents = b"export const editable = true;\n"
                member = tarfile.TarInfo(f"repo/{deep_relative}")
                member.size = len(contents)
                archive.addfile(member, BytesIO(contents))

            npm_archive = cache / "npm-jspdf_4.2.1.tgz"
            npm_files = {
                "package/package.json": json.dumps({"name": "jspdf", "version": "4.2.1", "license": "MIT"}).encode(),
                "package/LICENSE": b"MIT package license\n",
                "package/dist/jspdf.umd.min.js.map": json.dumps({"sources": ["source.js"], "sourcesContent": ["/* @license MIT */"]}).encode(),
            }
            with tarfile.open(npm_archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
                for name, contents in npm_files.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(contents)
                    archive.addfile(member, BytesIO(contents))

            commit = "a" * 40
            source_archive = repo_archive.read_bytes()
            lock = {
                "schema": prepare.SCHEMA,
                "source_packages": [{
                    "id": "long-source",
                    "name": "long-source",
                    "version": "1.0.0",
                    "repository": "https://example.invalid/long-source",
                    "commit": commit,
                    "archive_url": f"https://example.invalid/{commit}",
                    "archive_bytes": len(source_archive),
                    "archive_sha256": hashlib.sha256(source_archive).hexdigest(),
                    "archive_root": "repo",
                }],
                "npm_packages": [{
                    "name": "jspdf",
                    "version": "4.2.1",
                    "integrity": prepare._sha512_sri(npm_archive),
                    "license": "MIT",
                }],
            }
            (repository_root / "vendor" / "source-lock.json").write_text(json.dumps(lock), encoding="utf-8")

            deep_target = output / "repositories" / "long-source" / Path(deep_relative)
            self.assertGreater(len(os.fspath(deep_target)), 260)
            self.assertEqual(prepare.main([
                "--repository-root", os.fspath(repository_root),
                "--output", os.fspath(output),
                "--cache-dir", os.fspath(cache),
            ]), 0)
            extracted = prepare._filesystem_path(deep_target)
            self.assertEqual(extracted.read_bytes(), b"export const editable = true;\n")
            index_text = prepare._filesystem_path(output / "source-index.json").read_text(encoding="utf-8")
            self.assertNotIn("\\\\?\\", index_text)
            self.assertEqual(prepare.main([
                "--repository-root", os.fspath(repository_root),
                "--verify", os.fspath(output),
            ]), 0)
            shutil.rmtree(prepare._filesystem_path(temp_root))

    def test_jspdf_module_comments_are_copied_with_source_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp)
            dist = package / "dist"
            dist.mkdir()
            source_map = {
                "sources": ["../src/libs/example.js", "../src/ordinary.js"],
                "sourcesContent": [
                    "/* Copyright Example. Permission is hereby granted. */\nconst x=1;",
                    "/* ordinary implementation detail */\nconst y=2;",
                ],
            }
            (dist / "jspdf.umd.min.js.map").write_text(json.dumps(source_map), encoding="utf-8")
            comments = prepare._jspdf_module_comments(package)
            self.assertEqual(len(comments), 1)
            self.assertEqual(comments[0][0], "../src/libs/example.js")
            self.assertIn("Permission is hereby granted", comments[0][1])

    def test_standalone_notice_contains_full_dependency_and_font_terms(self):
        text = notice_builder.render_notice("Full transitive license text", "Full DejaVu terms")
        self.assertIn("Full transitive license text", text)
        self.assertIn("Full DejaVu terms", text)
        self.assertIn("jsPDF module attribution", text)


class Svg2PdfReconstructionTests(unittest.TestCase):
    def test_recorded_anchor_reconstruction_is_exact_and_reversible(self):
        upstream = b"prefix|anchor|suffix"
        expected = b"prefix|patched|suffix"
        manifest = {
            "runtime_files": [{
                "id": "svg2pdf",
                "bytes": len(expected),
                "sha256": hashlib.sha256(expected).hexdigest(),
                "local_patch": {
                    "schema": "figureStudio.vendorLocalPatch.v1",
                    "upstream_runtime_bytes": len(upstream),
                    "upstream_runtime_sha256": hashlib.sha256(upstream).hexdigest(),
                    "anchors": [{"rawBeforeAnchor": "anchor", "rawAfterAnchor": "patched"}],
                },
            }]
        }
        self.assertEqual(rebuild.reconstruct(upstream, manifest), expected)
        with self.assertRaises(ValueError):
            rebuild.reconstruct(upstream + b"!", manifest)

    def test_ambiguous_anchor_is_rejected(self):
        upstream = b"x|a|a"
        patched = b"x|b|a"
        manifest = {
            "runtime_files": [{
                "id": "svg2pdf",
                "bytes": len(patched),
                "sha256": hashlib.sha256(patched).hexdigest(),
                "local_patch": {
                    "schema": "figureStudio.vendorLocalPatch.v1",
                    "upstream_runtime_bytes": len(upstream),
                    "upstream_runtime_sha256": hashlib.sha256(upstream).hexdigest(),
                    "anchors": [{"rawBeforeAnchor": "a", "rawAfterAnchor": "b"}],
                },
            }]
        }
        with self.assertRaises(ValueError):
            rebuild.reconstruct(upstream, manifest)


if __name__ == "__main__":
    unittest.main()
