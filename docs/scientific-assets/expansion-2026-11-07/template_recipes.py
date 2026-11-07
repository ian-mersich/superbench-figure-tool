"""Original editable endocrine Figure Studio scene recipes (2026-11-07).

Authoring source only; asset forms resolve to first authored endocrine forms.
"""
from __future__ import annotations

from copy import deepcopy

SCHEMA = "figureStudio.scientificScene.v1"
SOURCE_RECORD = "source.figure-studio-scene-expansion.2026-11-07"
RIGHTS_RECORD = "rights.figure-studio-scene-expansion.repository-cc0.2026-11-07"

# Stable first forms from the separately authored endocrine asset concepts.
ASSET_BINDINGS = {
    "adrenal_cortex": "endocrine.adrenal_cortex.concentric_zones",
    "anterior_pituitary": "endocrine.anterior_pituitary.cords_longitudinal",
    "median_eminence": "endocrine.median_eminence.external_zone_sagittal",
    "thyroid_follicle": "endocrine.thyroid_follicle.single_follicle",
    "pancreatic_islet": "endocrine.pancreatic_islet.mixed_islet",
}

SOURCE_RECORD_DATA = {
    "id": SOURCE_RECORD,
    "created_on": "2026-11-07",
    "scope": "Original editable endocrine schematics composed from native Figure Studio vector objects and separately authored endocrine assets.",
    "authorship": "Clean-room original. Primary literature informs biological relationships and experimental conventions only; no published artwork or inherited attestations are included.",
}
RIGHTS_RECORD_DATA = {
    "id": RIGHTS_RECORD,
    "created_on": "2026-11-07",
    "license": "CC0-1.0",
    "basis": "Original work released under the repository's CC0 policy.",
}

REFERENCES = {
    "hpa-guide": {
        "citation": "Spencer RL, Deak T. A user's guide to HPA axis research. Physiol Behav. 2017;178:43–65. doi:10.1016/j.physbeh.2016.11.014.",
        "doi": "10.1016/j.physbeh.2016.11.014",
        "url": "https://pubmed.ncbi.nlm.nih.gov/27871862/",
        "support_location": "Overview of hypothalamic CRH, pituitary ACTH, adrenal glucocorticoid secretion, and glucocorticoid feedback.",
    },
    "hpa-feedback-primary": {
        "citation": "Osterlund CD, Rodriguez-Santiago M, Woodruff ER, Newsom RJ, Chadayammuri AP, Spencer RL. Glucocorticoid fast feedback inhibition of stress-induced ACTH secretion in the male rat: rate independence and stress-state resistance. Endocrinology. 2016;157(7):2785–2798. doi:10.1210/en.2016-1123.",
        "doi": "10.1210/en.2016-1123",
        "url": "https://pubmed.ncbi.nlm.nih.gov/27145013/",
        "support_location": "Rat in-vivo corticosterone infusion experiments show feedback inhibition of stress-induced ACTH and CRH responses, supporting qualitative upstream inhibitory links.",
    },
    "hpt-primary": {
        "citation": "Segerson TP et al. Thyroid hormone regulates TRH biosynthesis in the paraventricular nucleus of the rat hypothalamus. Science. 1987;238(4823):78–80. doi:10.1126/science.3116669.",
        "doi": "10.1126/science.3116669",
        "url": "https://pubmed.ncbi.nlm.nih.gov/3116669/",
        "support_location": "Rat thyroid-hormone manipulation experiments show reduced hypothalamic proTRH mRNA, supporting feedback from thyroid hormone to the TRH-producing hypothalamic population.",
    },
    "hpt-pituitary": {
        "citation": "Samuels MH, Wierman A, Wang C, Ridgway EC. The effect of altered thyroid status on pituitary hormone messenger ribonucleic acid concentrations in the rat. Endocrinology. 1989;124(5):2277–2282.",
        "doi": "10.1210/endo-124-5-2277",
        "url": "https://pubmed.ncbi.nlm.nih.gov/2495926/",
        "support_location": "Rat thyroid-status experiments measured pituitary TSH-subunit expression and support thyroid-hormone feedback at the pituitary level.",
    },
    "islet-human": {
        "citation": "Rodriguez-Diaz R et al. Paracrine interactions within the pancreatic islet determine the glycemic set point. Cell Metab. 2018;27(3):549–558.e4. doi:10.1016/j.cmet.2018.01.015.",
        "doi": "10.1016/j.cmet.2018.01.015",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5860066/",
        "support_location": "Primary human-islet experiments on intra-islet paracrine signaling and glucose regulation; this schematic limits itself to glucose-responsive insulin and does not imply a universal set point.",
    },
    "insulin-human": {
        "citation": "Campbell PJ, Mandarino LJ, Gerich JE. Quantification of the relative impairment in actions of insulin on hepatic glucose production and peripheral glucose uptake in non-insulin-dependent diabetes mellitus. Metabolism. 1988;37(1):15–21. doi:10.1016/0026-0495(88)90023-6.",
        "doi": "10.1016/0026-0495(88)90023-6",
        "url": "https://pubmed.ncbi.nlm.nih.gov/3275857/",
        "support_location": "Human glucose-clamp and isotope-flux study measured insulin-mediated suppression of hepatic glucose production and stimulation of peripheral glucose uptake; effects vary with diabetes status and insulin concentration.",
    },
    "perifusion-human": {
        "citation": "Buchwald P, Chuang ST, Watts B, Alcazar O. Assessing the rate dependence of the first phase of glucose-stimulated insulin secretion: dynamic perifusion studies with isolated human pancreatic islets. Am J Physiol Endocrinol Metab. 2025;329(6):E937–E950. doi:10.1152/ajpendo.00307.2025.",
        "doi": "10.1152/ajpendo.00307.2025",
        "url": "https://pubmed.ncbi.nlm.nih.gov/41247797/",
        "support_location": "Methods describe controlled inflow through isolated islets, sequential glucose conditions, outflow fraction collection, and insulin measurement; Figure 1 shows the apparatus concept.",
    },
    "perifusion-protocol": {
        "citation": "Wang X, Misawa R, et al. Detailed protocol for evaluation of dynamic perifusion of human islets to assess β-cell function. J Vis Exp. 2012;(62):e3702. doi:10.3791/3702.",
        "doi": "10.3791/3702",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3219161/",
        "support_location": "Protocol describes islet loading, continuous perfusion, sequential media changes, timed fraction collection, and downstream insulin measurement.",
    },
}

ENTRIES = [
    {
        "id": "hypothalamic-pituitary-adrenal-axis", "name": "Hypothalamic–pituitary–adrenal axis",
        "summary": "Stress-related hypothalamic drive, pituitary ACTH, adrenal glucocorticoid output, and negative feedback.",
        "category": "Endocrinology", "synonyms": ["HPA axis", "hypothalamic–pituitary–adrenal axis", "corticotropin axis"],
        "tags": ["CRH", "ACTH", "cortisol", "glucocorticoid", "negative feedback", "stress response"],
        "biology_note": "Parvocellular hypothalamic neurons release CRH into the median eminence portal circulation. CRH stimulates anterior-pituitary corticotrophs to release ACTH, which stimulates glucocorticoid synthesis and release from the adrenal cortex. Glucocorticoids feed back to reduce hypothalamic and pituitary drive.",
        "limitations": "Qualitative overview. Vasopressin co-drive, circadian and ultradian dynamics, species-specific glucocorticoids, and distributed neural inputs are not resolved; the diagram does not predict hormone concentrations or response timing.",
        "asset_keys": ["median_eminence", "anterior_pituitary", "adrenal_cortex"],
        "source_ids": ["hpa-guide", "hpa-feedback-primary"],
        "decisions": ["Use three anatomically ordered endocrine stations with portal CRH delivery to the anterior pituitary and circulating ACTH to the adrenal cortex.", "Show glucocorticoid feedback to both hypothalamic drive and pituitary corticotroph output with dashed inhibition-bar connectors; the marks denote qualitative inhibition, not quantitative strength."],
    },
    {
        "id": "hypothalamic-pituitary-thyroid-axis", "name": "Hypothalamic–pituitary–thyroid axis",
        "summary": "Hypothalamic TRH drives pituitary TSH and thyroid follicular T4/T3 output under feedback control.",
        "category": "Endocrinology", "synonyms": ["HPT axis", "thyroid axis", "hypothalamic–pituitary–thyroid axis"],
        "tags": ["TRH", "TSH", "thyroid follicle", "T4", "T3", "negative feedback"],
        "biology_note": "Hypothalamic TRH stimulates pituitary thyrotrophs to release TSH. TSH stimulates thyroid follicular synthesis and secretion of T4 and T3. Thyroid hormones reduce upstream TRH and TSH synthesis or secretion through feedback at hypothalamic and pituitary levels.",
        "limitations": "Qualitative overview. It omits local deiodinase activity, transport and binding proteins, iodine availability, illness-related regulation, and the distinct kinetics of TSH and thyroid hormones. No diagnostic reference ranges or concentrations are implied.",
        "asset_keys": ["median_eminence", "anterior_pituitary", "thyroid_follicle"],
        "source_ids": ["hpt-primary", "hpt-pituitary"],
        "decisions": ["Distinguish TRH delivery through the median eminence from circulating TSH action on a thyroid follicle; label the glandular products as T4 and T3.", "Route thyroid-hormone feedback separately to hypothalamic TRH neurons and pituitary thyrotrophs using dashed inhibition bars. The follicle is shown as an endocrine source, not a histological micrograph."],
    },
    {
        "id": "glucose-islet-feedback", "name": "Glucose–islet insulin feedback",
        "summary": "Rising extracellular glucose stimulates islet insulin release, promoting peripheral uptake and restraining hepatic glucose output.",
        "category": "Endocrinology", "synonyms": ["glucose–insulin feedback", "islet glucose sensing", "insulin-mediated glucose control"],
        "tags": ["extracellular glucose", "pancreatic islet", "beta cell", "insulin", "glucose uptake", "hepatic output"],
        "biology_note": "Elevated glucose stimulates insulin secretion from pancreatic islet β cells. Insulin promotes glucose uptake in insulin-responsive peripheral tissues and suppresses endogenous hepatic glucose production, tending to lower circulating glucose.",
        "limitations": "Qualitative conceptual loop. Insulin action varies by tissue, nutritional state, species, and disease context; glucose uptake is not uniform across all tissues. Glucagon and other hormones are omitted, and no universal set point or response rate is shown.",
        "asset_keys": ["pancreatic_islet"],
        "source_ids": ["islet-human", "insulin-human"],
        "decisions": ["Use primary human-islet evidence to orient elevated extracellular glucose upstream of islet insulin release.", "Represent insulin's actions as separate branches to peripheral glucose uptake and lower endogenous hepatic glucose production, as measured in human clamp studies; converge the branches on a qualitative lower-glucose outcome without implying universal rates."],
    },
    {
        "id": "islet-perifusion-experiment", "name": "Islet perifusion experiment",
        "summary": "Perfuse isolated islets through sequential media, collect timed effluent fractions, and measure secreted hormone.",
        "category": "Endocrine methods", "synonyms": ["islet perifusion", "islet perifusion assay", "dynamic glucose-stimulated insulin secretion"],
        "tags": ["isolated islets", "perifusion chamber", "inflow", "outflow", "fraction collection", "stimulus washout"],
        "biology_note": "A controlled medium stream passes through a chamber containing isolated islets. Outflow is collected in timed fractions for hormone measurement while the incoming medium changes across basal, stimulus, and washout periods.",
        "limitations": "Experimental-layout schematic only. It contains no measured secretion trace, concentration, sample number, flow rate, stimulus concentration, or expected response shape. Chamber geometry, equilibration, fraction interval, assay, and stimulus sequence must match the actual experiment.",
        "asset_keys": ["pancreatic_islet"],
        "source_ids": ["perifusion-human", "perifusion-protocol"],
        "decisions": ["Make the apparatus the main visual: inlet and medium selector feed a chamber with islets, then an outlet feeds sequential fraction tubes.", "Show a generic basal → stimulus → washout schedule and an empty readout frame to be populated with measured values; no response curve or protocol-specific concentrations are supplied."],
    },
]

_PALETTE = {
    "background": "#F7F9FC", "surface": "#FFFFFF", "ink": "#24313B",
    "muted": "#637381", "border": "#C9D5DE", "sample": "#2A8C82",
    "process": "#527DA8", "signal": "#D79A31", "inhibition": "#B94E49",
    "soft": "#E7EEF4", "accent": "#7667A8",
}


def _text(i, text, x, y, w, h=28, size=20, role="ink", align="center"):
    return {"id": i, "type": "text", "layer_id": "labels", "x": x, "y": y, "width": w, "height": h,
            "text": text, "placeholder": True, "editable": True, "font_size": size, "fill_role": role, "align": align}


def _shape(i, shape, x, y, w, h, fill="surface", stroke="border", radius=18, layer="objects"):
    return {"id": i, "type": "shape", "shape": shape, "layer_id": layer, "x": x, "y": y, "width": w, "height": h,
            "radius": radius, "fill_role": fill, "stroke_role": stroke, "stroke_width": 2.2}


_ASSET_REGIONS = {
    "median_eminence": {"neural": "process", "terminal": "signal", "boundary": "border", "sinusoid": "sample", "outline": "ink"},
    "anterior_pituitary": {"gland": "process", "sinusoid": "sample", "outline": "ink"},
    "adrenal_cortex": {"capsule": "border", "zona_glomerulosa": "sample", "zona_fasciculata": "signal", "zona_reticularis": "accent", "medulla": "inhibition", "outline": "ink"},
    "thyroid_follicle": {"follicular_epithelium": "process", "colloid": "signal", "stroma": "soft", "outline": "ink"},
    "pancreatic_islet": {"beta_cells": "signal", "other_endocrine": "accent", "capillary": "inhibition", "stroma": "soft", "outline": "ink"},
}


def _asset(i, key, x, y, w, h, layer="objects"):
    return {"id": i, "name": i.replace("_", " ").title(), "type": "asset", "layer_id": layer,
            "asset_id": ASSET_BINDINGS[key], "top_level": True, "x": x, "y": y, "width": w, "height": h,
            "palette_overrides": dict(_ASSET_REGIONS[key])}


def _edge(i, a, b, label, relation="activation", role="process", terminator="arrow", line="solid", route=None, offset=None):
    style = {"stroke_role": role, "stroke_width": 2.6, "line": line, "terminator": terminator}
    if route: style["route"] = route
    if offset: style["label_offset"] = {"x": offset[0], "y": offset[1]}
    return {"id": i, "layer_id": "relationships", "from": {"node_id": a, "anchor": "right"},
            "to": {"node_id": b, "anchor": "left"}, "relation": relation, "label": label, "style": style}


def _group(i, name, members, layer="objects"):
    return {"id": i, "name": name, "layer_id": layer, "members": list(members)}


def _base(entry, width=1100, height=650, subtitle=""):
    return {
        "schema": SCHEMA, "id": entry["id"], "name": entry["name"], "summary": entry["summary"],
        "source_record_id": SOURCE_RECORD, "rights_record_id": RIGHTS_RECORD,
        "scientific_record": {
            "id": "science.figure-studio." + entry["id"] + ".2026-11-07", "verified_on": "2026-11-07",
            "scope": entry["biology_note"],
            "relationships": [{"claim": entry["biology_note"], "source_ids": entry["source_ids"]}],
            "sources": [dict({"id": sid}, **REFERENCES[sid], decision=entry["decisions"][min(i, len(entry["decisions"])-1)]) for i, sid in enumerate(entry["source_ids"])],
            "design_precedents": [{"source_id": sid, "figure": "Methods / conceptual figure", "decision": decision}
                                  for sid, decision in zip(entry["source_ids"], entry["decisions"])],
            "limitations": [entry["limitations"]],
            "authorship": "Original editable scene composed from native vector/text objects and original endocrine asset placeholders. Published research informed biological claims and design decisions only; no publication artwork was copied, traced, or embedded.",
        },
        "insertion_art_style": "soft-color", "canvas": {"width": width, "height": height, "width_in": width/96, "height_in": height/96, "background_role": "background"},
        "layout_kind": "experiment" if entry["id"] == "islet-perifusion-experiment" else "mechanism",
        "palette": deepcopy(_PALETTE),
        "layers": [{"id": "context", "name": "Anatomical and assay context"}, {"id": "objects", "name": "Endocrine structures and apparatus"},
                   {"id": "relationships", "name": "Hormone and experimental relationships"}, {"id": "labels", "name": "Editable labels"}],
        "nodes": [_text("title", entry["name"], 36, 22, width-72, 34, 27, "ink", "left")],
        "groups": [], "connectors": [],
    }


def _hpa(e):
    s = _base(e); n=s["nodes"]
    n += [_text("subtitle", "Stress-related hypothalamic drive → ACTH → adrenal glucocorticoid output", 38, 60, 1024, 27, 19, "muted", "left"),
          _shape("portal_band", "rounded_rect", 52, 132, 254, 285, "soft", "border"),
          _shape("pituitary_band", "rounded_rect", 423, 132, 254, 285, "surface", "border"),
          _shape("adrenal_band", "rounded_rect", 794, 132, 254, 285, "soft", "border"),
          _asset("median_eminence", "median_eminence", 108, 196, 142, 116),
          _asset("anterior_pituitary", "anterior_pituitary", 479, 196, 142, 116),
          _asset("adrenal_cortex", "adrenal_cortex", 850, 196, 142, 116),
          _text("hypothalamus_label", "Hypothalamic CRH neurons", 68, 145, 222, 50, 20, "ink"),
          _text("median_label", "Median eminence", 68, 326, 222, 27, 19, "process"),
          _text("pituitary_label", "Anterior pituitary", 439, 145, 222, 30, 20, "ink"),
          _text("corticotroph_label", "Corticotroph", 439, 326, 222, 27, 19, "process"),
          _text("adrenal_label", "Adrenal cortex", 810, 145, 222, 30, 20, "ink"),
          _text("zona_label", "Glucocorticoid secretion", 810, 326, 222, 50, 19, "signal"),
          _text("crh_label", "CRH · portal blood", 269, 211, 190, 30, 18, "process"),
          _text("acth_label", "ACTH · circulation", 640, 211, 190, 30, 18, "process"),
          _shape("glucocorticoid_pool", "ellipse", 830, 464, 182, 48, "surface", "signal", 24, "context"),
          _text("glucocorticoid_pool_label", "Glucocorticoids", 840, 476, 162, 26, 18, "signal"),
          _text("crh_feedback_label", "Reduced CRH drive", 220, 558, 260, 30, 20, "inhibition"),
          _text("acth_feedback_label", "Reduced ACTH drive", 600, 558, 260, 30, 20, "inhibition")]
    s["groups"] = [
        _group("hypothalamic_portal_unit", "Hypothalamic CRH and portal release", ["portal_band", "median_eminence", "hypothalamus_label", "median_label", "crh_label"]),
        _group("pituitary_corticotroph_unit", "Anterior-pituitary corticotroph", ["pituitary_band", "anterior_pituitary", "pituitary_label", "corticotroph_label", "acth_label"]),
        _group("adrenal_glucocorticoid_unit", "Adrenal glucocorticoid output", ["adrenal_band", "adrenal_cortex", "adrenal_label", "zona_label"]),
        _group("feedback_hormone", "Circulating glucocorticoid feedback", ["glucocorticoid_pool", "glucocorticoid_pool_label", "crh_feedback_label", "acth_feedback_label"], "context"),
    ]
    s["connectors"]=[_edge("crh_to_corticotroph","median_eminence","anterior_pituitary","CRH", "activation", "process", offset=(0,-26)),
                      _edge("acth_to_adrenal","anterior_pituitary","adrenal_cortex","ACTH", "activation", "process", offset=(0,-26)),
                      {"id":"adrenal_release_to_pool","layer_id":"relationships","from":{"node_id":"adrenal_band","anchor":"bottom"},"to":{"node_id":"glucocorticoid_pool","anchor":"top"},"relation":"secretion","label":"release","style":{"stroke_role":"signal","stroke_width":2.4,"line":"solid","terminator":"arrow"}},
                      {"id":"cortisol_to_hypothalamus","layer_id":"relationships","from":{"node_id":"glucocorticoid_pool","anchor":"bottom"},"to":{"node_id":"portal_band","anchor":"bottom"},"relation":"inhibition","label":"reduces CRH drive","style":{"stroke_role":"inhibition","stroke_width":2.6,"line":"dashed","terminator":"bar","route":"elbow","label_offset":{"x":-130,"y":10}}},
                      {"id":"cortisol_to_pituitary","layer_id":"relationships","from":{"node_id":"glucocorticoid_pool","anchor":"bottom"},"to":{"node_id":"pituitary_band","anchor":"bottom"},"relation":"inhibition","label":"reduces ACTH drive","style":{"stroke_role":"inhibition","stroke_width":2.6,"line":"dashed","terminator":"bar","route":"elbow","label_offset":{"x":70,"y":10}}}]
    return s


def _hpt(e):
    s=_base(e); n=s["nodes"]
    n += [_text("subtitle","TRH and TSH drive thyroid-hormone synthesis; T3/T4 feed back at hypothalamus and pituitary",38,60,1024,27,19,"muted","left"),
          _shape("brain_region","rounded_rect",55,138,232,286,"soft","border"),
          _shape("pit_region","rounded_rect",363,138,232,286,"surface","border"),
          _shape("follicle_region","rounded_rect",671,125,378,312,"soft","border"),
          _asset("median_eminence","median_eminence",104,207,132,104),
          _asset("anterior_pituitary","anterior_pituitary",413,207,132,104),
          _asset("thyroid_follicle","thyroid_follicle",758,190,204,142),
          _text("hypothalamus_label","Hypothalamus",69,153,204,28,20),
          _text("trh_neurons","TRH neurons",69,332,204,27,19,"process"),
          _text("pituitary_label","Anterior pituitary",377,153,204,28,20),
          _text("thyrotroph_label","Thyrotroph",377,332,204,27,19,"process"),
          _text("follicle_label","Thyroid follicle",694,145,330,28,20),
          _text("products_label","T4 + T3 secretion",694,351,330,27,20,"signal"),
          _text("trh_label","TRH",287,203,76,32,19,"process"),_text("tsh_label","TSH",595,203,76,32,19,"process"),
          _shape("thyroid_hormone_pool","ellipse",810,468,156,48,"surface","signal",24,"context"),
          _text("thyroid_hormone_pool_label","T4 / T3",820,478,136,26,19,"signal"),
          _text("trh_feedback_label","Reduced TRH drive",184,560,260,30,20,"inhibition"),
          _text("tsh_feedback_label","Reduced TSH drive",550,560,260,30,20,"inhibition")]
    s["groups"] = [
        _group("hypothalamic_trh_unit", "Hypothalamic TRH release", ["brain_region", "median_eminence", "hypothalamus_label", "trh_neurons", "trh_label"]),
        _group("pituitary_tsh_unit", "Anterior-pituitary TSH release", ["pit_region", "anterior_pituitary", "pituitary_label", "thyrotroph_label", "tsh_label"]),
        _group("thyroid_follicle_unit", "Thyroid follicular hormone output", ["follicle_region", "thyroid_follicle", "follicle_label", "products_label"]),
        _group("thyroid_feedback_hormones", "Circulating thyroid hormones", ["thyroid_hormone_pool", "thyroid_hormone_pool_label", "trh_feedback_label", "tsh_feedback_label"], "context"),
    ]
    s["connectors"]=[_edge("trh_to_tsh","median_eminence","anterior_pituitary","TRH", "activation","process",offset=(0,-25)),
                      _edge("tsh_to_follicle","anterior_pituitary","thyroid_follicle","TSH", "activation","process",offset=(0,-25)),
                      {"id":"follicle_release_to_pool","layer_id":"relationships","from":{"node_id":"follicle_region","anchor":"bottom"},"to":{"node_id":"thyroid_hormone_pool","anchor":"top"},"relation":"secretion","label":"release","style":{"stroke_role":"signal","stroke_width":2.4,"line":"solid","terminator":"arrow"}},
                      {"id":"thyroid_feedback_hypothalamus","layer_id":"relationships","from":{"node_id":"thyroid_hormone_pool","anchor":"bottom"},"to":{"node_id":"brain_region","anchor":"bottom"},"relation":"inhibition","label":"reduces TRH drive","style":{"stroke_role":"inhibition","stroke_width":2.5,"line":"dashed","terminator":"bar","route":"elbow","label_offset":{"x":-120,"y":8}}},
                      {"id":"thyroid_feedback_pituitary","layer_id":"relationships","from":{"node_id":"thyroid_hormone_pool","anchor":"bottom"},"to":{"node_id":"pit_region","anchor":"bottom"},"relation":"inhibition","label":"reduces TSH drive","style":{"stroke_role":"inhibition","stroke_width":2.5,"line":"dashed","terminator":"bar","route":"elbow","label_offset":{"x":65,"y":8}}}]
    return s


def _glucose(e):
    s = _base(e)
    s['nodes'] += [
        _text('subtitle', 'Glucose-responsive insulin release and glucose-lowering actions', 38, 60, 1024, 28, 20, 'muted', 'left'),
        _shape('glucose_pool', 'ellipse', 60, 224, 190, 112, 'soft', 'sample', 56),
        _text('glucose_label', 'Glucose rises', 76, 260, 158, 36, 22, 'sample'),
        _shape('islet_region', 'rounded_rect', 344, 156, 250, 262, 'surface', 'border'),
        _asset('pancreatic_islet', 'pancreatic_islet', 391, 211, 156, 128),
        _text('islet_label', 'Pancreatic islet', 361, 169, 216, 30, 21),
        _text('beta_label', 'β-cell insulin release', 361, 359, 216, 50, 20, 'signal'),
        _shape('insulin_action', 'rounded_rect', 760, 156, 290, 262, 'surface', 'border'),
        _text('action_title', 'Insulin action', 778, 174, 254, 34, 22, 'signal'),
        _text('peripheral_label', 'Muscle + adipose tissue', 778, 237, 254, 28, 20),
        _text('uptake_label', 'Glucose uptake ↑', 778, 270, 254, 28, 20, 'process'),
        _text('liver_label', 'Liver', 778, 321, 254, 28, 20),
        _text('hepatic_label', 'Glucose production ↓', 778, 354, 254, 28, 20, 'process'),
        _text('insulin_label', 'Insulin', 597, 225, 160, 30, 21, 'signal'),
        _shape('net_glucose_response', 'rounded_rect', 364, 500, 536, 64, 'soft', 'inhibition', 16, 'context'),
        _text('net_glucose_response_label', 'Extracellular glucose falls', 380, 516, 504, 32, 22, 'inhibition'),
        _text('feedback_label', 'Negative feedback', 20, 430, 235, 30, 20, 'inhibition'),
    ]
    s['groups'] = [
        _group('glucose_input', 'Extracellular glucose', ['glucose_pool','glucose_label'], 'context'),
        _group('islet_insulin_source', 'Islet insulin release', ['islet_region','pancreatic_islet','islet_label','beta_label','insulin_label']),
        _group('insulin_action_group', 'Distinct peripheral and hepatic insulin actions', ['insulin_action','action_title','peripheral_label','uptake_label','liver_label','hepatic_label']),
        _group('net_glucose_response_group', 'Combined glucose response', ['net_glucose_response','net_glucose_response_label','feedback_label'], 'context'),
    ]
    s['connectors'] = [
        _edge('glucose_stimulates_islet','glucose_pool','pancreatic_islet','', 'activation','sample'),
        _edge('islet_insulin','pancreatic_islet','insulin_action','', 'secretion','signal'),
        {'id':'insulin_actions_lower_glucose','layer_id':'relationships','from':{'node_id':'insulin_action','anchor':'bottom'},'to':{'node_id':'net_glucose_response','anchor':'top'},'relation':'conversion','label':'','style':{'stroke_role':'process','stroke_width':2.5,'line':'solid','terminator':'arrow'}},
        {'id':'net_glucose_feedback','layer_id':'relationships','from':{'node_id':'net_glucose_response','anchor':'left'},'to':{'node_id':'glucose_pool','anchor':'bottom'},'relation':'inhibition','label':'','style':{'stroke_role':'inhibition','stroke_width':2.5,'line':'dashed','terminator':'bar'}},
    ]
    return s


def _perifusion(e):
    s=_base(e,1100,650); n=s["nodes"]
    n += [_text("subtitle","Controlled inflow, chamber residence, timed effluent fractions, hormone assay",38,60,1024,27,19,"muted","left"),
          _shape("media_bottle","rounded_rect",56,169,150,126,"surface","border",18),
          _text("media_label","Inlet medium",68,188,126,30,20),
          _text("media_note","basal / stimulus / washout",66,226,130,66,17,"muted"),
          _shape("selector","rounded_rect",265,190,150,82,"soft","process",18),
          _text("selector_label","Media selector",276,214,128,50,20,"process"),
          _shape("chamber","rounded_rect",485,148,223,166,"surface","sample",24),
          _asset("pancreatic_islet","pancreatic_islet",528,176,138,108),
          _text("chamber_label","Islets in chamber",494,319,205,28,19,"sample"),
          _shape("collector","rounded_rect",831,150,216,180,"soft","border",18),
          _text("collector_label","Timed fraction collector",845,164,188,48,20),
          _text("fraction_label","Sequential fractions",842,280,194,30,18,"muted"),
          _shape("tube1","rounded_rect",868,225,25,38,"surface","process",7),
          _shape("tube2","rounded_rect",904,225,25,38,"surface","process",7),
          _shape("tube3","rounded_rect",940,225,25,38,"surface","process",7),
          _shape("tube4","rounded_rect",976,225,25,38,"surface","process",7),
          _shape("timeline","rounded_rect",54,392,992,90,"surface","border",16,"context"),
          _shape("basal_bar","rounded_rect",78,423,260,32,"soft","process",12,"context"),
          _shape("stimulus_bar","rounded_rect",338,423,408,32,"soft","signal",12,"context"),
          _shape("washout_bar","rounded_rect",746,423,276,32,"soft","sample",12,"context"),
          _text("basal","Basal",78,395,260,24,18,"process"),_text("stimulus","Stimulus",338,395,408,24,18,"signal"),_text("washout","Washout",746,395,276,24,18,"sample"),
          _text("time_axis","Time / fractions",74,458,952,25,17,"muted"),
          _shape("readout_frame","rounded_rect",250,518,600,54,"surface","border",14,"context"),
          _text("readout_label","Insulin per fraction: add measurements",270,531,560,30,20,"muted"),
          ]
    s["groups"] = [
        _group("inflow_conditioning", "Medium supply and switching", ["media_bottle", "media_label", "media_note", "selector", "selector_label"], "context"),
        _group("islet_chamber", "Perifusion chamber", ["chamber", "pancreatic_islet", "chamber_label"]),
        _group("fraction_collection", "Timed effluent fractions", ["collector", "collector_label", "fraction_label", "tube1", "tube2", "tube3", "tube4"]),
        _group("protocol_phases", "Basal, stimulus, and washout periods", ["timeline", "basal_bar", "stimulus_bar", "washout_bar", "basal", "stimulus", "washout", "time_axis"], "context"),
        _group("readout_placeholder", "Editable hormone readout space", ["readout_frame", "readout_label"], "context"),
    ]
    s["connectors"]=[_edge("medium_to_selector","media_bottle","selector","", "transport","process"),
                      _edge("selector_to_chamber","selector","chamber","", "transport","process"),
                      _edge("chamber_to_collector","chamber","collector","", "transport","process")]
    return s


def make_scenes() -> list[dict]:
    """Return independent editable scene recipes in stable ENTRIES order."""
    builders = {
        "hypothalamic-pituitary-adrenal-axis": _hpa,
        "hypothalamic-pituitary-thyroid-axis": _hpt,
        "glucose-islet-feedback": _glucose,
        "islet-perifusion-experiment": _perifusion,
    }
    scenes = [builders[e["id"]](e) for e in ENTRIES]
    # Relationship names remain in stable IDs and scientific records. Visible
    # labels are explicit editable nodes positioned clear of connector paths.
    for scene in scenes:
        for connector in scene['connectors']:
            connector['label'] = ''
    return scenes

