"""Original Style 4 neurobiology companions for the 2026-11-03 expansion.

These editable SVG variants retain the accepted neuro asset topology and
semantic part IDs while adding hand-authored, bounded facets and fine contours.
They are original companion drawings, not copies or tracings of the existing
Style 4 Library assets.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import xml.etree.ElementTree as ET


_BASE_PATH = Path(__file__).with_name("neuro_asset_art.py")
_BASE_SPEC = spec_from_file_location("_neuro_asset_art_style4_base", _BASE_PATH)
if _BASE_SPEC is None or _BASE_SPEC.loader is None:
    raise ImportError(f"Cannot load accepted base neuro art module at {_BASE_PATH}")
_BASE = module_from_spec(_BASE_SPEC)
_BASE_SPEC.loader.exec_module(_BASE)

_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _NS)

STYLE4_DEFAULT_PAINTS = {
    "presynaptic": "#E2A168", "postsynaptic": "#B7DBD3",
    "cleft": "#F0E2C0", "vesicles": "#FFF7E8",
    "axon": "#E2A168", "myelin": "#83B9D5",
    "periaxonal_space": "#F5E9D5", "soma": "#B7AFE0",
    "process": "#D3CDEE", "schwann_cytoplasm": "#C0DED6",
    "ensheathment": "#85B7D4", "dendrite": "#B7DBD3",
    "spine": "#84B9D7", "postsynaptic_density": "#E2A168",
    "terminal": "#E2A168", "neuron": "#84B9D7",
    "astrocyte": "#AEA5D6", "microglia": "#B7AFE0",
    "neural_target": "#B7DBD3", "nodal_region": "#F0E2C0",
    "connection": "#83B9D5", "arrow": "#E2A168",
    "outline": "#2B3642",
}

_FORM_IDS = {
    "chemical_synapse": ("bouton_spine", "shaft_contact"),
    "axon_myelin": ("longitudinal", "transverse"),
    "oligodendrocyte": ("multiple_sheaths", "branching"),
    "schwann_cell": ("myelinating_internode", "nonmyelinating_bundle"),
    "dendritic_spine": ("mushroom", "thin"),
    "axon_terminal": ("single_bouton", "branched_terminals"),
    "neuron_astrocyte_contact": ("single_synapse", "process_network"),
    "microglia_contact": ("surveying", "synaptic_contact"),
    "node_of_ranvier": ("paired_internodes", "channel_region"),
    "neural_circuit": ("feedforward_chain", "convergent_inputs"),
}


def _q(tag: str) -> str:
    return f"{{{_NS}}}{tag}"


def _append(root: ET.Element, region: str, svg_markup: str) -> None:
    """Insert editable depth facets directly above their semantic base part."""
    wrapper = ET.fromstring(f'<g xmlns="{_NS}" data-region="{region}">{svg_markup}</g>')
    base_index = next((i for i, node in enumerate(root) if node.get("data-region") == region), None)
    if base_index is None:
        base_index = next((i for i, node in enumerate(root) if node.get("data-region") == "outline"), len(root)) - 1
    root.insert(base_index + 1, wrapper)


def _stroke(d: str, color: str, width: float = 1.0, opacity: float = 1.0) -> str:
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"/>')


def _facet(d: str, color: str, opacity: float) -> str:
    return f'<path d="{d}" fill="{color}" opacity="{opacity}"/>'


def _tapered_profile(d: str, color: str) -> str:
    return (f'<path d="{d}" fill="{color}" stroke="#2B3642" stroke-width="0.82" '
            'stroke-linecap="round" stroke-linejoin="round"/>')


def _depth_art(key: str, index: int, root: ET.Element) -> None:
    O = "#2B3642"
    HI = "#FFFFFF"
    SHADE = "#40566B"
    if key == "chemical_synapse":
        _append(root, "presynaptic", _facet("M30 42 Q30 33 41 30 Q53 27 69 30 L69 34 Q57 32 45 35 Q37 38 35 47 L35 60 Q35 65 42 67 L36 67 Q30 64 30 57Z", HI, .32) + _facet("M42 67 Q65 70 88 67 Q94 66 97 61 L96 66 Q91 71 82 71 H40Z", SHADE, .13))
        if index == 0:
            postfacet = _facet("M22 102 Q41 100 56 102 L58 96 Q60 92 65 90 Q70 92 71 98 L74 102 Q92 100 106 102 L106 107 Q63 112 22 107Z", HI, .35) + _facet("M58 85 Q59 82 65 82 Q71 82 71 86 Q70 88 66 89 Q62 89 58 87Z", HI, .34)
        else:
            postfacet = _facet("M23 84 Q62 82 105 84 L105 89 Q63 87 23 89Z", HI, .34) + _facet("M23 101 Q62 106 105 101 L105 106 Q62 111 23 106Z", SHADE, .1)
        _append(root, "postsynaptic", postfacet)
        _append(root, "vesicles", "".join(_stroke(d, HI, 1.05, .8) for d in (
            "M40 43 Q41 39 44 39", "M59 39 Q60 35 63 35", "M79 45 Q80 41 83 41")))
        _append(root, "cleft", _facet("M33 73 H94 V75 H33Z", HI, .48))
    elif key == "axon_myelin":
        if index == 0:
            _append(root, "myelin", _stroke("M22 35 H47 Q52 35 53 40 M76 35 H101 Q106 35 107 40 M22 93 H48 Q52 92 54 88 M76 88 Q79 93 84 93 H106", HI, 1.45, .73) + _stroke("M21 48 H53 M75 48 H108 M21 80 H53 M75 80 H108", SHADE, 1.1, .32))
            _append(root, "axon", _stroke("M19 61 H109", HI, 1.25, .64))
            _append(root, "periaxonal_space", _stroke("M22 54 H52 M76 54 H107 M22 74 H52 M76 74 H107", HI, .95, .8))
        else:
            _append(root, "myelin", _stroke("M43 37 A31 31 0 0 1 85 42 M36 83 A31 31 0 0 1 34 49 M48 41 A23 23 0 0 1 78 45 M42 78 A23 23 0 0 1 42 52", HI, 1.8, .78) + _stroke("M86 65 A23 23 0 0 1 81 80 M89 64 A31 31 0 0 1 78 89", SHADE, 1.3, .34))
            _append(root, "axon", _stroke("M56 55 A12 12 0 0 1 72 58", HI, 1.3, .62))
    elif key == "oligodendrocyte":
        if index == 0:
            somafacet = _facet("M24 60 Q25 48 34 45 Q43 43 50 50 Q54 56 51 69 Q46 80 34 80 Q26 76 24 68Z", HI, .31) + _facet("M30 75 Q41 82 50 70 L49 75 Q43 82 35 83Z", SHADE, .16)
            processfacet = (_tapered_profile("M52 56 Q65 42 76 26 Q78 24 80 25 Q72 43 57 62Z", "#D3CDEE") +
                            _tapered_profile("M55 61 Q66 60 79 60 L79 64 Q67 64 56 67Z", "#D3CDEE") +
                            _tapered_profile("M52 72 Q65 86 76 101 Q78 103 80 101 Q72 84 57 69Z", "#D3CDEE") +
                            _stroke("M53 58 Q65 43 77 27 M57 64 H78 M53 71 Q65 86 77 100", HI, 1.25, .72))
            myelinfacet = _stroke("M74 23 H99 M77 59 H100 M74 97 H101", HI, 1.35, .76) + _stroke("M73 30 H102 M76 66 H104 M72 104 H103", SHADE, 1.0, .28)
            axonfacet = _stroke("M77 26 H98 M80 62 H99 M76 100 H100", HI, 1.1, .72)
        else:
            somafacet = _facet("M48 61 Q49 51 57 48 Q67 46 75 54 Q79 61 75 70 Q70 79 60 79 Q51 76 48 68Z", HI, .31) + _facet("M53 72 Q65 80 75 68 L73 75 Q66 81 58 80Z", SHADE, .16)
            processfacet = (_tapered_profile("M54 57 Q43 44 31 28 Q29 26 28 28 Q35 45 50 62Z", "#D3CDEE") +
                            _tapered_profile("M70 57 Q82 43 95 28 Q97 26 98 28 Q91 45 74 62Z", "#D3CDEE") +
                            _tapered_profile("M52 70 Q41 86 29 102 Q28 104 30 105 Q46 96 58 75Z", "#D3CDEE") +
                            _tapered_profile("M72 70 Q83 86 98 102 Q100 104 102 102 Q90 85 76 68Z", "#D3CDEE") +
                            _stroke("M54 56 Q45 43 33 29 M70 56 Q80 42 94 29 M52 73 Q42 87 31 101 M72 73 Q83 87 96 101", HI, 1.2, .72))
            myelinfacet = _stroke("M22 24 H43 M83 24 H105 M19 99 H43 M84 99 H107", HI, 1.3, .76) + _stroke("M20 31 H45 M82 31 H107 M18 104 H45 M82 104 H109", SHADE, 1.0, .26)
            axonfacet = _stroke("M23 27 H43 M84 27 H104 M20 101 H43 M85 101 H106", HI, 1.05, .73)
        _append(root, "soma", somafacet)
        _append(root, "process", processfacet)
        _append(root, "myelin", myelinfacet)
        _append(root, "axon", axonfacet)
    elif key == "schwann_cell":
        if index == 0:
            _append(root, "schwann_cytoplasm", _facet("M42 44 Q56 33 76 39 L83 44 Q62 40 47 49Z", HI, .38) + _facet("M50 78 Q68 84 84 76 L79 82 Q64 88 49 82Z", SHADE, .12))
            _append(root, "ensheathment", _stroke("M39 50 Q45 46 52 46 H79 Q86 47 89 53 M40 77 Q63 82 87 77", HI, 1.35, .8))
            _append(root, "axon", _stroke("M22 61 H106", HI, 1.1, .68))
            _append(root, "periaxonal_space", _stroke("M42 54 H85 M42 74 H85", HI, .9, .82))
        else:
            _append(root, "schwann_cytoplasm", _facet("M24 42 Q31 29 47 29 Q52 31 54 37 Q47 38 43 43 Q38 49 39 56 Q42 61 51 60 Q58 59 60 53 Q64 58 68 60 Q74 59 78 55 Q81 49 77 43 Q73 38 69 37 Q73 30 85 30 Q103 36 108 48 L108 77 Q101 97 83 103 Q65 109 45 103 Q26 96 20 78Z", HI, .24) + _facet("M28 87 Q43 101 63 101 Q84 101 99 87 L95 97 Q79 108 63 108 Q43 108 31 98Z", SHADE, .11))
            _append(root, "ensheathment", _stroke("M32 39 Q29 49 34 56 Q38 61 45 61 Q52 61 56 55 M72 39 Q69 49 74 56 Q78 61 85 61 Q92 61 96 55 M32 75 Q29 85 34 92 Q38 97 45 97 Q52 97 56 91 M72 75 Q69 85 74 92 Q78 97 85 97 Q92 97 96 91", HI, 1.2, .62))
            _append(root, "axon", "".join(_stroke(f"M{x-3} {y-4} Q{x} {y-6} {x+3} {y-4}", HI, .9, .8) for x,y in ((44,46),(84,46),(44,82),(84,82))))
            _append(root, "periaxonal_space", _stroke("M38 43 Q37 49 40 53 M78 43 Q77 49 80 53 M38 79 Q37 85 40 89 M78 79 Q77 85 80 89", HI, .85, .9))
    elif key == "dendritic_spine":
        _append(root, "dendrite", _facet("M23 75 Q57 72 105 75 L105 80 Q61 78 23 82Z", HI, .29) + _facet("M23 96 Q61 103 105 97 L105 102 Q62 109 23 102Z", SHADE, .11))
        if index == 0:
            _append(root, "spine", _facet("M48 42 Q44 34 48 27 Q54 19 68 19 Q80 20 85 29 Q87 35 80 41 Q72 46 63 43 L62 69 H57 L57 44Z", HI, .36) + _facet("M70 47 Q80 43 84 35 Q87 43 80 48 L68 51Z", SHADE, .13))
        else:
            _append(root, "spine", _facet("M49 31 Q50 23 57 21 Q65 20 67 27 Q69 33 63 36 L64 69 H58 L55 36Z", HI, .4) + _facet("M61 40 L66 37 L67 69 H62Z", SHADE, .14))
        psd_facet = _stroke("M75 24 Q84 29 80 37", HI, 1.0, .58) if index == 0 else _stroke("M61 22 Q68 25 66 31", HI, .95, .58)
        _append(root, "postsynaptic_density", psd_facet)
    elif key == "axon_terminal":
        _append(root, "axon", _stroke("M22 64 Q52 62 75 65 M20 71 Q48 73 71 71", HI, 1.3, .68))
        terminalfacet = (_facet("M84 61 Q85 54 93 53 Q101 54 103 62 Q105 72 98 79 Q91 83 85 77Z", HI, .34) + _facet("M83 74 Q92 80 101 73 L98 79 Q90 84 84 78Z", SHADE, .16)) if index == 0 else (_facet("M89 47 Q90 42 96 42 Q102 43 104 49 Q104 54 99 57 Q93 56 90 53Z M89 84 Q90 79 96 79 Q102 80 104 86 Q104 91 99 94 Q93 93 90 90Z", HI, .34) + _facet("M91 53 Q97 57 102 52 L100 56 Q96 59 91 57Z M91 90 Q97 94 102 89 L100 93 Q96 96 91 94Z", SHADE, .14))
        _append(root, "terminal", terminalfacet)
        _append(root, "vesicles", "".join(_stroke(f"M{x-1.6} {y-2.4} Q{x} {y-3.5} {x+1.6} {y-2.4}", HI, .8, .92) for x,y in ((91,63),(99,69),(91,74),(95,50),(99,55),(95,87),(99,92))))
    elif key == "neuron_astrocyte_contact":
        if index == 0:
            _append(root, "neuron", _facet("M24 101 Q42 98 58 101 L60 94 Q61 90 66 88 Q70 90 71 96 L74 101 Q88 98 103 101 L103 105 Q63 110 24 105Z", HI, .34))
            _append(root, "presynaptic", _facet("M56 39 Q55 28 63 25 Q73 20 82 27 Q89 31 88 41 Q86 49 78 52 Q66 53 59 47Z", HI, .33) + _facet("M60 46 Q73 53 85 45 L83 50 Q75 56 63 51Z", SHADE, .12))
            _append(root, "astrocyte", _stroke("M109 31 Q100 37 96 46 Q94 51 91 54", HI, 1.4, .75))
            _append(root, "cleft", _stroke("M60 55 Q73 52 87 55", HI, 1.1, .87))
        else:
            _append(root, "neuron", _facet("M22 94 Q45 91 64 95 Q87 91 106 95 L106 101 Q64 106 22 101Z", HI, .27) + _facet("M43 68 Q43 62 50 61 Q57 62 58 68 Q58 73 54 76 L58 87 H52 L48 76 Q43 73 43 68Z", HI, .29))
            _append(root, "presynaptic", _facet("M43 44 Q43 39 51 39 Q59 39 61 45 L61 51 Q55 55 48 53Z M77 44 Q77 39 85 39 Q93 39 95 45 L95 51 Q89 55 82 53Z", HI, .35))
            _append(root, "astrocyte", _stroke("M69 99 Q68 80 71 69 Q74 57 71 49 Q69 38 75 30 M67 48 Q63 33 54 24 M74 47 Q84 34 98 25", HI, 1.4, .73))
            _append(root, "cleft", _stroke("M43 57 Q52 55 61 57 M77 57 Q86 55 95 57", HI, .95, .86))
    elif key == "microglia_contact":
        process_facet = (_stroke("M57 57 Q47 45 33 37 M54 64 Q42 61 29 56 M55 71 Q41 77 29 89 M71 57 Q82 44 97 34 M74 64 Q88 63 102 60 M70 73 Q78 80 83 84", HI, 1.25, .68) if index == 0 else _stroke("M55 63 Q62 59 66 63 Q72 69 78 69 M47 53 Q35 44 22 34 M31 64 Q28 61 17 56 M31 64 Q28 78 19 94 M48 75 Q51 87 64 98 M31 57 Q35 48 39 35", HI, 1.2, .68))
        _append(root, "process", process_facet)
        if index == 0:
            _append(root, "microglia", _facet("M56 61 Q58 52 66 52 Q74 53 76 61 Q76 70 68 75 Q60 75 56 68Z", HI, .35) + _facet("M57 69 Q65 75 73 68 L70 74 Q63 78 58 73Z", SHADE, .13))
        else:
            _append(root, "microglia", _facet("M35 61 Q37 53 44 52 Q52 53 54 61 Q54 69 47 74 Q39 74 35 68Z", HI, .35) + _facet("M36 68 Q44 75 52 68 L49 74 Q42 78 37 73Z", SHADE, .13))
            _append(root, "neural_target", _facet("M80 61 Q81 55 87 54 Q94 53 98 60 Q100 67 95 72 Q89 76 83 71Z", HI, .28))
    elif key == "node_of_ranvier":
        _append(root, "axon", _stroke("M21 61 H107", HI, 1.25, .7))
        if index == 0:
            _append(root, "myelin", _stroke("M22 50 H48 Q52 50 53 55 M75 55 Q77 50 82 50 H105 M22 78 H49 M80 78 H105", HI, 1.5, .72) + _stroke("M22 80 H51 M77 80 H105", SHADE, 1.0, .26))
            _append(root, "nodal_region", _facet("M59 54 H69 V76 H59Z", HI, .27))
        else:
            _append(root, "myelin", _stroke("M19 49 H44 Q51 49 53 55 M75 55 Q78 49 85 49 H109 M19 79 H45 M82 79 H109", HI, 1.45, .73))
            _append(root, "nodal_region", "".join(f'<circle cx="{x}" cy="{y}" r="1.35" fill="#FFF7E8"/>' for x,y in ((61,56),(67,56),(61,64),(67,64),(61,71),(67,71))))
    elif key == "neural_circuit":
        if index == 0:
            neuronfacet = _facet("M18 60 Q19 55 26 55 Q33 55 34 62 Q34 69 27 72 Q20 71 18 66Z M56 60 Q57 55 64 55 Q71 55 72 62 Q72 69 65 72 Q58 71 56 66Z M94 60 Q95 55 102 55 Q109 55 110 62 Q110 69 103 72 Q96 71 94 66Z", HI, .31)
            connectionfacet = _stroke("M39 61 H50 M77 61 H88", HI, 1.1, .74)
        else:
            neuronfacet = _facet("M18 29 Q19 24 27 23 Q35 24 37 31 Q37 39 29 42 Q21 41 18 35Z M18 88 Q19 83 27 82 Q35 83 37 90 Q37 98 29 101 Q21 100 18 94Z M58 58 Q60 51 68 50 Q77 51 80 60 Q80 69 72 74 Q62 73 58 66Z M94 59 Q95 54 103 53 Q111 54 113 62 Q113 70 105 73 Q97 72 94 66Z", HI, .31)
            connectionfacet = _stroke("M40 36 Q46 39 52 52 M40 92 Q46 89 52 76 M83 64 H91", HI, 1.1, .74)
        _append(root, "neuron", neuronfacet)
        _append(root, "connection", connectionfacet)


def render_svg(key: str, index: int, title: str, description: str) -> str:
    """Return one accessible, editable Style 4 SVG companion at 128 px."""
    if key not in _FORM_IDS:
        raise KeyError(key)
    if index not in (0, 1):
        raise IndexError("form index must be 0 or 1")
    root = ET.fromstring(_BASE.render_svg(key, index, title, description))
    root.set("data-asset", f"neuro.{key}.{_FORM_IDS[key][index]}")
    root.set("data-illustration-style", "Style 4")
    parents = {child: parent for parent in root.iter() for child in parent}

    def in_outline(element: ET.Element) -> bool:
        current = element
        while current is not root:
            if current.get("data-region") == "outline":
                return True
            current = parents.get(current, root)
        return False

    for element in root.iter():
        region = element.get("data-region")
        if region is not None:
            paint = STYLE4_DEFAULT_PAINTS.get(region)
            if element.get("fill") not in (None, "none") and paint:
                element.set("fill", paint)
            if element.get("stroke") not in (None, "none") and paint:
                element.set("stroke", paint if region != "outline" else "#2B3642")
        if element.get("stroke-width") and in_outline(element):
            width = float(element.get("stroke-width", "1"))
            if width >= 2:
                element.set("stroke-width", "0.95")
            elif width > 1:
                element.set("stroke-width", "0.8")
        if element.tag == _q("title"):
            element.text = title
        elif element.tag == _q("desc"):
            element.text = description
    _depth_art(key, index, root)
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)
