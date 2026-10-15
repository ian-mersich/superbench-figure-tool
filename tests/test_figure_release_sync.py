import json
from pathlib import Path
import shutil
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from figure_tool_package_producer import build_tool_package
from check_figure_release_sync import check_sync


@pytest.fixture
def release(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "package.json").write_text(json.dumps({"name": "@superbench/figure-tool", "version": "1.0.0-beta.9"}))
    for name in ("app", "vendor", "assets/scientific-packs", "assets/scientific-scenes", "web"):
        path = source / name
        path.mkdir(parents=True)
        (path / "release.txt").write_text(name)
    (source / "app/index.html").write_text("editor")
    (source / "web/index.html").write_text("shell")
    package = tmp_path / "package"
    manifest = build_tool_package(source, package, source_revision="a" * 40,
                                  distribution_scope="public-release", public_release_eligible=True)
    digest = manifest["package_sha256"]
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps({"tool_id": "figure-studio", "version": manifest["version"],
        "commit": "a" * 40, "package_sha256": digest,
        "distribution_scope": "public-release", "public_release_eligible": True}))
    store = tmp_path / "store"
    (store / "state").mkdir(parents=True)
    (store / "state/figure-studio.json").write_text(json.dumps({"active": {
        "tool_id": "figure-studio", "version": manifest["version"],
        "package_sha256": digest, "tree_sha256": manifest["tree_sha256"]}}))
    (store / "trusted-pins.json").write_text(json.dumps({"packages": {"figure-studio": {manifest["version"]: digest}}}))
    installed = store / "packages/figure-studio" / f"{manifest['version']}-{digest[:12]}"
    shutil.copytree(package, installed)
    site = tmp_path / "site"
    shutil.copytree(package / "payload", site)
    (site / "SOURCE_RELEASE.json").write_text(json.dumps({"product_version": manifest["version"],
        "source_revision": "a" * 40, "package_sha256": digest,
        "payload_tree_sha256": manifest["tree_sha256"], "payload_file_count": len(manifest["payload_files"])}))
    return package, digest, pin, store, site, installed


def test_every_consumer_and_payload_agrees(release):
    package, digest, pin, store, site, _ = release
    result = check_sync(package, digest, pin, store, site_root=site)
    assert result["status"] == "passed"
    assert result["checked_payload_files"] == 7


@pytest.mark.parametrize("changed", ["web", "installed", "selection", "trust", "pin", "metadata"])
def test_version_label_cannot_hide_drift(release, changed):
    package, digest, pin, store, site, installed = release
    if changed == "web":
        (site / "app/index.html").write_text("outdated editor")
    elif changed == "installed":
        (installed / "payload/app/index.html").write_text("outdated editor")
    else:
        path = {"selection": store / "state/figure-studio.json", "trust": store / "trusted-pins.json",
                "pin": pin, "metadata": site / "SOURCE_RELEASE.json"}[changed]
        data = json.loads(path.read_text())
        if changed == "selection": data["active"]["package_sha256"] = "f" * 64
        elif changed == "trust": data["packages"]["figure-studio"]["1.0.0-beta.9"] = "f" * 64
        elif changed == "pin": data["commit"] = "b" * 40
        else: data["source_revision"] = "b" * 40
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        check_sync(package, digest, pin, store, site_root=site)
