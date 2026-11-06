"""Check scientific catalog schemas and SVGs before browser qualification.

This read-only preflight uses the existing asset, record, form and cross-pack
identity rules. Exact qualification pins, rights audits and revision receipts
remain required by validate-scientific-assets.py and are checked separately.
A passing schema report never qualifies artwork or approves product release.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = ROOT / 'assets/scientific-packs/library.json'
DEFAULT_OUTPUT = ROOT / 'qa_artifacts/family-library/catalog-schema-preflight.json'
VALIDATOR_PATH = ROOT / 'scripts/validate-scientific-assets.py'
_spec = importlib.util.spec_from_file_location('_catalog_schema_asset_validator', VALIDATOR_PATH)
validator = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = validator
_spec.loader.exec_module(validator)


def catalog_schema_report(library_path: Path | str = DEFAULT_LIBRARY) -> dict:
    """Return a schema/SVG report without invoking qualification pins."""
    library_path = Path(library_path).resolve()
    library = library_path.parent
    registry_bytes = library_path.read_bytes()
    registry = json.loads(registry_bytes)
    report = {
        'schema': 'superbench.independentCatalogSchemaPreflight.v1',
        'scope': 'Existing asset, record, concept/form, SVG safety and cross-pack identity checks. Exact qualification pins, rights audits and revision receipts remain required separately.',
        'status': 'pending', 'asset_count': 0, 'pack_count': len(registry['packs']),
        'errors': [], 'packs': [], 'source_hashes': {},
        'source_unchanged_during_preflight': True,
    }
    inputs = {library_path: hashlib.sha256(registry_bytes).hexdigest()}
    identity = validator.LibraryIdentityState()
    for row in registry['packs']:
        file = validator.exact_pack_file(
            library,
            validator.canonical_relative_file(row['path'], label='registry catalog path', suffix='.json'),
            label='registry catalog path',
        )
        raw = file.read_bytes()
        inputs[file] = hashlib.sha256(raw).hexdigest()
        pack = json.loads(raw)
        base = file.parent
        modern = pack['id'] != validator.CORE_PACK_ID
        entry = {
            'pack_id': pack['id'], 'asset_count': len(pack['assets']),
            'concept_count': len({a.get('concept_id') or a['id'] for a in pack['assets']}),
            'errors': [],
        }

        def checked(label, call):
            try:
                call()
            except (ValueError, KeyError, TypeError) as error:
                issue = {'check': label, 'message': str(error)}
                entry['errors'].append(issue)
                report['errors'].append({'pack_id': pack['id'], **issue})

        try:
            source_ids = validator.validate_record_table(pack, 'source_records', required=modern)
            rights_ids = validator.validate_record_table(pack, 'rights_records', required=modern)
        except (ValueError, KeyError, TypeError) as error:
            issue = {'check': 'record tables', 'message': str(error)}
            entry['errors'].append(issue)
            report['errors'].append({'pack_id': pack['id'], **issue})
            source_ids, rights_ids = set(), set()
        if modern:
            checked('modern release records', lambda: validator.validate_modern_release_records(pack))
        ids, files = set(), {}
        for asset in pack['assets']:
            report['asset_count'] += 1
            relative = validator.canonical_relative_file(asset['file'], label='SVG path', suffix='.svg')
            svg = validator.exact_pack_file(base, relative, label='SVG path')
            inputs[svg] = hashlib.sha256(svg.read_bytes()).hexdigest()
            checked(asset['id'] + ' schema and SVG', lambda a=asset: validator.validate_asset(
                a, pack, base, pack['license_definitions'], pack['style_tokens'].get('viewBox'), ids, files,
                require_modern_metadata=modern, source_record_ids=source_ids, rights_record_ids=rights_ids,
            ))
            checked(asset['id'] + ' cross-pack identity', lambda a=asset: validator._register_library_asset(
                identity, pack_id=pack['id'], pack_dir=base, asset=a,
            ))
            if modern:
                terms = [('scientific_name', asset['scientific_name'])] + [
                    (f'synonyms[{i}]', synonym) for i, synonym in enumerate(asset['synonyms'])
                ]
                observed = {}
                for field, value in terms:
                    key = validator.normalize_search_term(value)
                    if key in observed:
                        entry.setdefault('normalized_alias_duplicates', []).append({
                            'asset_id': asset['id'], 'normalized': key, 'first': observed[key],
                            'duplicate': {'field': field, 'value': value},
                        })
                    else:
                        observed[key] = {'field': field, 'value': value}
        checked('concept variants', lambda: validator.validate_concept_variants(pack['assets']))
        if row['asset_count'] != entry['asset_count'] or row['concept_count'] != entry['concept_count']:
            checked('registry counts', lambda: validator.fail('Registry counts disagree with current catalog'))
        if modern:
            categories = {}
            for asset in pack['assets']:
                value = categories.setdefault(asset['category'], {'concepts': set(), 'style_count': 0})
                value['concepts'].add(asset['concept_id'])
                value['style_count'] += 1
            expected = {key: {'concept_count': len(value['concepts']), 'style_count': value['style_count']}
                        for key, value in categories.items()}
            if pack['category_counts'] != expected:
                checked('category counts', lambda: validator.fail('Category counts disagree with catalog'))
        report['packs'].append(entry)
    for source, digest in inputs.items():
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            report['source_unchanged_during_preflight'] = False
        report['source_hashes'][str(source)] = digest
    report['status'] = ('failed' if report['errors'] else
                        'passed' if report['source_unchanged_during_preflight'] else 'source_changed')
    return report


def validate_catalog_schema(library_path: Path | str = DEFAULT_LIBRARY) -> dict:
    """Return a passing preflight or raise ValueError before creating a browser."""
    try:
        report = catalog_schema_report(library_path)
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise ValueError("Scientific catalog schema preflight could not read source: " + str(error)) from error
    if report['status'] != 'passed':
        details = '\n'.join('- ' + item['message'] for item in report['errors'])
        if not report['source_unchanged_during_preflight']:
            details += '\n- Catalog or SVG source changed during preflight.'
        raise ValueError('Scientific catalog schema preflight failed:\n' + details)
    return report


def bounded_output(output: Path | str) -> Path:
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / 'qa_artifacts'):
        raise ValueError('Schema report output must stay in canonical qa_artifacts.')
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        output = bounded_output(args.output)
        report = catalog_schema_report(args.library)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({'report': str(output), 'status': report['status'], 'assets': report['asset_count'],
                          'packs': report['pack_count'], 'errors': report['errors'],
                          'source_unchanged': report['source_unchanged_during_preflight']}))
        return 0 if report['status'] == 'passed' else 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('Scientific catalog schema preflight failed: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
