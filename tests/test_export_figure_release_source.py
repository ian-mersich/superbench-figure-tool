from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from scripts import export_figure_release_source as exporter
from scripts import figure_tool_package_producer as producer


def tiny_source(root: Path) -> Path:
    root.mkdir()
    (root / "package.json").write_text(json.dumps({"name": producer.CANONICAL_PACKAGE_NAME, "version": "1.0.0"}), encoding="utf-8")
    for name in producer.PAYLOAD_ROOTS:
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / "index.html").write_text("original " + name, encoding="utf-8")
    (root / "assets/scientific-packs/library.json").write_text(json.dumps({
        "packs": [{"id": "fixture", "asset_count": 3, "concept_count": 2}]
    }), encoding="utf-8")
    (root / "assets/scientific-scenes/library.v1.json").write_text(json.dumps({
        "scenes": [{"id": f"template-{index}"} for index in range(3)]
    }), encoding="utf-8")
    (root / "docs/scientific-assets").mkdir(parents=True)
    (root / "docs/scientific-assets/review.md").write_text("Accepted original artwork", encoding="utf-8")
    return root


@pytest.mark.parametrize("reuse_existing", [False, True])
def test_source_exports_preserve_every_payload_byte_and_keep_preferred_sources_outside_runtime(tmp_path, monkeypatch, reuse_existing):
    source = tiny_source(tmp_path / "source")
    package = tmp_path / "package"
    manifest = producer.build_tool_package(source, package, source_revision="a" * 40, distribution_scope="public-release", public_release_eligible=True)
    monkeypatch.setattr(exporter, "SUPPORT_FILES", ("package.json",))
    output = tmp_path / "output"
    output.mkdir()
    existing_materials = None
    if reuse_existing:
        existing_materials = tmp_path / "reused-materials"
        existing_materials.mkdir()
        (existing_materials / "source-index.json").write_text('{"verified": true}', encoding="utf-8")
    calls = []
    stages = []
    def check_export(repository):
        assert not (output / "figure-tool-source.zip").exists()
        exporter.verify_payload(repository, manifest)
        assert (repository / ".github/workflows/source-ci.yml").is_file()
        stages.append("source-check")
    def preferred(_source, destination, _cache, *, reuse_existing=False):
        stages.append("preferred-materials")
        calls.append((destination, reuse_existing))
        if not reuse_existing:
            destination.mkdir()
            (destination / "source-index.json").write_text('{"verified": true}', encoding="utf-8")
        return {"status": "included-and-verified", "index_sha256": exporter.sha(destination / "source-index.json")}
    monkeypatch.setattr(exporter, "prepare_vendor_materials", preferred)
    export_options = {"preferred_materials": existing_materials} if existing_materials else {}
    expected_materials = existing_materials or output / "preferred-source-materials"
    receipt = exporter.export_source(source, package, output, cache=tmp_path / "cache", support_revision="b" * 40,
                                     pre_archive_check=check_export, **export_options)
    assert stages == ["source-check", "preferred-materials"]
    assert calls == [(expected_materials, reuse_existing)]
    assert receipt["shared_payload_parity"] == "passed"
    exporter.verify_payload(output / "source-repository", manifest)
    readme = (output / "source-repository/README.md").read_text(encoding="utf-8")
    assert "3 Library drawings and 3 scientific templates" in readme
    assert "concepts" not in readme
    assert not (output / "source-repository/vendor/source-materials").exists()
    with zipfile.ZipFile(output / receipt["archive"]) as archive:
        for row in manifest["payload_files"]:
            assert archive.read(row["path"]) == (package / "payload" / row["path"]).read_bytes()
        archive_metadata = json.loads(archive.read("SOURCE_RELEASE.json"))
        assert archive_metadata["vendor_source_materials"]["status"] == "included-and-verified"
        if reuse_existing:
            assert str(existing_materials) not in json.dumps(archive_metadata)
        assert "preferred-source-materials/source-index.json" in archive.namelist()
        assert archive.read("docs/scientific-assets/review.md") == b"Accepted original artwork"
    source_metadata = json.loads((output / "source-repository/SOURCE_RELEASE.json").read_text())
    assert source_metadata["schema"] == "figureStudio.publicSourceRelease.v2"
    assert source_metadata["canonical_source_revision"] == "a" * 40
    assert source_metadata["source_support_revision"] == "b" * 40
    assert source_metadata["vendor_source_materials"]["status"] == "fetch-and-verify-from-lock"
    if reuse_existing:
        assert (existing_materials / "source-index.json").read_text(encoding="utf-8") == '{"verified": true}'
        assert str(existing_materials) not in json.dumps(source_metadata)


def test_rejected_slim_export_is_not_sealed_or_sent_to_vendor_preparation(tmp_path, monkeypatch):
    source = tiny_source(tmp_path / "source")
    package = tmp_path / "package"
    producer.build_tool_package(source, package, source_revision="a" * 40,
                                distribution_scope="public-release", public_release_eligible=True)
    monkeypatch.setattr(exporter, "SUPPORT_FILES", ("package.json",))
    monkeypatch.setattr(exporter, "prepare_vendor_materials", lambda *a, **k: pytest.fail("validation must run first"))
    output = tmp_path / "output"
    output.mkdir()
    def reject(repository):
        assert repository.is_dir()
        raise ValueError("Required startup fixture is missing")
    with pytest.raises(ValueError, match="startup fixture"):
        exporter.export_source(source, package, output, cache=tmp_path / "cache", pre_archive_check=reject)
    assert not (output / "figure-tool-source.zip").exists()
    assert not (output / "preferred-source-materials").exists()


@pytest.mark.parametrize("kind", ["changed", "added", "missing"])
def test_source_parity_fails_closed_for_any_payload_change(tmp_path, kind):
    source = tiny_source(tmp_path / "source")
    package = tmp_path / "package"
    manifest = producer.build_tool_package(source, package, source_revision="a" * 40)
    payload = package / "payload"
    path = payload / "app/index.html"
    if kind == "changed":
        path.write_text("changed", encoding="utf-8")
    elif kind == "added":
        (payload / "app/unreviewed.js").write_text("new", encoding="utf-8")
    else:
        path.unlink()
    with pytest.raises(ValueError, match="shared payload"):
        exporter.verify_payload(payload, manifest)
