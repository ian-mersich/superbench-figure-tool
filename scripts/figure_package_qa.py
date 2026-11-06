"""Bind browser qualification to an exact extracted Figure tool package.

The QA code stays in the canonical repository. Package mode serves and reads
only the verified payload, including its catalogs and embedded predecessors.
This verifies a caller-selected digest; it does not approve public distribution.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

try:
    from .figure_tool_package_producer import verify_tool_package
except ImportError:
    from figure_tool_package_producer import verify_tool_package


def add_package_arguments(parser):
    parser.add_argument('--package-root', type=Path,
                        help='Extracted tool ZIP root containing tool-package.json and payload/.')
    parser.add_argument('--package-sha256',
                        help='Required trusted semantic package digest when --package-root is supplied.')

def _asset_preview_cancellation_proofs(evidence):
    """Join passive observations only; callers supply manifest and file hashes."""
    if not isinstance(evidence, dict):
        return []
    lifecycle = evidence.get('lifecycle', [])
    contexts = evidence.get('domContexts', {})
    sources = evidence.get('ownedSources', {})
    if not isinstance(lifecycle, list) or not isinstance(contexts, dict) or not isinstance(sources, dict):
        return []
    proofs = []
    for failure_index, failure in enumerate(lifecycle):
        if (failure.get('event'), failure.get('resourceType'), failure.get('method'), failure.get('failure')) != (
                'failed', 'image', 'GET', 'net::ERR_ABORTED'):
            continue
        url, context = failure.get('url', ''), failure.get('context')
        parsed = urlsplit(url)
        source = sources.get(parsed.path, {})
        digest = source.get('manifestSha256', '')
        if (f'{parsed.scheme}://{parsed.netloc}' != evidence.get('origin') or parsed.fragment
                or not parsed.path.startswith('/assets/scientific-packs/') or not parsed.path.endswith('.svg')
                or not re.fullmatch(r'[0-9a-f]{64}', digest) or digest != source.get('sourceSha256')
                or parse_qs(parsed.query, keep_blank_values=True) != {'v': [digest]} or not source.get('assetId')):
            continue
        same = [(index, row) for index, row in enumerate(lifecycle)
                if row.get('url') == url and row.get('context') == context]
        if any((row.get('event') == 'response' and row.get('status') != 200)
               or (row.get('event') == 'failed' and row.get('resourceType') != 'image') for _, row in same):
            continue
        before = [(index, row) for index, row in same if index < failure_index]
        if not (any(row.get('resourceType') == 'fetch' and row.get('event') == 'response'
                    and row.get('status') == 200 for _, row in before)
                and any(row.get('resourceType') == 'fetch' and row.get('event') == 'finished' for _, row in before)):
            continue
        active, ambiguous = None, False
        for index, row in before:
            if row.get('resourceType') != 'image':
                continue
            if row.get('event') == 'request':
                ambiguous = ambiguous or active is not None
                active = (index, row)
            elif row.get('event') in ('finished', 'failed'):
                ambiguous = ambiguous or active is None
                active = None
        if active is None or ambiguous:
            continue
        start_index, start = active
        dom = contexts.get(context, contexts.get(str(context), {}))
        events = dom.get('events', [])
        actions = {row.get('actionId'): row for row in events if row.get('kind') == 'action'}
        replacements = [(event, change) for event in events for change in event.get('changes', [])
                        if change.get('type') == 'src-replaced' and change.get('oldSrc') == url
                        and event.get('atMs', float('inf')) <= failure.get('atMs', -1)]
        if len(replacements) != 1:
            continue
        event, change = replacements[0]
        node = change.get('image', {})
        action = actions.get(event.get('afterActionId'), {})
        allowed = {'assetArtStyleSelect': 'change', 'assetCategorySelect': 'change',
                   'assetSubcategorySelect': 'change', 'assetSearchInput': 'input'}
        data = node.get('src', {})
        if (not isinstance(data, dict) or data.get('scheme') != 'data'
                or not str(data.get('header', '')).startswith('data:image/svg+xml')
                or type(data.get('characters')) is not int or data['characters'] <= 0
                or node.get('assetId') != source['assetId'] or not node.get('nodeId')
                or action.get('targetId') not in allowed or allowed[action['targetId']] != action.get('type')
                or not action.get('value') or action.get('atMs', float('inf')) > event.get('atMs', -1)):
            continue
        observations = []
        for row in events:
            if row.get('kind') == 'action':
                observations.extend((row.get('atMs', -1), image) for image in row.get('before', []))
                observations.extend((row.get('afterAtMs', row.get('atMs', -1)), image) for image in row.get('after', []))
            for mutation in row.get('changes', []):
                images = ([mutation.get('image', {})] if mutation.get('type') == 'src-replaced'
                          else mutation.get('removed', []) + mutation.get('added', []))
                observations.extend((row.get('atMs', -1), image) for image in images)
        # Browser DOM observations bound the HTTP-source epoch. Python request
        # timestamps are callback receipts and can arrive after the src mutation.
        epochs = {}
        for at, image in sorted(observations, key=lambda item: item[0]):
            if image.get('src') == url and image.get('assetId') == source['assetId']:
                epochs.setdefault(image.get('nodeId'), at)
        occurrence = sum(row.get('event') == 'request' and row.get('resourceType') == 'image'
                         for index, row in before if index <= start_index)
        ordered_epochs = list(epochs.items())
        if (occurrence < 1 or occurrence > len(ordered_epochs)
                or ordered_epochs[occurrence - 1][0] != node['nodeId']
                or not action['atMs'] <= ordered_epochs[occurrence - 1][1] <= event['atMs']):
            continue
        if not isinstance(dom.get('current'), list):
            continue
        active_previews = [image for image in dom['current'] if image.get('connected') is True
                           and image.get('assetId') == source['assetId']]
        if not all(image.get('src') and image.get('complete') is True and image.get('naturalWidth', 0) > 0
                   and image.get('naturalHeight', 0) > 0 for image in active_previews):
            continue
        later = [(at, image) for at, image in observations if at >= event['atMs']]
        if not any(image.get('nodeId') == node['nodeId'] and image.get('assetId') == source['assetId']
                   and image.get('connected') is False for _, image in later):
            continue
        action_end = min((row['atMs'] for row in actions.values() if row.get('atMs', -1) > action['atMs']),
                         default=float('inf'))
        current = [(at, image) for at, image in later if at <= action_end and image.get('connected') is True
                   and image.get('assetId') == source['assetId'] and image.get('src') == data]
        if not current:
            continue
        latest_at = max(at for at, _ in current)
        latest = [image for at, image in current if at == latest_at]
        if not all(image.get('complete') is True and image.get('naturalWidth', 0) > 0
                   and image.get('naturalHeight', 0) > 0 for image in latest):
            continue
        preview = latest[0]
        proofs.append({'url': url, 'method': 'GET', 'failure': 'net::ERR_ABORTED', 'context': context,
                       'assetId': source['assetId'], 'sourceSha256': digest, 'actionId': action['actionId'],
                       'retiredNodeId': node['nodeId'], 'currentNodeId': preview['nodeId'],
                       'imageRequestStartIndex': start_index, 'imageRequestStartAtMs': start['atMs'],
                       'imageRequestOccurrence': occurrence,
                       'httpSourceObservedAtMs': ordered_epochs[occurrence - 1][1],
                       'requestTimestampBasis': 'Python callback receipt; DOM node epoch bounds source lifetime',
                       'cause': 'Owned asset image source replaced by hydrated SVG preview'})
    return proofs


def classify_request_failures(failures, *, asset_preview_evidence=None):
    expected = [row for row in failures if row['failure'] == 'net::ERR_ABORTED' and
                ((row.get('method') == 'HEAD' and '/vendor/' in row['url'] and row.get('phase') == 'startup')
                 or row.get('phase') == 'closing-context')]
    result = {'expectedCancellationCount': len(expected),
              'unexpected': [row for row in failures if row not in expected],
              'basis': 'Only startup vendor HEAD probes or context-closing requests with net::ERR_ABORTED are expected cancellations. Runtime vendor GET statuses and dependency readiness are retained separately.'}
    if asset_preview_evidence is not None:
        try:
            proofs = _asset_preview_cancellation_proofs(asset_preview_evidence)
        except (AttributeError, KeyError, TypeError, ValueError):
            proofs = []  # Malformed evidence cannot grant a cancellation exemption.
        signature = lambda row: (row.get('url'), row.get('method'), row.get('failure'))
        lifecycle = asset_preview_evidence.get('lifecycle', []) if isinstance(asset_preview_evidence, dict) else []
        if not isinstance(lifecycle, list) or not all(isinstance(row, dict) for row in lifecycle):
            lifecycle = []
        # Without request IDs, explain a signature only when every recorded
        # failure with that signature has a complete, unambiguous proof.
        explained = [proof for proof in proofs if sum(signature(row) == signature(proof) for row in failures)
                     == sum(row.get('event') == 'failed' and signature(row) == signature(proof) for row in lifecycle)
                     == sum(signature(row) == signature(proof) for row in proofs)]
        result['explainedAssetPreviewCancellations'] = explained
        result['unexpected'] = [row for row in result['unexpected']
                                if not any(signature(row) == signature(proof) for proof in explained)]
    return result


@dataclass(frozen=True)
class FigureQaTarget:
    source_root: Path
    package_root: Path | None = None
    package_sha256: str | None = None

    @classmethod
    def from_arguments(cls, source_root, package_root=None, package_sha256=None):
        if bool(package_root) != bool(package_sha256):
            raise ValueError('--package-root and --package-sha256 must be supplied together')
        if package_sha256 and not re.fullmatch(r'[0-9a-f]{64}', package_sha256):
            raise ValueError('--package-sha256 must be a lowercase SHA-256 semantic package digest')
        if package_root:
            for path in (Path(package_root).absolute(), Path(package_root).absolute() / 'payload'):
                if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                    raise ValueError('Package QA roots must be extracted directories, not links')
        target = cls(Path(source_root).resolve(), Path(package_root).resolve() if package_root else None,
                     package_sha256)
        if target.package_root:
            target.verified_manifest()
        return target

    @property
    def runtime_root(self):
        return self.package_root / 'payload' if self.package_root else self.source_root

    def verified_manifest(self):
        if not self.package_root:
            raise ValueError('No extracted package was selected')
        for path in (self.package_root, self.package_root / 'payload'):
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                raise ValueError('Package QA roots must be extracted directories, not links')
        return verify_tool_package(self.package_root, trusted_package_sha256=self.package_sha256)

    def inventory_identity(self):
        """Rehash the entire payload and reject changes, extra files or links."""
        manifest = self.verified_manifest()
        result = {'package/tool-package.json': hashlib.sha256(
            (self.package_root / 'tool-package.json').read_bytes()).hexdigest()}
        result.update({'payload/' + row['path']: row['sha256'] for row in manifest['payload_files']})
        return result

    def record(self):
        if not self.package_root:
            return {'kind': 'canonical-checkout', 'runtimeRoot': str(self.runtime_root)}
        manifest = self.verified_manifest()
        return {'kind': 'verified-extracted-tool-package', 'packageRoot': str(self.package_root),
                'runtimeRoot': str(self.runtime_root), 'packageSha256': manifest['package_sha256'],
                'version': manifest['version'], 'treeSha256': manifest['tree_sha256'],
                'manifestSha256': hashlib.sha256((self.package_root / 'tool-package.json').read_bytes()).hexdigest(),
                'payloadFileCount': len(manifest['payload_files']),
                'payloadBytes': sum(row['size'] for row in manifest['payload_files']),
                'sourceProvenance': manifest['source_provenance']}
