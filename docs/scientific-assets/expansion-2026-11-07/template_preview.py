"""Original SVG previews for the same editable endocrine recipe objects.

The preview retains native node identities, labels, directional arrows and
inhibitory bars. Editor insertion remains the recipe's source of truth.
"""
from __future__ import annotations

import html
import math
import textwrap
import xml.etree.ElementTree as ET


def render(recipe, records):
    width, height = recipe['canvas']['width'], recipe['canvas']['height']
    palette = recipe['palette']
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(recipe["name"])}</title>',
        f'<desc id="desc">{html.escape(recipe["summary"])}</desc>',
        f'<rect width="{width}" height="{height}" fill="{palette[recipe["canvas"]["background_role"]]}"/>']
    lookup = {n['id']: n for n in recipe['nodes']}
    for node in recipe['nodes']:
        x, y, w, h = (node[k] for k in ('x', 'y', 'width', 'height'))
        node_id = html.escape(node['id'])
        if node['type'] == 'asset':
            _, path = records[node['asset_id']]
            svg = ET.fromstring(path.read_text(encoding='utf-8'))
            for element in svg.iter():
                role = node.get('palette_overrides', {}).get(element.get('data-region'))
                if role:
                    for paint in ('fill', 'stroke'):
                        if element.get(paint) and element.get(paint) != 'none':
                            element.set(paint, palette[role])
                    # Paints can be defined on the region's descendants.
                    for leaf in element.iter():
                        for paint in ('fill', 'stroke'):
                            if leaf.get(paint) and leaf.get(paint) != 'none':
                                leaf.set(paint, palette[role])
                if element.get('id'):
                    element.set('id', node['id'] + '_' + element.get('id'))
            svg.set('x', str(x)); svg.set('y', str(y))
            svg.set('width', str(w)); svg.set('height', str(h))
            svg.set('data-scene-node', node['id'])
            svg.set('aria-labelledby', node['id'] + '_title ' + node['id'] + '_desc')
            out.append(ET.tostring(svg, encoding='unicode'))
        elif node['type'] == 'shape':
            style = f'fill="{palette[node["fill_role"]]}" stroke="{palette[node["stroke_role"]]}" stroke-width="{node["stroke_width"]}" data-scene-node="{node_id}"'
            if node['shape'] == 'ellipse':
                out.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" {style}/>')
            elif node['shape'] == 'path':
                out.append(f'<path transform="translate({x} {y})" d="{html.escape(node["path"])}" {style}/>')
            else:
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{node.get("radius",0)}" {style}/>')
    for relation in recipe['connectors']:
        def anchor(endpoint):
            n, a = lookup[endpoint['node_id']], endpoint['anchor']
            return (n['x'] + n['width'] * {'left': 0, 'right': 1}.get(a, .5),
                    n['y'] + n['height'] * {'top': 0, 'bottom': 1}.get(a, .5))
        start, end = anchor(relation['from']), anchor(relation['to'])
        points = [start, end]
        style = relation['style']
        if style.get('route') == 'elbow':
            a, b = relation['from']['anchor'], relation['to']['anchor']
            if a == b == 'bottom':
                lane = max(start[1], end[1]) + 28
                points = [start, (start[0], lane), (end[0], lane), end]
            elif a in ('left', 'right') and b in ('left', 'right'):
                middle = (start[0] + end[0]) / 2
                points = [start, (middle, start[1]), (middle, end[1]), end]
            else:
                points = [start, (start[0], end[1]), end]
        color = palette[style['stroke_role']]
        sw = style['stroke_width']
        dash = ' stroke-dasharray="7 5"' if style.get('line') == 'dashed' else ''
        path = 'M' + ' L'.join(f'{x:g} {y:g}' for x, y in points)
        out.append(f'<g data-scene-connector="{html.escape(relation["id"])}"><path d="{path}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{dash}/>')
        x, y = end
        previous = next((p for p in reversed(points[:-1]) if p != end), start)
        theta = math.atan2(y-previous[1], x-previous[0])
        ux, uy = math.cos(theta), math.sin(theta)
        if style.get('terminator') == 'bar':
            d = f'M{x-7*uy:g} {y+7*ux:g} L{x+7*uy:g} {y-7*ux:g}'
            out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw+1}"/>')
        elif style.get('terminator') == 'arrow':
            d = f'M{x-9*ux+5*uy:g} {y-9*uy-5*ux:g} L{x:g} {y:g} L{x-9*ux-5*uy:g} {y-9*uy+5*ux:g}'
            out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"/>')
        # Explicit node labels already identify CRH/TRH/ACTH/TSH and medium
        # flow. Feedback and tissue-action labels carry additional meaning.
        label = relation.get('label', '')
        if label and relation['relation'] in ('inhibition', 'secretion', 'transport') and label not in ('release', 'insulin'):
            segments = [(a, b, math.dist(a, b)) for a, b in zip(points, points[1:])]
            a, b, _ = max(segments, key=lambda row: row[2])
            offset = style.get('label_offset', {})
            tx = (a[0]+b[0])/2 + offset.get('x', 0)
            ty = (a[1]+b[1])/2 + offset.get('y', 0) - 7
            out.append(f'<text x="{tx:g}" y="{ty:g}" text-anchor="middle" font-family="Arial,sans-serif" font-size="17" fill="{color}">{html.escape(label)}</text>')
        out.append('</g>')
    for node in recipe['nodes']:
        if node['type'] != 'text':
            continue
        size = node['font_size']
        align = node['align']
        x = node['x'] + (node['width']/2 if align == 'center' else node['width'] if align == 'right' else 0)
        lines = []
        for paragraph in node['text'].splitlines():
            lines.extend(textwrap.wrap(paragraph, max(8, int(node['width']/(size*.51)))) or [''])
        spans = ''.join(f'<tspan x="{x:g}" dy="{0 if i==0 else size*1.15:g}">{html.escape(line)}</tspan>' for i, line in enumerate(lines))
        out.append(f'<text data-scene-node="{html.escape(node["id"])}" x="{x:g}" y="{node["y"]+size:g}" text-anchor="{"middle" if align=="center" else "end" if align=="right" else "start"}" font-family="Arial,sans-serif" font-size="{size:g}" font-weight="{700 if node["id"]=="title" else 500}" fill="{palette[node["fill_role"]]}">{spans}</text>')
    return '\n'.join([*out, '</svg>']) + '\n'
