"""Original editable Figure Studio scene recipes for the 2026-11-03 expansion.

This is an authoring source, not a shipped catalog.  It returns recipes in the
existing ``figureStudio.scientificScene.v1`` shape so the owning release lane
can review and promote individual scenes with previews and rights records.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


SCHEMA = "figureStudio.scientificScene.v1"
SOURCE_RECORD = "source.figure-studio-scene-expansion.2026-11-03"
RIGHTS_RECORD = "rights.figure-studio-scene-expansion.repository-cc0.2026-11-03"


REFERENCES = {
    "bustin-2009": {
        "citation": "Bustin SA et al. The MIQE guidelines: minimum information for publication of quantitative real-time PCR experiments. Clinical Chemistry. 2009;55:611–622.",
        "doi": "10.1373/clinchem.2008.112797",
        "url": "https://pubmed.ncbi.nlm.nih.gov/19246619/",
    },
    "bustin-2010": {
        "citation": "Bustin SA et al. MIQE précis: Practical implementation of minimum standard guidelines for fluorescence-based quantitative real-time PCR experiments. BMC Molecular Biology. 2010;11:74.",
        "doi": "10.1186/1471-2199-11-74",
        "url": "https://pubmed.ncbi.nlm.nih.gov/20858237/",
    },
    "immunoprecipitation-2020": {
        "citation": "Immunoprecipitation. Cold Spring Harbor Protocols. 2020.",
        "doi": "10.1101/pdb.top098509",
        "url": "https://doi.org/10.1101/pdb.top098509",
    },
    "coip-kinase-2020": {
        "citation": "Immunopharmacology and Quantitative Analysis of Tyrosine Kinase Signaling. Current Protocols in Immunology. 2020;130:e104.",
        "doi": "10.1002/cpim.104",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7583487/",
    },
    "donaldson-2001": {
        "citation": "Donaldson JG. UNIT 4.3 Immunofluorescence Staining. Current Protocols in Cell Biology. 2001.",
        "doi": "10.1002/0471143030.cb0403s00",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4709840/",
    },
    "yong-2019": {
        "citation": "An Introduction to Performing Immunofluorescence Staining. Methods in Molecular Biology. 2019.",
        "doi": "10.1007/978-1-4939-8935-5_26",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6918834/",
    },
    "gonzalez-2011": {
        "citation": "Gonzalez RM et al. Development of a fibrinogen-specific sandwich enzyme-linked immunosorbent assay microarray assay. Analytical Biochemistry. 2011;414:99–102.",
        "doi": "10.1016/j.ab.2011.02.039",
        "url": "https://pubmed.ncbi.nlm.nih.gov/21371419/",
    },
    "kragstrup-2013": {
        "citation": "Kragstrup TW et al. A simple set of validation steps identifies and removes false results in a sandwich ELISA caused by anti-animal IgG antibodies in plasma from arthritis patients. SpringerPlus. 2013;2:263.",
        "doi": "10.1186/2193-1801-2-263",
        "url": "https://pubmed.ncbi.nlm.nih.gov/23875127/",
    },
    "balko-2023": {
        "citation": "Balko S et al. A Robust and Standardized Approach to Quantify Wound Closure Using the Scratch Assay. Methods and Protocols. 2023;6:87.",
        "doi": "10.3390/mps6050087",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10514857/",
    },
    "jonkman-2014": {
        "citation": "Li et al. An introduction to the wound healing assay using live-cell microscopy. Cell Adhesion & Migration. 2015.",
        "doi": "10.1080/19336918.2015.1087939",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5154238/",
    },
    "pell-2021": {
        "citation": "Pell TJ et al. Epithelial Barrier Integrity Profiling: Combined Approach Using Cellular Junctional Complex Imaging and Transepithelial Electrical Resistance. SLAS Discovery. 2021;26:884–894.",
        "doi": "10.1177/24725552211013077",
        "url": "https://discovery.ucl.ac.uk/id/eprint/10132067/",
    },
    "keser-2026": {
        "citation": "Assessment of Epithelial Barrier Integrity by TEER and FITC-Dextran Permeability Assays. Bio-protocol. 2026;16:e5673.",
        "doi": "10.21769/BioProtoc.5673",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13180708/",
    },
    "sudhof-2004": {
        "citation": "Südhof TC. The synaptic vesicle cycle. Annual Review of Neuroscience. 2004;27:509–547.",
        "doi": "10.1146/annurev.neuro.26.041002.131412",
        "url": "https://doi.org/10.1146/annurev.neuro.26.041002.131412",
    },
    "schoch-2006": {
        "citation": "Schoch S, Gundelfinger ED. Molecular organization of the presynaptic active zone. Cell and Tissue Research. 2001;326:379–391.",
        "doi": "10.1007/s00441-001-0244-y",
        "url": "https://pubmed.ncbi.nlm.nih.gov/11598704/",
    },
    "gerhardt-2003": {
        "citation": "Gerhardt H et al. VEGF guides angiogenic sprouting utilizing endothelial tip cell filopodia. Journal of Cell Biology. 2003;161:1163–1177.",
        "doi": "10.1083/jcb.200302047",
        "url": "https://pubmed.ncbi.nlm.nih.gov/12810700/",
    },
    "hellstrom-2007": {
        "citation": "Hellström M et al. Dll4 signalling through Notch1 regulates formation of tip cells during angiogenesis. Nature. 2007;445:776–780.",
        "doi": "10.1038/nature05571",
        "url": "https://pubmed.ncbi.nlm.nih.gov/17259973/",
    },
    "suchting-2007": {
        "citation": "Suchting S et al. The Notch ligand Delta-like 4 negatively regulates endothelial tip cell formation and vessel branching. PNAS. 2007;104:3225–3230.",
        "doi": "10.1073/pnas.0611177104",
        "url": "https://pubmed.ncbi.nlm.nih.gov/17296941/",
    },
}


# Independently verified article metadata and specific supporting locations.
_reference_review=json.loads((Path(__file__).with_name('template_reference_corrections.json')).read_text(encoding='utf-8'))
for finding in _reference_review['findings']:
    corrected_key={'li-2015':'jonkman-2014','schoch-2001':'schoch-2006','stanifer-2026':'keser-2026'}.get(finding['id'],finding['id'])
    if finding.get('verified_source') and corrected_key in REFERENCES:
        REFERENCES[corrected_key].update(finding['verified_source'])
    for verified in finding.get('verified_sources',[]):
        for ref in REFERENCES.values():
            if ref['doi']==verified['doi']:ref.update(verified)
for key,verified in zip(['dodge-1967','geppert-1994'],_reference_review['primary_release_evidence']['sources']):
    REFERENCES[key]=verified
REFERENCES['bustin-2009']['support_location']='MIQE checklist and article text on RNA quality, reverse transcription, assay performance, controls and normalization.'
REFERENCES['bustin-2010']['support_location']='MIQE précis checklist and practical assay-validation guidance.'
REFERENCES['balko-2023']['support_location']='Methods describing scratch creation, matched image acquisition and wound-closure quantification.'


ENTRIES = [
    {
        "id": "rt-qpcr-expression-workflow", "name": "RT-qPCR expression workflow",
        "summary": "RNA quality, reverse transcription, amplification, and control-aware expression analysis.",
        "category": "Gene expression", "synonyms": ["RT-qPCR", "qPCR", "quantitative PCR", "real-time PCR"],
        "tags": ["RNA", "cDNA", "amplification", "Cq", "no-template control", "reference gene"],
        "biology_note": "RT-qPCR measures target amplification after RNA is converted to cDNA; interpretation depends on assay performance and validated normalization.",
        "limitations": "Schematic only. No amplification curves, expression values, fold changes, or significance are shown. Validate RNA, primer specificity, efficiency, controls, and reference genes for the experiment.",
        "asset_ids": ["core.sample.cell_pellet_tube", "core.lab.microcentrifuge_tube", "exp.lab_equipment.qpcr_instrument"],
        "stages": [("RNA sample", "Cells or tissue"), ("RNA QC", "Integrity + amount"), ("Reverse transcription", "RNA → cDNA"), ("Set reactions", "Target, reference + controls"), ("qPCR", "Record amplification"), ("Compare expression", "Validated normalization")],
        "relations": ["sampling", "measurement", "conversion", "measurement", "measurement"],
        "edge_labels": ["collect", "assess", "transcribe", "amplify", "check"],
        "source_ids": ["bustin-2009", "bustin-2010"],
        "decisions": ["Show RNA-to-cDNA conversion, the target/reference assay, and negative controls as distinct steps; leave all amplification traces and relative-expression results blank because they depend on the user's assay and data."],
    },
    {
        "id": "immunoprecipitation-workflow", "name": "Immunoprecipitation workflow",
        "summary": "Antibody capture of a target from lysate, bead recovery, washing, and downstream analysis.",
        "category": "Protein methods", "synonyms": ["IP", "co-IP", "immunoprecipitation", "protein complex capture"],
        "tags": ["protein", "antibody", "beads", "lysate", "wash", "immunoblot"],
        "biology_note": "An antibody enriches its target from a prepared sample; co-immunoprecipitation can recover associated proteins when the complex survives extraction and washing.",
        "limitations": "Schematic only. Recovery is not proof of direct binding. Antibody specificity, lysis conditions, bead background, interaction stability, input, and immunoglobulin-chain interference require experiment-specific controls.",
        "asset_ids": ["core.sample.cell_pellet_tube", "core.lab.microcentrifuge_tube", "core.antibody.igg", "core.lab.plate_96_well"],
        "stages": [("Cell lysate", "Preserve target context"), ("Antibody capture", "Target-specific antibody"), ("Bead binding", "Immobilize complex"), ("Wash", "Remove unbound material"), ("Elute", "Recover enriched proteins"), ("Readout", "Immunoblot or MS")],
        "relations": ["sampling", "binding", "binding", "transport", "measurement"],
        "edge_labels": ["lyse", "capture", "recover", "wash", "analyze"],
        "source_ids": ["immunoprecipitation-2020", "coip-kinase-2020"],
        "decisions": ["Separate target recognition, solid-phase recovery, washing, and downstream detection. Leave the recovered protein composition unassigned; enrichment alone does not establish direct molecular contact."],
    },
    {
        "id": "indirect-immunofluorescence-workflow", "name": "Indirect immunofluorescence workflow",
        "summary": "Fixed-cell labeling with a target-specific primary antibody and fluorophore-linked secondary antibody.",
        "category": "Imaging methods", "synonyms": ["indirect IF", "immunofluorescence staining", "fluorescent antibody staining", "IF microscopy"],
        "tags": ["cells", "fixation", "permeabilization", "primary antibody", "secondary antibody", "fluorescence"],
        "biology_note": "The primary antibody recognizes the selected target; a fluorophore-conjugated secondary antibody binds the primary antibody for imaging.",
        "limitations": "Schematic only. Localization and signal are not data. Fixation, permeabilization, antibody specificity, fluorophore cross-reactivity, spectral bleed-through, and imaging settings require validation; include appropriate negative controls.",
        "asset_ids": ["core.cell.generic", "core.antibody.igg", "exp.lab_equipment.confocal_microscope"],
        "stages": [("Cell model", "Culture or tissue"), ("Prepare specimen", "Fix, permeabilize + block"), ("Primary antibody", "Recognize target"), ("Fluorescent secondary", "Label primary antibody"), ("Wash + mount", "Reduce unbound signal"), ("Image", "Acquire channels")],
        "relations": ["sampling", "conversion", "binding", "binding", "measurement"],
        "edge_labels": ["prepare", "fix", "recognize", "label", "image"],
        "source_ids": ["donaldson-2001", "yong-2019"],
        "decisions": ["Use the indirect-labeling sequence and separate staining from image acquisition; depict controls as a visible check rather than implying that a fluorescent signal is target-specific by itself."],
    },
    {
        "id": "sandwich-elisa-workflow", "name": "Sandwich ELISA workflow",
        "summary": "Capture antibody, sample antigen, detection antibody, enzyme signal, and calibrated readout.",
        "category": "Protein assays", "synonyms": ["sandwich ELISA", "capture ELISA", "enzyme immunoassay", "two-site immunoassay"],
        "tags": ["antigen", "capture antibody", "detection antibody", "microplate", "standard curve", "absorbance"],
        "biology_note": "Two antibodies recognize distinct epitopes of an analyte; an enzyme-linked detection system produces a measurable signal for comparison with standards.",
        "limitations": "Schematic only. No standard curve or concentrations are supplied. Antibody pairing, matrix effects, cross-reactivity, sample dilution, calibration range, and signal saturation must be assessed for the analyte and sample type.",
        "asset_ids": ["core.lab.plate_96_well", "core.antibody.igg", "core.lab.plate_reader"],
        "stages": [("Coat", "Immobilize capture antibody"), ("Block", "Limit nonspecific binding"), ("Add sample", "Analyte binds capture"), ("Detect", "Enzyme-linked antibody"), ("Develop", "Enzyme + substrate"), ("Read", "Compare with standards")],
        "relations": ["binding", "conversion", "binding", "binding", "measurement"],
        "edge_labels": ["coat", "block", "capture analyte", "detect", "read signal"],
        "source_ids": ["gonzalez-2011", "kragstrup-2013"],
        "decisions": ["Show capture and detection as separate antibody-binding events, with standards carried into the readout. Do not invent a calibration curve or imply that antibody pairing is validated."],
    },
    {
        "id": "wound-closure-assay-workflow", "name": "Wound-closure assay workflow",
        "summary": "Create a cell-free gap, image matched fields over time, and quantify gap closure.",
        "category": "Cell migration", "synonyms": ["scratch assay", "wound healing assay", "gap closure", "collective migration"],
        "tags": ["cell monolayer", "scratch", "gap", "time course", "image analysis", "migration"],
        "biology_note": "A gap in a confluent cell layer can be followed by microscopy to assess collective movement into the cleared area.",
        "limitations": "In vitro gap closure does not by itself isolate migration from proliferation, survival, or changes in cell spreading. Standardize gap geometry, image positions, and timing; interpret in the context of model and controls.",
        "asset_ids": ["culture.assay_workflow.epithelial_scratch_wound", "exp.lab_equipment.confocal_microscope"],
        "stages": [("Cell monolayer", "Matched cell model"), ("Create gap", "Record starting geometry"), ("Apply condition", "Include vehicle control"), ("Image same field", "Start + later times"), ("Measure gap", "Area or width"), ("Compare", "Replicates + controls")],
        "relations": ["sampling", "conversion", "treatment", "measurement", "measurement"],
        "edge_labels": ["seed", "clear gap", "treat", "image", "measure"],
        "source_ids": ["balko-2023", "jonkman-2014"],
        "decisions": ["Keep the initial gap, repeated imaging of the same field, and gap measurement explicit. The schematic does not show closure trajectories or attribute closure exclusively to migration."],
    },
    {
        "id": "epithelial-barrier-transwell-workflow", "name": "Epithelial barrier Transwell assay",
        "summary": "Grow a polarized epithelial layer on a porous insert and pair electrical and tracer-flux readouts.",
        "category": "Barrier assays", "synonyms": ["Transwell barrier", "TEER assay", "FITC-dextran permeability", "epithelial permeability"],
        "tags": ["epithelial monolayer", "porous insert", "apical", "basolateral", "TEER", "paracellular flux"],
        "biology_note": "An epithelial monolayer separates apical and basolateral compartments; TEER reports ionic conductance while tracer passage measures permeability to the chosen tracer.",
        "limitations": "The two readouts are complementary and not interchangeable. TEER does not measure macromolecule flux; tracer results depend on tracer size, sampling, membrane, model, and assay conditions. A Transwell is an in-vitro model, not an intact organ barrier.",
        "asset_ids": ["exp.model_system.transwell_culture.monoculture", "core.lab.plate_reader"],
        "stages": [("Seed insert", "Apical cell suspension"), ("Establish layer", "Monitor coverage"), ("Measure TEER", "Ionic conductance"), ("Add tracer", "Apical donor side"), ("Collect receiver", "Basolateral compartment"), ("Quantify flux", "Tracer-specific readout")],
        "relations": ["sampling", "conversion", "measurement", "transport", "measurement"],
        "edge_labels": ["seed", "mature", "add tracer", "tracer flux", "quantify"],
        "source_ids": ["pell-2021", "keser-2026"],
        "decisions": ["Pair the nondestructive electrical readout with a separate directional tracer-flux step, showing apical and basolateral compartments without equating resistance with macromolecule permeability."],
    },
    {
        "id": "chemical-synaptic-transmission", "name": "Chemical synaptic transmission",
        "summary": "Calcium-dependent vesicle release across a chemical synapse, with generic postsynaptic receptors.",
        "category": "Neuroscience", "synonyms": ["chemical synapse", "synaptic transmission", "neurotransmitter release", "synaptic vesicle cycle"],
        "tags": ["presynaptic bouton", "calcium", "synaptic vesicle", "exocytosis", "synaptic cleft", "postsynaptic receptor"],
        "biology_note": "At a canonical chemical synapse, presynaptic depolarization promotes calcium-dependent vesicle fusion; released transmitter crosses the cleft and activates postsynaptic receptors.",
        "limitations": "A generalized schematic, not a specific neuron, transmitter, receptor subtype, or measured synaptic response. Release probability, receptor kinetics, short-term plasticity, cotransmission, and clearance mechanisms vary by synapse.",
        "asset_ids": ["neuro.chemical_synapse.bouton_spine"],
        "stages": [("Spike arrives", "Presynaptic depolarization"), ("Ca²⁺ entry", "Voltage-gated channels"), ("Vesicle fusion", "Active-zone release"), ("Cleft crossing", "Transmitter diffusion"), ("Receptor binding", "Postsynaptic membrane"), ("Signal ends", "Uptake or degradation")],
        "relations": ["transport", "transport", "secretion", "transport", "binding"],
        "edge_labels": ["depolarize", "Ca²⁺ influx", "exocytosis", "diffuse", "activate receptor"],
        "source_ids": ["dodge-1967", "geppert-1994", "sudhof-2004", "schoch-2006"],
        "decisions": ["Use the bouton–spine asset as the spatial anchor and label the ordered release steps from vesicle pool to postsynaptic response. Keep transmitter and receptor identity generic; show clearance without selecting a synapse-specific route."],
    },
    {
        "id": "angiogenic-sprouting", "name": "Angiogenic sprouting",
        "summary": "An endothelial sprout near local VEGF cues, with leading tips and neighboring cells.",
        "category": "Vascular biology", "synonyms": ["sprouting angiogenesis", "endothelial sprout", "tip cell", "vessel branching"],
        "tags": ["endothelial cell", "VEGF", "tip cell", "stalk cell", "DLL4", "Notch", "lumen"],
        "biology_note": "Endothelial tip cells extend toward proangiogenic cues while neighboring stalk cells support sprout extension; VEGF and DLL4–Notch signaling contribute to tip–stalk patterning.",
        "limitations": "A qualitative spatial schematic, not a universal sequence or measured outcome. Lumen formation and blood flow are not shown. Tip–stalk states are dynamic; matrix, flow, tissue context, VEGF presentation, and signaling can alter sprout behavior and branching.",
        "asset_ids": ["tissue.angiogenic_sprout.single_tip"],
        "stages": [("Parent vessel", "Endothelial source"), ("VEGF cue", "Local guidance"), ("Tip extension", "Migration + filopodia"), ("Stalk support", "Neighboring cells"), ("Lumen extends", "Sprout organization"), ("Branch pattern", "Context-dependent")],
        "relations": ["secretion", "transport", "transport", "expression", "conversion"],
        "edge_labels": ["VEGF cue", "guide", "extend", "DLL4–Notch", "remodel"],
        "source_ids": ["gerhardt-2003", "hellstrom-2007", "suchting-2007"],
        "decisions": ["Use the single-tip sprout asset as the spatial anchor; depict VEGF guidance and DLL4–Notch-mediated lateral regulation as contextual relationships, with tip/stalk states and branch pattern kept qualitative and dynamic."],
    },
]


PALETTE = {
    "background": "#F7F9FC", "surface": "#FFFFFF", "ink": "#24313B",
    "muted": "#637381", "border": "#C9D5DE", "sample": "#2A8C82",
    "process": "#527DA8", "signal": "#D79A31", "caution": "#9A5F33",
    "accent": "#7667A8", "soft": "#E7EEF4",
}


def _text(node_id: str, text: str, x: float, y: float, width: float,
          *, size: int = 16, role: str = "ink", align: str = "center",
          include_scientific_record: bool = False) -> dict:
    return {
        "id": node_id, "type": "text", "layer_id": "editable_labels",
        "x": x, "y": y, "width": width, "height": max(22, size + 5),
        "text": text, "placeholder": True, "editable": True,
        "font_size": size, "fill_role": role, "align": align,
        **({"include_scientific_record": True} if include_scientific_record else {}),
    }


def _shape(node_id: str, x: float, y: float, width: float, height: float,
           *, fill: str = "surface", stroke: str = "border", radius: int = 12) -> dict:
    return {
        "id": node_id, "type": "shape", "shape": "rounded_rect",
        "layer_id": "workflow_stages", "x": x, "y": y,
        "width": width, "height": height, "radius": radius,
        "fill_role": fill, "stroke_role": stroke, "stroke_width": 1.8,
    }


def _asset(node_id: str, asset_id: str, x: float, y: float,
           width: float = 74, height: float = 74) -> dict:
    return {
        "id": node_id, "name": node_id.replace("_", " ").title(),
        "type": "asset", "layer_id": "biological_objects",
        "asset_id": asset_id, "top_level": True,
        "x": x, "y": y, "width": width, "height": height,
        "palette_overrides": {"outline": "ink"},
    }


def _anchor(node_id: str, side: str) -> dict:
    return {"node_id": node_id, "anchor": side}


def _record(entry: dict) -> dict:
    refs = []
    for source_id in entry["source_ids"]:
        ref = REFERENCES[source_id]
        refs.append({"id": source_id, **ref,
                     "support_location": ref.get("support_location", "Article text supporting the stated biological context; overview reference only."),
                     "decision": entry["decisions"][0]})
    return {
        "id": f"science.figure-studio.{entry['id']}.2026-11-03",
        "verified_on": "2026-11-03",
        "scope": entry["summary"],
        "relationships": [{"claim": entry["biology_note"], "source_ids": entry["source_ids"]}],
        "sources": refs,
        "limitations": [entry["limitations"]],
        "authorship": "Original editable scene composed from released Figure Studio assets and original vector/text objects; published figures informed scientific relationships only. No publication artwork was copied, traced, or embedded.",
    }


# Stage-specific drawings keep each experimental step recognizable without a
# row of generic process boxes. Limits and methods stay in scientific_record.
STAGE_ASSETS = {
    "rt-qpcr-expression-workflow": ["core.sample.cell_pellet_tube", "core.rna.strand_linear", "exp.nucleic_acid.cdna_library", "core.lab.microcentrifuge_tube", "exp.lab_equipment.qpcr_instrument", "exp.nucleic_acid.pcr_amplicon"],
    "immunoprecipitation-workflow": ["core.lab.microcentrifuge_tube", "core.antibody.igg", "core.protein.enzyme", "core.lab.microcentrifuge_tube", "core.lab.microcentrifuge_tube", "exp.lab_equipment.blot_imager"],
    "indirect-immunofluorescence-workflow": ["core.cell.generic", "core.lab.well_plate", "core.antibody.igg", "core.antibody.igg", "core.sample.tissue_section_slide", "exp.lab_equipment.confocal_microscope"],
    "sandwich-elisa-workflow": ["core.antibody.igg", "core.lab.plate_96_well", "core.protein.enzyme", "core.antibody.igg", "core.lab.plate_96_well", "core.lab.plate_reader"],
    "wound-closure-assay-workflow": ["core.cell.epithelial_apical", "culture.assay_workflow.epithelial_scratch_wound", "core.lab.pipette", "core.lab.microscope", "culture.assay_workflow.epithelial_scratch_wound", "culture.assay_workflow.epithelial_scratch_wound"],
    "epithelial-barrier-transwell-workflow": ["core.cell.epithelial", "exp.model_system.transwell_culture.monoculture", "exp.model_system.transwell_culture.monoculture", "core.lab.microcentrifuge_tube", "exp.model_system.transwell_culture.monoculture", "core.lab.plate_reader"],
    "chemical-synaptic-transmission": ["neuro.axon_myelin.longitudinal", "core.channel.ion", "core.vesicle", "core.ligand.small_molecule", "core.channel.ion", "core.protein.enzyme"],
    "angiogenic-sprouting": ["tissue.capillary.longitudinal", "core.ligand.peptide", "tissue.angiogenic_sprout.single_tip", "tissue.angiogenic_sprout.branching", "tissue.capillary.longitudinal", "tissue.angiogenic_sprout.branching"],
}


def _make(entry: dict) -> dict:
    width, height = 1120, 430
    nodes = [_text("title", entry["name"], 36, 24, 1048, size=27, align="left", include_scientific_record=True)]
    groups = []
    icons = STAGE_ASSETS[entry['id']]
    for i, ((label, caption), aid) in enumerate(zip(entry["stages"], icons)):
        x = 26 + i * 182
        object_id = f"stage_{i + 1}_object"
        nodes.extend([
            _asset(object_id, aid, x + 22, 127),
            _text(f"stage_{i + 1}_number", str(i+1), x + 60, 85, 40, size=16, role="muted"),
            _text(f"stage_{i + 1}_label", label, x - 2, 238, 174, size=17, role="process"),
            _text(f"stage_{i + 1}_caption", caption, x - 2, 281, 174, size=16, role="muted"),
        ])
        # Draw assay-specific marks as separate editable vector parts.
        extras=[]
        if entry['id']=='immunoprecipitation-workflow' and i==2:
            nodes[-4]=_shape(object_id,x+25,139,76,76,fill='soft',stroke='process',radius=38)
            for j,(dx,dy) in enumerate([(40,145),(70,160),(45,184)]):
                extras.append(_text(f'bead_antibody_{j}','Y',x+dx,dy,20,size=25,role='process'))
        if entry['id']=='immunoprecipitation-workflow' and i==3:
            extras.append(_asset('wash_pipette','core.lab.pipette',x+75,112,50,50))
        if entry['id']=='indirect-immunofluorescence-workflow' and i==3:
            marker=_shape('secondary_fluorophore',x+62,177,15,15,fill='signal',stroke='signal',radius=8)
            extras.append(marker)
        if entry['id']=='sandwich-elisa-workflow' and i==2:
            nodes[-4]=_shape(object_id,x+43,151,45,45,fill='sample',stroke='ink',radius=22)
            extras.append(_asset('captured_antibody','core.antibody.igg',x+34,178,60,60))
            extras.append(_text('analyte_label','Antigen',x+86,151,75,size=14,role='sample'))
        if entry['id']=='sandwich-elisa-workflow' and i==3:
            extras.append(_shape('detection_enzyme',x+61,177,18,18,fill='signal',stroke='ink',radius=9))
            extras.append(_text('enzyme_label','Enzyme',x+81,174,80,size=14,role='signal'))
        if entry['id']=='wound-closure-assay-workflow' and i==4:
            extras.append(_text('gap_measure','↔',x+42,151,50,size=30,role='signal'))
        nodes.extend(extras)
        # Captions may wrap at manuscript size; preserve explicit readable space.
        next(n for n in nodes if n['id']==f'stage_{i+1}_caption')['height']=54
        next(n for n in nodes if n['id']==f'stage_{i+1}_label')['height']=43
        groups.append({"id": f"stage_{i+1}", "name": label, "layer_id": "workflow_stages",
                       "members": [object_id, f"stage_{i+1}_number", f"stage_{i+1}_label", f"stage_{i+1}_caption", *[n["id"] for n in extras]]})
    nodes.append(_text("illustrative_note", "Schematic · adapt labels and controls to your experiment", 36, 378, 1048, size=16, role="muted", align="left"))
    connectors = [{"id": f"stage_{i+1}_to_{i+2}", "layer_id": "workflow_relationships",
        "from": _anchor(f"stage_{i+1}_object", "right"), "to": _anchor(f"stage_{i+2}_object", "left"),
        "relation": entry["relations"][i], "label": "",
        "style": {"stroke_role": "process", "stroke_width": 2.2, "line": "solid", "terminator": "arrow"}}
        for i in range(5)]
    return {
        "schema": SCHEMA, "id": entry["id"], "name": entry["name"], "summary": entry["summary"],
        "source_record_id": SOURCE_RECORD, "rights_record_id": RIGHTS_RECORD,
        "scientific_record": _record(entry), "insertion_art_style": "soft-color",
        "canvas": {"width": width, "height": height, "width_in": width/96, "height_in": height/96, "background_role": "background"},
        "palette": deepcopy(PALETTE),
        "layers": [{"id": "workflow_stages", "name": "Experimental stages"},
                   {"id": "biological_objects", "name": "Biological objects and assay equipment"},
                   {"id": "workflow_relationships", "name": "Experimental sequence"},
                   {"id": "editable_labels", "name": "Editable labels"}],
        "nodes": nodes, "groups": groups, "connectors": connectors,
    }


def _ellipse(identifier,x,y,w,h,role='signal'):
    n=_shape(identifier,x,y,w,h,fill=role,stroke='ink')
    n['shape']='ellipse'
    return n


def _path(identifier,x,y,w,h,path,role='soft',stroke='ink'):
    n=_shape(identifier,x,y,w,h,fill=role,stroke=stroke)
    n.update(shape='path',path=path)
    return n


def _mechanism_base(entry,width=1000,height=600):
    return {'schema':SCHEMA,'id':entry['id'],'name':entry['name'],'summary':entry['summary'],
        'source_record_id':SOURCE_RECORD,'rights_record_id':RIGHTS_RECORD,
        'scientific_record':_record(entry),'insertion_art_style':'soft-color','layout_kind':'mechanism',
        'canvas':{'width':width,'height':height,'width_in':width/96,'height_in':height/96,'background_role':'background'},
        'palette':deepcopy(PALETTE),'layers':[
            {'id':'workflow_stages','name':'Biological compartments'},
            {'id':'biological_objects','name':'Biological structures'},
            {'id':'workflow_relationships','name':'Biological relationships'},
            {'id':'editable_labels','name':'Editable labels'}],
        'nodes':[],'groups':[],'connectors':[]}


def _chemical_synapse(entry):
    scene=_mechanism_base(entry)
    scene['summary']='Calcium-dependent vesicle release across a chemical synapse, with generic postsynaptic receptors.'
    # The membrane boundaries are deliberately separate; the gap is the cleft.
    pre=_path('presynaptic_terminal',190,105,620,195,
        'M 0 35 Q 0 0 35 0 L 270 0 L 270 -45 L 330 -45 L 330 0 L 585 0 Q 620 0 620 35 L 620 160 Q 620 195 585 195 L 35 195 Q 0 195 0 160 Z',role='soft',stroke='process')
    pre['height']=240
    # Keep all path-local coordinates nonnegative for predictable native placement.
    pre['path']='M 0 80 Q 0 45 35 45 L 270 45 L 270 0 L 330 0 L 330 45 L 585 45 Q 620 45 620 80 L 620 205 Q 620 240 585 240 L 35 240 Q 0 240 0 205 Z'
    pre.update(y=60,width=620,height=240)
    post=_path('postsynaptic_membrane',190,390,620,115,
        'M 0 0 L 620 0 L 620 90 Q 310 120 0 90 Z',role='sample',stroke='process')
    nodes=[_text('title',entry['name'],34,20,932,size=27,align='left',include_scientific_record=True),pre,post,
        _text('presynaptic_label','Presynaptic terminal',225,130,240,size=20,align='left'),
        _text('postsynaptic_label','Postsynaptic membrane',225,450,300,size=20,role='surface',align='left'),
        _text('cleft_label','Synaptic cleft',820,329,160,size=17,role='muted'),
        _text('calcium_label','Ca²⁺ entry',25,320,145,size=18,role='process'),
        _text('fusion_label','Vesicle fusion',565,181,190,size=18,role='process'),
        _text('transmitter_label','Transmitter',405,337,140,size=17,role='signal'),
        _text('receptor_label','Receptor binding',535,430,210,size=18,role='surface'),
        _text('boundary_note','Generic synapse · transmitter and receptor identities are unspecified',35,550,930,size=16,role='muted',align='left')]
    for i,(x,y) in enumerate([(325,215),(395,220),(460,210)]):
        nodes.append(_ellipse(f'vesicle_{i}',x,y,34,34,role='surface'))
    nodes.extend([_path('releasing_vesicle',608,256,42,45,'M 0 45 L 12 45 L 12 32 C 0 25 1 6 17 3 C 34 0 43 23 29 32 L 29 45 L 42 45',role='surface'),
        _shape('calcium_channel',280,281,24,38,fill='process',stroke='ink',radius=5),
        _text('calcium_ion','Ca²⁺',236,338,70,size=16,role='process'),
        _shape('receptor_one',495,372,18,46,fill='accent',stroke='ink',radius=5),
        _shape('receptor_two',558,372,18,46,fill='accent',stroke='ink',radius=5)])
    for i,(x,y) in enumerate([(624,315),(615,341),(590,355)]):
        nodes.append(_ellipse(f'transmitter_{i}',x,y,10,10,role='signal'))
    scene['nodes']=nodes
    scene['groups']=[
        {'id':'presynaptic_group','name':'Presynaptic membrane and vesicles','layer_id':'biological_objects','members':['presynaptic_terminal','vesicle_0','vesicle_1','vesicle_2','releasing_vesicle','presynaptic_label']},
        {'id':'release_group','name':'Calcium entry and transmitter release','layer_id':'workflow_stages','members':['calcium_channel','calcium_ion','transmitter_0','transmitter_1','transmitter_2','fusion_label','transmitter_label']},
        {'id':'postsynaptic_group','name':'Postsynaptic receptors','layer_id':'biological_objects','members':['postsynaptic_membrane','receptor_one','receptor_two','postsynaptic_label','receptor_label']}]
    def edge(identifier,start,end,relation,source='bottom',target='top'):
        return {'id':identifier,'layer_id':'workflow_relationships','from':_anchor(start,source),'to':_anchor(end,target),
                'relation':relation,'label':'','style':{'stroke_role':'process','stroke_width':2.2,'line':'solid','terminator':'arrow'}}
    scene['connectors']=[edge('calcium_influx','calcium_ion','calcium_channel','transport','top','bottom'),
                         edge('transmitter_release','releasing_vesicle','transmitter_0','secretion'),
                         edge('transmitter_binding','transmitter_2','receptor_two','binding')]
    return scene


def _angiogenesis(entry):
    scene=_mechanism_base(entry,1000,600)
    scene['summary']='An endothelial sprout near local VEGF cues, with parent vessel, leading tips and neighboring cells.'
    scene['nodes']=[_text('title',entry['name'],34,20,932,size=27,align='left',include_scientific_record=True),
        _asset('endothelial_sprout','tissue.angiogenic_sprout.branching',200,70,480,480),
        _text('parent_label','Parent vessel',36,401,210,size=20,role='process'),
        _text('tip_label','Leading tips',690,170,220,size=20,role='process'),
        _text('stalk_label','Neighboring stalk cells',550,410,365,size=20,role='process'),
        _text('vegf_label','Local VEGF cues',710,86,230,size=20,role='signal'),
        _text('matrix_label','Surrounding matrix',35,505,270,size=18,role='muted'),
        _text('dynamic_note','Tip–stalk states change with local signaling and tissue context',35,556,930,size=16,role='muted',align='left'),
        _text('guidance_label','Guidance',716,320,180,size=17,role='process'),
        _ellipse('vegf_one',815,135,17,17),_ellipse('vegf_two',865,200,17,17),
        _ellipse('vegf_three',805,264,17,17),_ellipse('vegf_four',910,285,17,17),
        _shape('matrix_segment_one',82,474,160,5,fill='border',stroke='border',radius=2),
        _shape('matrix_segment_two',300,500,170,5,fill='border',stroke='border',radius=2),
        _shape('matrix_segment_three',510,508,150,5,fill='border',stroke='border',radius=2)]
    # Solid endothelial cord: this template makes no lumen-formation claim.
    sprout=next(n for n in scene['nodes'] if n['id']=='endothelial_sprout')
    sprout['palette_overrides'].update(vessel_wall='sample',lumen='sample',matrix='border')
    target=_ellipse('guidance_tip',552,171,4,4,role='sample');target['opacity']=0
    scene['nodes'].extend([target,
        _path('parent_leader',220,312,62,84,'M 0 84 L 62 0',role='background',stroke='muted'),
        _path('tip_leader',555,175,150,30,'M 150 30 L 0 0',role='background',stroke='muted'),
        _path('stalk_leader',480,385,130,25,'M 130 25 L 0 0',role='background',stroke='muted')])
    scene['groups']=[
        {'id':'vessel_group' ,'name':'Endothelial sprout and parent vessel','layer_id':'biological_objects','members':['endothelial_sprout','parent_label','tip_label','stalk_label','parent_leader','tip_leader','stalk_leader','guidance_tip']},
        {'id':'guidance_group','name':'Local VEGF cues','layer_id':'workflow_stages','members':['vegf_label','vegf_one','vegf_two','vegf_three','vegf_four','guidance_label']},
        {'id':'matrix_group','name':'Surrounding matrix context','layer_id':'workflow_stages','members':['matrix_label','matrix_segment_one','matrix_segment_two','matrix_segment_three']}]
    scene['connectors']=[{'id':'vegf_guidance','layer_id':'workflow_relationships','from':_anchor('vegf_three','left'),'to':_anchor('guidance_tip','center'),
        'relation':'activation','label':'','style':{'stroke_role':'signal','stroke_width':2.2,'line':'dashed','terminator':'arrow'}}]
    return scene


def make_scenes() -> list[dict]:
    """Return deep, independently editable recipes in stable catalog order."""
    return [_chemical_synapse(e) if e['id']=='chemical-synaptic-transmission' else _angiogenesis(e) if e['id']=='angiogenic-sprouting' else _make(e) for e in ENTRIES]


if __name__ == "__main__":
    import json
    print(json.dumps(make_scenes(), indent=2, ensure_ascii=False))
