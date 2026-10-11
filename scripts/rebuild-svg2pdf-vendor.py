from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reconstruct(upstream_bytes: bytes, manifest: dict) -> bytes:
    entries = [row for row in manifest.get("runtime_files", []) if row.get("id") == "svg2pdf"]
    if len(entries) != 1:
        raise ValueError("vendor manifest must contain exactly one svg2pdf runtime entry")
    runtime = entries[0]
    patch = runtime.get("local_patch")
    if not isinstance(patch, dict) or patch.get("schema") != "figureStudio.vendorLocalPatch.v1":
        raise ValueError("svg2pdf local patch record is missing")
    if len(upstream_bytes) != patch.get("upstream_runtime_bytes") or _sha256(upstream_bytes) != patch.get("upstream_runtime_sha256"):
        raise ValueError("input is not the exact pinned svg2pdf.js 2.7.0 upstream UMD runtime")
    output = upstream_bytes
    anchors = patch.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        raise ValueError("svg2pdf local patch anchors are missing")
    for index, anchor in enumerate(anchors):
        before = anchor.get("rawBeforeAnchor")
        after = anchor.get("rawAfterAnchor")
        if not isinstance(before, str) or not isinstance(after, str) or not before or not after:
            raise ValueError(f"invalid svg2pdf patch anchor {index}")
        before_bytes = before.encode("utf-8")
        after_bytes = after.encode("utf-8")
        occurrences = output.count(before_bytes)
        if occurrences != 1:
            raise ValueError(f"svg2pdf patch anchor {index} must occur once; found {occurrences}")
        output = output.replace(before_bytes, after_bytes, 1)
    if len(output) != runtime.get("bytes") or _sha256(output) != runtime.get("sha256"):
        raise ValueError("reconstructed svg2pdf runtime does not match vendor manifest bytes")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconstruct the exact local svg2pdf UMD patch from its pinned npm distribution.")
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--upstream", type=Path, required=True, help="Exact package/dist/svg2pdf.umd.min.js from svg2pdf.js 2.7.0")
    parser.add_argument("--output", type=Path, help="Write the reconstructed runtime here")
    parser.add_argument("--check", action="store_true", help="Compare reconstructed bytes with the checked-in vendor runtime")
    args = parser.parse_args(argv)
    if args.check == bool(args.output):
        parser.error("choose exactly one of --check or --output")
    root = args.repository_root.resolve()
    try:
        manifest = json.loads((root / "vendor" / "manifest.json").read_text(encoding="utf-8"))
        rebuilt = reconstruct(args.upstream.read_bytes(), manifest)
        if args.check:
            expected = root / "vendor" / "svg2pdf" / "svg2pdf.umd.min.js"
            if rebuilt != expected.read_bytes():
                raise ValueError("reconstructed bytes differ from vendor/svg2pdf/svg2pdf.umd.min.js")
            print("svg2pdf upstream-plus-patch bytes match the checked-in runtime")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(rebuilt)
            print(f"Reconstructed svg2pdf runtime at {args.output.resolve()}")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"svg2pdf reconstruction failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
