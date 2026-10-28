from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def render_notice(third_party_text: str, font_license_text: str, native_text: str = "") -> str:
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
        + ("\n" + native_text.rstrip() + "\n" if native_text else "")
    )


ACKNOWLEDGEMENTS = '## PDFium runtime acknowledgements\n\nThis product includes PDFium from the pinned bblanchon/pdfium-binaries release.\nThis software is based in part on the work of the FreeType Team (https://freetype.org/).\nThis software is based in part on the work of the Independent JPEG Group.\nComplete supplier and supplemental component terms accompany the distribution in vendor/NOTICE and vendor/pdfium/notices/.\n'


def native_notice_section(repository_root: Path) -> str:
    lock = json.loads((repository_root / "vendor/source-lock.json").read_text(encoding="utf-8"))
    sections = []
    for row in lock.get("binary_artifacts", []):
        sections += ["## PDFium browser runtime — " + row["version"], "", ACKNOWLEDGEMENTS,
                     "Immutable supplier archive: " + row["archive"]["url"],
                     "Archive SHA-256: " + row["archive"]["sha256"],
                     "Reference PDFium checkout is recipe-consistent, not separately build-attested.", ""]
        for item in row["notices"]:
            path = (repository_root / item["path"]).resolve()
            if not path.is_relative_to(repository_root.resolve()) or path.is_symlink():
                raise ValueError("Unsafe native notice path")
            data = path.read_bytes()
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Native notice identity differs: " + item["path"])
            sections += ["### " + item["component"] + " — " + item["path"], "",
                         data.decode(item["text_encoding"]).replace("\r\n", "\n").replace("\r", "\n").rstrip(), ""]
    return "\n".join(sections).rstrip() + "\n" if sections else ""


def build(repository_root: Path, source_materials: Path, output: Path, *, app_notice_output: Path | None = None, root_notice_output: Path | None = None) -> None:
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
        render_notice(notices.read_text(encoding="utf-8"), font_license.read_text(encoding="utf-8"), native_notice_section(repository_root)),
        encoding="utf-8",
        newline="\n",
    )

    if app_notice_output is not None or root_notice_output is not None:
        first_party = (repository_root / "NOTICE").read_text(encoding="utf-8").split("\n## PDFium runtime acknowledgements\n")[0].rstrip()
        if native_notice_section(repository_root):
            first_party += "\n\n" + ACKNOWLEDGEMENTS.rstrip()
        for target in (app_notice_output, root_notice_output):
            if target is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(first_party + "\n", encoding="utf-8", newline="\n")



def main() -> int:
    parser = argparse.ArgumentParser(description="Build the standalone vendor notice file from verified pinned source materials.")
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--source-materials", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--app-notice-output", type=Path)
    parser.add_argument("--root-notice-output", type=Path)
    args = parser.parse_args()
    repository_root = args.repository_root.resolve()
    source_materials = (args.source_materials or repository_root / "vendor" / "source-materials").resolve()
    output = (args.output or repository_root / "vendor" / "NOTICE").resolve()
    build(repository_root, source_materials, output, app_notice_output=args.app_notice_output, root_notice_output=args.root_notice_output)
    print(f"Built {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
