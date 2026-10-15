from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import shutil
import zipfile

import pytest

from scripts import figure_tool_package_producer as producer


ROOT = Path(__file__).resolve().parents[1]


def _tiny_figure_source(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"name": producer.CANONICAL_PACKAGE_NAME, "version": "1.0.0"}), encoding="utf-8")
    for payload_root in producer.PAYLOAD_ROOTS:
        directory = root / Path(*payload_root.split("/"))
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.html").write_text("<main>Figure</main>", encoding="utf-8")
    return root


def _build_tiny_package(tmp_path: Path, version: str | None = None):
    source = _tiny_figure_source(tmp_path / "source")
    package = tmp_path / "package"
    package.mkdir()
    package.rmdir()
    manifest = producer.build_tool_package(
        source, package, source_revision="a" * 40, version_override=version
    )
    return package, manifest


def test_package_manifest_matches_host_contract_and_private_qa_version_is_marked(tmp_path: Path) -> None:
    package, manifest = _build_tiny_package(tmp_path, "1.0.0-qa.a")
    assert manifest["schema"] == "superbench.toolPackage.v1"
    assert manifest["version"] == "1.0.0-qa.a"
    assert manifest["source_provenance"]["source_version"] == "1.0.0"
    assert manifest["source_provenance"]["synthetic_version_identity"] is True
    assert producer.verify_tool_package(package, trusted_package_sha256=manifest["package_sha256"]) == manifest


@pytest.mark.parametrize("scope,source_eligible,manifest_eligible", [
    ("private-review", True, False),
    ("public-release", True, True),
    ("private-review", False, False),
])
def test_release_scope_gates_manifest_eligibility_without_changing_source_validation(
    tmp_path: Path, monkeypatch, scope: str, source_eligible: bool, manifest_eligible: bool,
) -> None:
    source = _tiny_figure_source(tmp_path / "fixture")
    validation = {"scope": scope, "public_release_eligible": source_eligible}
    monkeypatch.setattr(producer, "resolve_commit", lambda *_: "a" * 40)
    monkeypatch.setattr(producer, "extract_git_archive", lambda _repo, _commit, destination: shutil.copytree(source, destination))
    def validate(_source, *, distribution_scope):
        assert distribution_scope == scope
        return validation
    monkeypatch.setattr(producer, "validate_release_source", validate)
    monkeypatch.setattr(producer, "_rights_receipt", lambda _source, result, *, scope: {
        "scope": scope, "source_public_release_eligible": result["public_release_eligible"],
    })
    release = producer.build_release_artifacts(tmp_path, "fixture", tmp_path / "release", distribution_scope=scope)
    with zipfile.ZipFile(release.package_zip) as archive:
        manifest = json.loads(archive.read("tool-package.json"))
        assert manifest["source_provenance"]["distribution_scope"] == scope
        assert manifest["source_provenance"]["public_release_eligible"] is manifest_eligible
    receipt = json.loads(release.receipt_path.read_text(encoding="utf-8"))
    assert receipt["validation"] == validation
    assert receipt["public_distribution_authorized"] is (scope == "public-release" and source_eligible)
    assert release.public_release_eligible is source_eligible
    assert producer.verify_archive_payload_parity(release.package_zip, release.web_zip)["file_count"] == 5


def test_package_builder_accepts_canonical_identity_and_only_exact_legacy_pair(tmp_path: Path) -> None:
    source = _tiny_figure_source(tmp_path / "source")
    (source / "package.json").write_text(
        json.dumps({"name": "@bsd-studio/figure-studio", "version": "1.0.0-beta.3"}), encoding="utf-8"
    )
    manifest = producer.build_tool_package(source, tmp_path / "historical-package", source_revision="a" * 40)
    assert manifest["source_provenance"]["source_version"] == "1.0.0-beta.3"

    (source / "package.json").write_text(
        json.dumps({"name": "@bsd-studio/figure-studio", "version": "1.0.0-beta.4"}), encoding="utf-8"
    )
    with pytest.raises(producer.ReleaseBuildError, match="identity or version is invalid"):
        producer.build_tool_package(source, tmp_path / "rejected-package", source_revision="b" * 40)


def test_core_bundle_validator_accepts_canonical_and_exact_legacy_metadata(tmp_path: Path) -> None:
    from scripts.figure_studio_core_bundle import capture_figure_studio_core

    source = tmp_path / "figure"
    for relative in ("app", "vendor", "assets/scientific-packs", "assets/scientific-scenes"):
        directory = source / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "entry.txt").write_text("ok", encoding="utf-8")
    package_file = source / "package.json"
    package_file.write_text(json.dumps({"name": "@superbench/figure-tool", "version": "1.0.0-beta.4"}), encoding="utf-8")
    assert capture_figure_studio_core(source).identity["core_version"] == "1.0.0-beta.4"

    package_file.write_text(json.dumps({"name": "@bsd-studio/figure-studio", "version": "1.0.0-beta.3"}), encoding="utf-8")
    assert capture_figure_studio_core(source).identity["core_version"] == "1.0.0-beta.3"
    package_file.write_text(json.dumps({"name": "@bsd-studio/figure-studio", "version": "1.0.0-beta.4"}), encoding="utf-8")
    with pytest.raises(ValueError, match="canonical core version"):
        capture_figure_studio_core(source)


def test_apache_packages_ship_terms_and_reject_missing_or_changed_notices(tmp_path: Path) -> None:
    source = _tiny_figure_source(tmp_path / "source")
    metadata = json.loads((source / "package.json").read_text())
    metadata["license"] = "Apache-2.0"
    (source / "package.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(producer.ReleaseBuildError, match="matching first-party terms"):
        producer.build_tool_package(source, tmp_path / "missing", source_revision="a" * 40)
    (source / "app/legal").mkdir()
    for relative in ("LICENSE", "NOTICE", "LICENSE_POLICY.md",
                     "assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md", "assets/CC0-1.0.txt"):
        (source / relative).parent.mkdir(parents=True, exist_ok=True)
        (source / "app/legal" / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, source / relative)
        shutil.copy2(ROOT / relative, source / "app/legal" / relative)
    package = tmp_path / "valid"
    manifest = producer.build_tool_package(source, package, source_revision="a" * 40)
    assert {"app/legal/LICENSE", "app/legal/NOTICE", "app/legal/LICENSE_POLICY.md",
            "app/legal/assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md", "app/legal/assets/CC0-1.0.txt"} <= {
        row["path"] for row in manifest["payload_files"]}
    (source / "app/legal/NOTICE").write_text("Changed attribution", encoding="utf-8")
    with pytest.raises(producer.ReleaseBuildError, match="NOTICE"):
        producer.build_tool_package(source, tmp_path / "changed", source_revision="a" * 40)


def test_package_archive_is_deterministic_and_portable(tmp_path: Path) -> None:
    package, manifest = _build_tiny_package(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    digest_first = producer._write_deterministic_zip(package, first, package=True)
    digest_second = producer._write_deterministic_zip(package, second, package=True)
    assert digest_first == digest_second
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.testzip() is None
        assert "tool-package.json" in archive.namelist()
        assert "payload/app/index.html" in archive.namelist()
        assert manifest["package_sha256"] == json.loads(archive.read("tool-package.json"))["package_sha256"]

    web_zip = tmp_path / "web.zip"
    producer._write_deterministic_zip(package, web_zip, package=False)
    with zipfile.ZipFile(web_zip) as archive:
        assert set(archive.namelist()) == {
            "app/index.html", "vendor/index.html", "assets/scientific-packs/index.html",
            "assets/scientific-scenes/index.html", "web/index.html",
        }
        assert archive.read("app/index.html") == b"<main>Figure</main>"
    assert producer.verify_archive_payload_parity(first, web_zip)["file_count"] == len(manifest["payload_files"])


@pytest.mark.parametrize("mutation", ["changed", "missing", "extra", "duplicate"])
def test_archive_parity_rejects_web_payload_drift(tmp_path: Path, mutation: str) -> None:
    package, _ = _build_tiny_package(tmp_path)
    native, web = tmp_path / "native.zip", tmp_path / "web.zip"
    producer._write_deterministic_zip(package, native, package=True)
    with zipfile.ZipFile(web, "w") as archive:
        for path in (package / "payload").rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(package / "payload").as_posix()
            if mutation == "missing" and relative == "app/index.html":
                continue
            archive.writestr(relative, b"changed" if mutation == "changed" and relative == "app/index.html" else path.read_bytes())
        if mutation in {"extra", "duplicate"}:
            archive.writestr("extra.txt" if mutation == "extra" else "app/index.html", b"extra")
    with pytest.raises(producer.ReleaseBuildError, match="mismatch|exactly|duplicate"):
        producer.verify_archive_payload_parity(native, web)


def test_public_artifacts_only_runs_public_validation_without_catalog_key(tmp_path: Path, monkeypatch, capsys) -> None:
    output = ROOT / "qa_artifacts" / "test-cli-public-artifacts"
    calls = []
    def build(repository, revision, destination, **options):
        calls.append((repository, revision, destination, options))
        return producer.BuiltRelease("1.0.0", "a" * 40, "b" * 64, "c" * 64, "d" * 64,
            output / "native.zip", output / "web.zip", output / "receipt.json", output / "rights.json",
            output / "inventory.json", "public-release", False, True)
    monkeypatch.setattr(producer, "build_release_artifacts", build)
    monkeypatch.setattr(producer, "_public_key_from_environment", lambda *_: pytest.fail("artifacts-only must not read a signing key"))
    monkeypatch.setattr("sys.argv", ["producer", "--output-root", str(output), "--distribution-scope", "public-release", "--artifacts-only"])
    assert producer.main() == 0
    assert calls[0][3] == {"distribution_scope": "public-release", "version_override": None, "source_exports": False}
    result = json.loads(capsys.readouterr().out)
    assert result["signed_catalog"] is None
    assert result["status"] == "built_public_release_candidate"


def test_artifacts_only_does_not_bypass_failed_source_qualification(monkeypatch, capsys) -> None:
    def reject(*_args, **_kwargs):
        raise producer.ReleaseBuildError("Public release is pending for scientific packs")
    monkeypatch.setattr(producer, "build_release_artifacts", reject)
    monkeypatch.setattr("sys.argv", ["producer", "--artifacts-only", "--distribution-scope", "public-release"])
    assert producer.main() == 2
    assert "pending for scientific packs" in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--previous-feed=x", "--initialize-catalog", "--sign-private-review-candidate",
    "--public-signing-key-env=X", "--public-trust-anchor-env=X", "--qa-signing-key-env=X"])
def test_artifacts_only_rejects_every_catalog_option(option: str, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["producer", "--artifacts-only", option])
    monkeypatch.setattr(producer, "build_release_artifacts", lambda *_args, **_kwargs: pytest.fail("must reject before building"))
    with pytest.raises(SystemExit) as error:
        producer.main()
    assert error.value.code == 2


def test_public_scope_requires_exact_supplement_and_preserves_historical_pending_audits() -> None:
    result = producer.validate_release_source(ROOT, distribution_scope="private-review")
    assert result["scope"] == "private-review"
    assert result["public_release_eligible"] is True
    approved = sorted([
        "rna-methods", "cell-architecture-transport",
        "culture-models-assays", "microbial-biology",
    ])
    assert sum(len(json.loads((ROOT / producer.PACK_ROOT / row['path']).read_text(encoding='utf8'))['assets'])
               for row in result['packs'] if row['pack_id'] in approved) == 80
    assert all(row['status'] == 'rights_cleared_quality_pending' and row['effective_product_release_status'] == 'released'
               for row in result['packs'] if row['pack_id'] in approved)
    assert result["pending_pack_ids"] == []
    assert result["scenes"]["pending_scene_ids"] == []
    assert result["scenes"]["historical_pending_scene_ids"] == ["single-cell-rna-workflow", "spatial-rna-methods"]
    assert producer.validate_release_source(ROOT, distribution_scope="public-release")["public_release_eligible"] is True


def test_qa_version_override_is_rejected_for_public_release(tmp_path: Path) -> None:
    with pytest.raises(producer.ReleaseBuildError, match="only for private-review"):
        producer.build_release_artifacts(ROOT, "HEAD", tmp_path / "build", distribution_scope="public-release",
                                         version_override="1.0.0-qa.a")


def test_package_builder_requires_static_web_entrypoint(tmp_path: Path) -> None:
    source = _tiny_figure_source(tmp_path / "source")
    (source / "web/index.html").unlink()
    with pytest.raises(producer.ReleaseBuildError, match="Static web editor entry point is missing"):
        producer.build_tool_package(source, tmp_path / "package", source_revision="a" * 40)


def test_current_payload_inventory_is_exact_core_and_web_partition() -> None:
    files = producer._source_inventory(ROOT)
    core = producer._prefixed_inventory(ROOT, ("app", "vendor", "assets/scientific-packs", "assets/scientific-scenes"))
    web = producer._prefixed_inventory(ROOT, ("web",))
    assert sorted(core + web, key=lambda row: str(row["path"]).casefold()) == files
    assert len(files) == len(core) + len(web)
    assert {"app/legal/LICENSE", "app/legal/NOTICE", "app/legal/LICENSE_POLICY.md"} <= {
        row["path"] for row in core}
    assert sum(int(row["size"]) for row in files) == sum(int(row["size"]) for row in core + web)
    assert producer._tree_digest(core) != producer._tree_digest(web)


def test_git_archive_uses_committed_bytes_despite_dirty_checkout(tmp_path: Path) -> None:
    repository = tmp_path / "figure-source"
    repository.mkdir()
    subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
    tracked = repository / "tracked.txt"
    tracked.write_text("committed source\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "tracked.txt"], check=True, capture_output=True)
    subprocess.run([
        "git", "-C", str(repository), "-c", "user.name=Figure QA", "-c",
        "user.email=figure-qa@example.invalid", "commit", "-m", "source fixture",
    ], check=True, capture_output=True)
    revision = producer.resolve_commit(repository)
    tracked.write_text("uncommitted checkout edit\n", encoding="utf-8")
    (repository / "untracked.txt").write_text("not committed\n", encoding="utf-8")
    archived = producer.extract_git_archive(repository, revision, tmp_path / "archive")
    assert (archived / "tracked.txt").read_text(encoding="utf-8") == "committed source\n"
    assert not (archived / "untracked.txt").exists()


def test_private_candidate_signing_is_explicit_and_cannot_use_public_mode(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    public = producer._catalog_public_key(key)
    release = producer.BuiltRelease(
        version="1.0.0-qa.a", source_revision="a" * 40,
        package_sha256="1" * 64, archive_sha256="2" * 64, web_archive_sha256="3" * 64,
        package_zip=tmp_path / "package.zip", web_zip=tmp_path / "web.zip",
        receipt_path=tmp_path / "receipt.json", rights_receipt_path=tmp_path / "rights.json",
        inventory_path=tmp_path / "inventory.json", distribution_scope="private-review",
        synthetic_version_identity=True, public_release_eligible=False,
    )
    with pytest.raises(producer.ReleaseBuildError, match="explicit QA-only opt-in"):
        producer.signed_catalog_document(release, private_key=key, previous_catalog=None,
                                         initialize_catalog=True, trusted_public_key=public,
                                         now=datetime(2026, 10, 8, tzinfo=timezone.utc))
    document = producer.signed_catalog_document(
        release, private_key=key, previous_catalog=None, initialize_catalog=True,
        allow_private_review_candidate=True, trusted_public_key=public,
        now=datetime(2026, 10, 8, tzinfo=timezone.utc),
    )
    assert document["schema"] == "superbench.toolReleaseCatalog.v2"
    assert document["releases"][0]["archive_sha256"] == "2" * 64


def test_public_catalog_cannot_claim_private_candidate_is_eligible(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    public = producer._catalog_public_key(key)
    release = producer.BuiltRelease(
        version="1.0.0", source_revision="a" * 40,
        package_sha256="1" * 64, archive_sha256="2" * 64, web_archive_sha256="3" * 64,
        package_zip=tmp_path / "package.zip", web_zip=tmp_path / "web.zip",
        receipt_path=tmp_path / "receipt.json", rights_receipt_path=tmp_path / "rights.json",
        inventory_path=tmp_path / "inventory.json", distribution_scope="public-release",
        public_release_eligible=False,
    )
    with pytest.raises(producer.ReleaseBuildError, match="eligible, nonsynthetic public release"):
        producer.signed_catalog_document(release, private_key=key, previous_catalog=None,
                                         initialize_catalog=True, trusted_public_key=public)


def _release_from_package(package: Path, manifest: dict[str, object], tmp_path: Path) -> producer.BuiltRelease:
    package_zip = tmp_path / f"{manifest['version']}.zip"
    archive_sha = producer._write_deterministic_zip(package, package_zip, package=True)
    return producer.BuiltRelease(
        version=str(manifest["version"]),
        source_revision="a" * 40,
        package_sha256=str(manifest["package_sha256"]),
        archive_sha256=archive_sha,
        web_archive_sha256="3" * 64,
        package_zip=package_zip,
        web_zip=tmp_path / "web.zip",
        receipt_path=tmp_path / "receipt.json",
        rights_receipt_path=tmp_path / "rights.json",
        inventory_path=tmp_path / "inventory.json",
        distribution_scope="private-review",
        synthetic_version_identity=bool(manifest["source_provenance"]["synthetic_version_identity"]),
        public_release_eligible=False,
    )


def test_signed_feed_snapshots_retain_and_verify_prior_release_archives(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    public = producer._catalog_public_key(key)
    package_a, manifest_a = _build_tiny_package(tmp_path / "a", "1.0.0-qa.a")
    release_a = _release_from_package(package_a, manifest_a, tmp_path)
    feed_a = tmp_path / "feed-a"
    feed_a.mkdir()
    archive_a = feed_a / f"archives/figure-studio/{release_a.version}-{release_a.package_sha256}.zip"
    archive_a.parent.mkdir(parents=True)
    archive_a.write_bytes(release_a.package_zip.read_bytes())
    catalog_a = producer.signed_catalog_document(
        release_a, private_key=key, previous_catalog=None, initialize_catalog=True,
        allow_private_review_candidate=True, trusted_public_key=public,
        now=datetime.now(timezone.utc).replace(microsecond=0),
    )
    (feed_a / "catalog.json").write_text(json.dumps(catalog_a), encoding="utf-8")

    package_b, manifest_b = _build_tiny_package(tmp_path / "b", "1.0.0-qa.b")
    release_b = _release_from_package(package_b, manifest_b, tmp_path)
    feed_b = tmp_path / "feed-b"
    feed_b.mkdir()
    verified_a = producer.retain_previous_feed(feed_a, feed_b, public_key=public)
    catalog_b = producer.signed_catalog_document(
        release_b, private_key=key, previous_catalog=verified_a,
        allow_private_review_candidate=True, trusted_public_key=public,
        now=datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=1),
    )
    assert catalog_b["sequence"] == 2
    assert [row["version"] for row in catalog_b["releases"]] == ["1.0.0-qa.a", "1.0.0-qa.b"]
    assert archive_a.read_bytes() == (feed_b / f"archives/figure-studio/{release_a.version}-{release_a.package_sha256}.zip").read_bytes()

    corrupted = feed_a / f"archives/figure-studio/{release_a.version}-{release_a.package_sha256}.zip"
    corrupted.write_bytes(corrupted.read_bytes() + b"corrupt")
    with pytest.raises(producer.ReleaseBuildError, match="archive digest is invalid"):
        producer.retain_previous_feed(feed_a, tmp_path / "feed-c", public_key=public)
