"""Reproduce or verify the isolated factory around exact supplier JavaScript.

This concatenates checked-in bytes; it neither compiles nor executes PDFium.
The supplier source remains unmodified inside the derived factory.
"""
import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    ('scripts/pdfium-factory/factory-prefix.js.txt', '77974bc314e705279e3fcad80eb71c6a1352b1081b1933394ea56799bc243754'),
    ('vendor/pdfium/pdfium.js', '9bdac90c5714c50187d5a96ce04b2dd9b01c5a8e6ded68978536ee3820f6e218'),
    ('scripts/pdfium-factory/factory-suffix.js.txt', '02fdaf1e04f0cd31c21a94eca4f9bdbc7787e21f43a248e5a3ac8a1b252044a6'),
)
OUTPUT_SHA256 = '1e1e859bef696fbb858b25b884a0ded18181c373702af7f80ce3db7e7838033e'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify without writing the checked-in factory.')
    args = parser.parse_args()
    parts = []
    for relative, expected in INPUTS:
        raw = (ROOT / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f'Pinned factory input differs: {relative}')
        parts.append(raw)
    result = b''.join(parts)
    if hashlib.sha256(result).hexdigest() != OUTPUT_SHA256:
        raise SystemExit('Derived factory differs from the reviewed runtime.')
    output = ROOT / 'vendor/pdfium/pdfium.esm.js'
    if args.check:
        if output.read_bytes() != result:
            raise SystemExit('Checked-in PDFium factory differs from its exact inputs.')
    else:
        output.write_bytes(result)
    print('PDFium isolated factory verified' if args.check else 'PDFium isolated factory reproduced')


if __name__ == '__main__':
    main()
