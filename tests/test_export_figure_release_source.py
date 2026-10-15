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
    (root / "docs/scientific-assets").mkdir(parents=True)
    (root / "docs/scientific-assets/review.md").write_text("Accepted original artwork", encoding="utf-8")
    return root


def test_source_exports_preserve_every_payload_byte_and_keep_preferred_sources_outside_runtime(tmp_path, monkeypatch):
    source = tiny_source(tmp_path / "source")
    package = tmp_path / "package"
    manifest = producer.build_tool_package(source, package, source_revision="a" * 40, distribution_scope="public-release", public_release_eligible=True)
    monkeypatch.setattr(exporter, "SUPPORT_FILES", ("package.json",))
    def preferred(_source, destination, _cache):
        destination.mkdir()
        (destination / "source-index.json").write_text('{"verified": true}', encoding="utf-8")
        return {"status": "included-and-verified", "index_sha256": exporter.sha(destination / "source-index.json")}
    monkeypatch.setattr(exporter, "prepare_vendor_materials", preferred)
    output = tmp_path / "output"
    output.mkdir()
    receipt = exporter.export_source(source, package, output, cache=tmp_path / "cache")
    assert receipt["shared_payload_parity"] == "passed"
    exporter.verify_payload(output / "source-repository", manifest)
    assert not (output / "source-repository/vendor/source-materials").exists()
    with zipfile.ZipFile(output / receipt["archive"]) as archive:
        for row in manifest["payload_files"]:
            assert archive.read(row["path"]) == (package / "payload" / row["path"]).read_bytes()
        assert json.loads(archive.read("SOURCE_RELEASE.json"))["vendor_source_materials"]["status"] == "included-and-verified"
        assert "preferred-source-materials/source-index.json" in archive.namelist()
        assert archive.read("docs/scientific-assets/review.md") == b"Accepted original artwork"
    assert json.loads((output / "source-repository/SOURCE_RELEASE.json").read_text())["vendor_source_materials"]["status"] == "fetch-and-verify-from-lock"


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
