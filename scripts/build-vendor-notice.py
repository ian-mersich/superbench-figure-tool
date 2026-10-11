from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def render_notice(third_party_text: str, font_license_text: str) -> str:
    body = third_party_text.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    font = font_license_text.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return (
        "# Third-party notices for Figure Tool vendor files\n\n"
        "This file accompanies the vendored browser code and fonts. It includes the full package license and notice texts identified from the pinned distributions, plus the jsPDF module attribution and license comments mapped from its pinned source map. These notices are informational and do not make a legal determination about the scope or compatibility of any license.\n\n"
        + body
        + "\n\n## DejaVu font terms\n\n"
        + "The following is the complete license text distributed with the DejaVu font files.\n\n"
        + font
        + "\n"
    )


def build(repository_root: Path, source_materials: Path, output: Path) -> None:
    verifier = repository_root / "scripts" / "prepare-vendor-source.py"
    subprocess.run(
        [sys.executable, str(verifier), "--repository-root", str(repository_root), "--verify", str(source_materials)],
        check=True,
    )
    notices = source_materials / "THIRD_PARTY_NOTICES.md"
    font_license = repository_root / "vendor" / "licenses" / "dejavu-sans-LICENSE.txt"
    if not notices.is_file() or not font_license.is_file():
        raise ValueError("source package notices or DejaVu license text are missing")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_notice(notices.read_text(encoding="utf-8"), font_license.read_text(encoding="utf-8")),
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the standalone vendor notice file from verified pinned source materials.")
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--source-materials", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    repository_root = args.repository_root.resolve()
    source_materials = (args.source_materials or repository_root / "vendor" / "source-materials").resolve()
    output = (args.output or repository_root / "vendor" / "NOTICE").resolve()
    build(repository_root, source_materials, output)
    print(f"Built {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
