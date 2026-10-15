"""Read-only verification that web, Superbench's pin and installed Figure agree."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from figure_tool_package_producer import verify_tool_package

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_sync(package_root: Path, digest: str, core_pin: Path, store: Path,
               *, site_root: Path | None = None, base_url: str | None = None) -> dict:
    if (site_root is None) == (base_url is None):
        raise ValueError("Choose exactly one local site root or live base URL")
    manifest = verify_tool_package(package_root, trusted_package_sha256=digest)
    version = manifest["version"]
    revision = manifest["source_provenance"]["source_revision"]
    tree = manifest["tree_sha256"]
    pin = read_json(core_pin)
    expected_pin = {"tool_id": "figure-studio", "version": version,
                    "commit": revision, "package_sha256": digest,
                    "distribution_scope": "public-release", "public_release_eligible": True}
    if (pin.get("public_release_eligible") is not True
            or any(pin.get(key) != value for key, value in expected_pin.items())):
        raise ValueError("Superbench source pin differs from the shared public release")
    if (manifest["source_provenance"]["distribution_scope"] != "public-release"
            or manifest["source_provenance"]["public_release_eligible"] is not True):
        raise ValueError("Expected package is not a qualified public release")
    state = read_json(store / "state/figure-studio.json")
    active = state.get("active", {})
    if any(active.get(key) != value for key, value in {
            "tool_id": "figure-studio", "version": version,
            "package_sha256": digest, "tree_sha256": tree}.items()):
        raise ValueError("Installed Figure selection differs from the shared release")
    trust = read_json(store / "trusted-pins.json")
    if trust.get("packages", {}).get("figure-studio", {}).get(version) != digest:
        raise ValueError("Installed Figure trust pin differs from the shared release")
    installed = store / "packages/figure-studio" / f"{version}-{digest[:12]}"
    verify_tool_package(installed, trusted_package_sha256=digest)

    def fetch(relative: str) -> bytes:
        if site_root is not None:
            return (site_root / relative).read_bytes()
        url = base_url.rstrip("/") + "/" + quote(relative, safe="/") + "?figure_release=" + digest
        with urlopen(Request(url, headers={"Cache-Control": "no-cache"}), timeout=30) as response:
            return response.read()

    metadata = json.loads(fetch("SOURCE_RELEASE.json"))
    expected_meta = {"product_version": version, "source_revision": revision,
                     "package_sha256": digest, "payload_tree_sha256": tree,
                     "payload_file_count": len(manifest["payload_files"])}
    if any(metadata.get(key) != value for key, value in expected_meta.items()):
        raise ValueError("Web release metadata differs from the shared release")

    def compare(row: dict) -> str | None:
        actual = fetch(row["path"])
        if len(actual) != row["size"] or hashlib.sha256(actual).hexdigest() != row["sha256"]:
            return row["path"]
        return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        mismatches = [name for name in pool.map(compare, manifest["payload_files"]) if name]
    if mismatches:
        raise ValueError("Web payload differs from desktop: " + ", ".join(mismatches))
    return {"schema": "figureStudio.releaseSyncCheck.v1", "status": "passed",
            **expected_meta, "core_pin_matches": True, "installed_selection_matches": True,
            "installed_trust_matches": True, "installed_payload_verified": True,
            "web_payload_verified": True, "checked_payload_files": len(manifest["payload_files"]),
            "web_target": str(site_root) if site_root else base_url}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--package-sha256", required=True)
    parser.add_argument("--core-pin", type=Path, default=ROOT.parent / "mersich_lab_superbench/core/config/figure-release.json")
    parser.add_argument("--store", type=Path, default=Path(os.environ.get("LOCALAPPDATA", "")) / "BSD Studio/ToolPackages")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--site-root", type=Path, help="Tool subtree containing app/, web/ and SOURCE_RELEASE.json")
    target.add_argument("--base-url", help="Published tool subtree URL")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to((ROOT / "qa_artifacts").resolve())
    if output.exists():
        parser.error("Use a fresh report path")
    try:
        result = check_sync(args.package_root, args.package_sha256, args.core_pin, args.store,
                            site_root=args.site_root, base_url=args.base_url)
    except Exception as error:
        result = {"schema": "figureStudio.releaseSyncCheck.v1", "status": "failed", "error": str(error)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
