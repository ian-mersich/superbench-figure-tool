"""Original, editable schematic SVGs for a neurobiology asset expansion.

These drawings are generic topology sketches, not reconstructions of published
art. Literature entries record biological facts and broad structural decisions
that informed the art. New work remains draft pending the repository's normal
scientific, visual, licensing, and product review.
"""

from __future__ import annotations

from html import escape


REFERENCES = [
    {
        "id": "synapse_ultrastructure",
        "citation": "Harris KM, Jensen FE, Tsao B. Three-dimensional structure of dendritic spines and synapses in rat hippocampus (CA1) at postnatal day 15 and adult ages. J Neurosci. 1992;12:2685–2705.",
        "doi": "10.1523/JNEUROSCI.12-07-02685.1992",
        "url": "https://doi.org/10.1523/JNEUROSCI.12-07-02685.1992",
        "figure": "Figures 3–4 (spine classes; thin, mushroom, and shaft synapses)",
        "design_decision": "Supports the distinction between presynaptic terminal, synaptic cleft, dendritic spine, and dendritic shaft; used only to set the biological topology, not to copy the illustrated geometry.",
    },
    {
        "id": "astrocyte_meshwork",
        "citation": "Arizono M, et al. Structural basis of astrocytic Ca2+ signals at tripartite synapses. Nat Commun. 2020;11:1906.",
        "doi": "10.1038/s41467-020-15648-4",
        "url": "https://doi.org/10.1038/s41467-020-15648-4",
        "figure": "Figures 1, 3, and 8i (reticular meshwork; direct synapse contacts; tripartite-synapse schematic)",
        "design_decision": "Informed the distinction between a process contacting a bouton–spine synapse and a broader astrocytic process network; no activity or signaling effect is encoded.",
    },
    {
        "id": "oligo_multiaxon",
        "citation": "Almeida RG, Czopka T, Ffrench-Constant C, Lyons DA. Individual axons regulate the myelinating potential of single oligodendrocytes in vivo. Development. 2011;138:4443–4450.",
        "doi": "10.1242/dev.071001",
        "url": "https://doi.org/10.1242/dev.071001",
        "figure": "Figure 2 (single oligodendrocytes and multiple sheaths)",
        "design_decision": "Supports one oligodendrocyte soma extending several separate myelinating processes to axons; the drawn branches and axon positions are newly composed.",
    },
    {
        "id": "schwann_remak",
        "citation": "Orita S, et al. Schwann cell LRP1 regulates Remak bundle ultrastructure and axonal interactions to prevent neuropathic pain. J Neurosci. 2013;33:5590–5602.",
        "doi": "10.1523/JNEUROSCI.3342-12.2013",
        "url": "https://doi.org/10.1523/JNEUROSCI.3342-12.2013",
        "figure": "Figures 2B and 3A (myelinated fiber; Remak bundle ultrastructure)",
        "design_decision": "Informed the separate one-axon myelinating internode and multiple small-axon nonmyelinating Remak bundle topologies; no pathology is depicted.",
    },
    {
        "id": "microglia_synapse_contact",
        "citation": "Wake H, et al. Resting microglia directly monitor the functional state of synapses in vivo and determine the fate of ischemic terminals. J Neurosci. 2009;29:3974–3980.",
        "doi": "10.1523/JNEUROSCI.4363-08.2009",
        "url": "https://doi.org/10.1523/JNEUROSCI.4363-08.2009",
        "figure": "Figure 1",
        "design_decision": "Supports ramified surveying processes and direct, transient synaptic contacts. The asset uses a neutral contact mark and deliberately does not depict engulfment, elimination, or pruning.",
    },
    {
        "id": "feedforward_convergence",
        "citation": "Sailamul P, Jang J, Paik SB. Synaptic convergence regulates synchronization-dependent spike transfer in feedforward neural networks. J Comput Neurosci. 2017;43:189–202.",
        "doi": "10.1007/s10827-017-0657-5",
        "url": "https://doi.org/10.1007/s10827-017-0657-5",
        "figure": "Figures 1 and 5 (feedforward network and convergence topology)",
        "design_decision": "Supports the topology of feedforward chains and convergent projections; arrows in this generic drawing show only direction and do not imply excitation or inhibition.",
    },
]


CONCEPTS = {
    "chemical_synapse": {
        "key": "chemical_synapse", "name": "Chemical synapse", "category": "neurobiology", "subcategory": "synapse",
        "synonyms": ["neuronal synapse", "synaptic contact", "axon-dendrite synapse"],
        "forms": [
            {"id": "bouton_spine", "label": "Bouton to spine", "description": "A presynaptic bouton apposed to a dendritic spine across a narrow cleft."},
            {"id": "shaft_contact", "label": "Bouton to shaft", "description": "A presynaptic bouton apposed directly to a dendritic shaft."},
        ],
        "limits": "Generic chemical-synapse topology; does not specify transmitter, synapse class, direction of net circuit effect, or molecular composition.",
        "refs": ["synapse_ultrastructure"],
    },
    "axon_myelin": {
        "key": "axon_myelin", "name": "Myelinated axon", "category": "neurobiology", "subcategory": "axon and myelin",
        "synonyms": ["myelin sheath", "internode", "myelinated nerve fiber"],
        "forms": [
            {"id": "longitudinal", "label": "Longitudinal internodes", "description": "An axon with two myelin internodes separated by a node."},
            {"id": "transverse", "label": "Transverse myelin ring", "description": "A cross-section through an axon surrounded by concentric myelin lamellae."},
        ],
        "limits": "Schematic topology only; sheath thickness and spacing are not to scale and do not identify CNS or PNS origin.",
        "refs": ["oligo_multiaxon", "schwann_remak"],
    },
    "oligodendrocyte": {
        "key": "oligodendrocyte", "name": "Oligodendrocyte", "category": "neurobiology", "subcategory": "glia",
        "synonyms": ["oligodendroglia", "CNS myelinating glia"],
        "forms": [
            {"id": "multiple_sheaths", "label": "Multiple sheaths", "description": "One oligodendrocyte soma connects through distinct processes to sheaths on several axons."},
            {"id": "branching", "label": "Compact branching view", "description": "A compact radial composition showing a single soma and branched processes ending in separate sheaths."},
        ],
        "limits": "Generic CNS oligodendrocyte topology; sheath count and process lengths are illustrative, not quantitative.",
        "refs": ["oligo_multiaxon"],
    },
    "schwann_cell": {
        "key": "schwann_cell", "name": "Schwann cell", "category": "neurobiology", "subcategory": "glia",
        "synonyms": ["peripheral glia", "myelinating Schwann cell", "Remak Schwann cell"],
        "forms": [
            {"id": "myelinating_internode", "label": "Myelinating internode", "description": "One Schwann cell wraps one axon segment between exposed paranodal ends."},
            {"id": "nonmyelinating_bundle", "label": "Nonmyelinating bundle", "description": "A nonmyelinating Schwann cell cytoplasm surrounds several small axons in a Remak-like bundle."},
        ],
        "limits": "Generic peripheral glial topology; the second form is nonmyelinating and does not imply disease or axon loss.",
        "refs": ["schwann_remak"],
    },
    "dendritic_spine": {
        "key": "dendritic_spine", "name": "Dendritic spine", "category": "neurobiology", "subcategory": "dendrite",
        "synonyms": ["spine head", "spine neck", "postsynaptic protrusion"],
        "forms": [
            {"id": "mushroom", "label": "Mushroom", "description": "A relatively broad head on a short, wider neck rising from a dendritic shaft."},
            {"id": "thin", "label": "Thin", "description": "A small head on a slender neck rising from a dendritic shaft."},
        ],
        "limits": "Morphology classes are simplified schematic forms; real spine shapes vary continuously and are context dependent.",
        "refs": ["synapse_ultrastructure"],
    },
    "axon_terminal": {
        "key": "axon_terminal", "name": "Axon terminal", "category": "neurobiology", "subcategory": "axon",
        "synonyms": ["nerve ending", "presynaptic terminal", "terminal bouton"],
        "forms": [
            {"id": "single_bouton", "label": "Single bouton", "description": "One terminal bouton at the end of a short axon segment."},
            {"id": "branched_terminals", "label": "Branched terminals", "description": "A terminal axon branch ending in several separate boutons."},
        ],
        "limits": "Terminal morphology only; does not assert target cell, transmitter, release probability, or synaptic effect.",
        "refs": ["synapse_ultrastructure"],
    },
    "neuron_astrocyte_contact": {
        "key": "neuron_astrocyte_contact", "name": "Neuron–astrocyte contact", "category": "neurobiology", "subcategory": "neuron-glia contact",
        "synonyms": ["tripartite synapse", "perisynaptic astrocyte process", "astrocyte-neuron interface"],
        "forms": [
            {"id": "single_synapse", "label": "Single synapse contact", "description": "An astrocyte process approaches one synaptic site formed by a bouton and spine."},
            {"id": "process_network", "label": "Process network", "description": "A branching astrocyte process mesh approaches multiple neuronal elements."},
        ],
        "limits": "Anatomical contact schematic; does not imply universal coverage, signaling direction, or functional regulation.",
        "refs": ["astrocyte_meshwork"],
    },
    "microglia_contact": {
        "key": "microglia_contact", "name": "Microglial process contact", "category": "neurobiology", "subcategory": "neuron-glia contact",
        "synonyms": ["microglia-synapse contact", "microglial surveillance", "microglial process"],
        "forms": [
            {"id": "surveying", "label": "Surveying processes", "description": "A ramified microglial cell with thin processes extending through nearby tissue."},
            {"id": "synaptic_contact", "label": "Synaptic contact", "description": "One microglial process touches a synaptic region without engulfment or removal."},
        ],
        "limits": "Neutral morphology/contact schematic; no implication of synaptic pruning, phagocytosis, activation state, or injury.",
        "refs": ["microglia_synapse_contact"],
    },
    "node_of_ranvier": {
        "key": "node_of_ranvier", "name": "Node of Ranvier", "category": "neurobiology", "subcategory": "axon and myelin",
        "synonyms": ["node", "paranode", "myelin gap"],
        "forms": [
            {"id": "paired_internodes", "label": "Paired internodes", "description": "An exposed axon gap between two adjacent myelin internodes."},
            {"id": "channel_region", "label": "Nodal channel region", "description": "A magnified axon segment with a compact channel-rich nodal region flanked by myelin ends."},
        ],
        "limits": "Simplified nodal domain; molecular identities and conduction dynamics are not represented.",
        "refs": ["oligo_multiaxon", "schwann_remak"],
    },
    "neural_circuit": {
        "key": "neural_circuit", "name": "Neural circuit", "category": "neurobiology", "subcategory": "circuit",
        "synonyms": ["neuronal circuit", "feedforward pathway", "convergent input"],
        "forms": [
            {"id": "feedforward_chain", "label": "Feedforward chain", "description": "A generic series of neuronal nodes connected by directional arrows."},
            {"id": "convergent_inputs", "label": "Convergent inputs", "description": "Several upstream nodes project toward one downstream node."},
        ],
        "limits": "Generic directional connectivity only; arrows show schematic information flow and make no claim about excitation, inhibition, cell identity, or measured activity.",
        "refs": ["feedforward_convergence"],
    },
}


_REGIONS = {
    "chemical_synapse": [("presynaptic", "Presynaptic bouton", "#F4A261"), ("postsynaptic", "Postsynaptic structure", "#C7F2EC"), ("cleft", "Synaptic cleft", "#D9F4E5"), ("vesicles", "Synaptic vesicles", "#FFFFFF"), ("outline", "Structural outline", "#26323D")],
    "axon_myelin": [("axon", "Axon", "#F4A261"), ("myelin", "Myelin", "#8EC8FF"), ("periaxonal_space", "Periaxonal space", "#D9F4E5"), ("outline", "Structural outline", "#26323D")],
    "oligodendrocyte": [("soma", "Oligodendrocyte soma", "#B8B5FF"), ("process", "Cell processes", "#D9D7FF"), ("myelin", "Myelin sheaths", "#8EC8FF"), ("axon", "Axons", "#F4A261"), ("outline", "Structural outline", "#26323D")],
    "schwann_cell": [("schwann_cytoplasm", "Schwann cell cytoplasm", "#D9F4E5"), ("axon", "Axons", "#F4A261"), ("ensheathment", "Schwann cell ensheathment", "#8EC8FF"), ("periaxonal_space", "Periaxonal spaces", "#FFFFFF"), ("outline", "Structural outline", "#26323D")],
    "dendritic_spine": [("dendrite", "Dendrite", "#C7F2EC"), ("spine", "Spine", "#8EC8FF"), ("postsynaptic_density", "Postsynaptic density", "#F4A261"), ("outline", "Structural outline", "#26323D")],
    "axon_terminal": [("axon", "Axon", "#F4A261"), ("terminal", "Terminal boutons", "#F4A261"), ("vesicles", "Vesicle marks", "#FFFFFF"), ("outline", "Structural outline", "#26323D")],
    "neuron_astrocyte_contact": [("neuron", "Postsynaptic neuron", "#8EC8FF"), ("presynaptic", "Presynaptic terminal", "#F4A261"), ("astrocyte", "Astrocyte processes", "#B8B5FF"), ("cleft", "Synaptic cleft", "#FFFFFF"), ("outline", "Structural outline", "#26323D")],
    "microglia_contact": [("microglia", "Microglial soma", "#B8B5FF"), ("process", "Microglial processes", "#D9D7FF"), ("neural_target", "Neuronal elements", "#C7F2EC"), ("outline", "Structural outline", "#26323D")],
    "node_of_ranvier": [("axon", "Axon", "#F4A261"), ("myelin", "Myelin internodes", "#8EC8FF"), ("nodal_region", "Nodal region", "#D9F4E5"), ("outline", "Structural outline", "#26323D")],
    "neural_circuit": [("neuron", "Neuronal nodes", "#C7F2EC"), ("connection", "Directional connections", "#8EC8FF"), ("arrow", "Arrowheads", "#F4A261"), ("outline", "Structural outline", "#26323D")],
}


def regions_for(key: str, index: int) -> list[dict[str, str]]:
    """Return stable semantic recolor regions shared by a concept's forms."""
    concept = CONCEPTS[key]
    if index not in (0, 1):
        raise IndexError("form index must be 0 or 1")
    return [{"id": rid, "label": label, "default": color} for rid, label, color in _REGIONS[key]]


def _art(key: str, index: int) -> str:
    """Return original region-grouped geometry for one concept and form."""
    O = '#26323D'
    if key == "chemical_synapse":
        bouton = "M24 44 Q24 33 36 29 Q43 26 52 29 V20 Q52 14 58 14 H66 Q72 14 72 20 V29 Q82 26 91 31 Q101 36 101 48 V55 Q101 67 90 70 H36 Q24 68 24 55Z"
        stem = "M52 31 V20 Q52 14 58 14 H66 Q72 14 72 20 V31"
        vesicles = '<circle cx="43" cy="43" r="4.5"/><circle cx="62" cy="39" r="4.5"/><circle cx="82" cy="45" r="4.5"/>'
        cleft = "M30 73 H96 V77 H30Z"
        if index == 0:
            post = "M18 100 Q41 98 57 100 L58 95 Q58 91 63 88 Q57 86 57 84 Q57 80 65 80 Q73 80 73 84 Q73 87 67 88 Q72 91 72 95 L73 100 Q91 98 110 100 L110 112 Q64 117 18 112Z"
        else:
            post = "M18 80 Q64 78 110 80 L110 108 Q64 113 18 108Z"
        return f'''<g data-region="postsynaptic" fill="#C7F2EC"><path d="{post}"/></g><g data-region="presynaptic" fill="#F4A261"><path d="{bouton}"/></g><g data-region="vesicles" fill="#FFFFFF">{vesicles}</g><g data-region="cleft" fill="#D9F4E5"><path d="{cleft}"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="{post}"/><path d="{bouton}"/><path d="{stem}"/><g stroke-width="1.5">{vesicles}</g></g>'''
    if key == "axon_myelin" and index == 0:
        # Long paired sheath walls, separated by a genuine exposed nodal gap.
        # Rounded internode ends are only at x=18/56 and x=72/111; the center
        # remains a thin continuous axon rather than a stack of ring profiles.
        top = "M24 31 H49 Q56 31 56 38 V51 H18 V38 Q18 31 24 31Z M79 31 H104 Q111 31 111 38 V51 H72 V38 Q72 31 79 31Z"
        bottom = "M18 77 H56 V90 Q56 97 49 97 H24 Q18 97 18 90Z M72 77 H111 V90 Q111 97 104 97 H79 Q72 97 72 90Z"
        peri_top = "M18 52 H56 V57 H18Z M72 52 H111 V57 H72Z"
        peri_bottom = "M18 71 H56 V76 H18Z M72 71 H111 V76 H72Z"
        axon = "M12 60 Q12 58 15 58 H113 Q116 58 116 61 V67 Q116 70 113 70 H15 Q12 70 12 67Z"
        return f'''<g data-region="myelin" fill="#8EC8FF"><path d="{top}"/><path d="{bottom}"/></g><g data-region="periaxonal_space" fill="#D9F4E5"><path d="{peri_top}"/><path d="{peri_bottom}"/></g><g data-region="axon" fill="#F4A261"><path d="{axon}"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="{top}"/><path d="{bottom}"/><path d="{peri_top}"/><path d="{peri_bottom}"/><path d="{axon}"/><path d="M56 38 V51 M72 38 V51 M56 77 V90 M72 77 V90"/></g>'''
    if key == "axon_myelin":
        return f'''<g data-region="myelin" fill="#8EC8FF"><circle cx="64" cy="64" r="39"/><circle cx="64" cy="64" r="31" fill="#FFFFFF"/><circle cx="64" cy="64" r="25" fill="#8EC8FF"/><circle cx="64" cy="64" r="18" fill="#FFFFFF"/></g><g data-region="periaxonal_space" fill="#D9F4E5"><circle cx="64" cy="64" r="16.5"/></g><g data-region="axon" fill="#F4A261"><circle cx="64" cy="64" r="12"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5"><circle cx="64" cy="64" r="39"/><circle cx="64" cy="64" r="31"/><circle cx="64" cy="64" r="25"/><circle cx="64" cy="64" r="18"/><circle cx="64" cy="64" r="12"/></g>'''
    if key == "oligodendrocyte" and index == 0:
        return f'''<g data-region="myelin" fill="#8EC8FF"><rect x="70" y="20" width="35" height="12" rx="6"/><rect x="73" y="56" width="34" height="12" rx="6"/><rect x="69" y="94" width="37" height="12" rx="6"/></g><g data-region="process" fill="none" stroke="#D9D7FF" stroke-width="8" stroke-linecap="round"><path d="M52 57 Q65 43 76 27M56 64 Q69 62 78 62M52 72 Q66 85 76 100"/></g><g data-region="soma" fill="#B8B5FF"><ellipse cx="39" cy="64" rx="18" ry="21"/><circle cx="39" cy="64" r="6" fill="#7B78C9"/></g><g data-region="axon" fill="#F4A261"><rect x="73" y="23" width="29" height="6" rx="3"/><rect x="76" y="59" width="28" height="6" rx="3"/><rect x="72" y="97" width="31" height="6" rx="3"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="39" cy="64" rx="18" ry="21"/><path d="M52 57 Q65 43 76 27M56 64 Q69 62 78 62M52 72 Q66 85 76 100"/><rect x="70" y="20" width="35" height="12" rx="6"/><rect x="73" y="56" width="34" height="12" rx="6"/><rect x="69" y="94" width="37" height="12" rx="6"/><rect x="73" y="23" width="29" height="6" rx="3" stroke-width="1.5"/><rect x="76" y="59" width="28" height="6" rx="3" stroke-width="1.5"/><rect x="72" y="97" width="31" height="6" rx="3" stroke-width="1.5"/></g>'''
    if key == "oligodendrocyte":
        return f'''<g data-region="myelin" fill="#8EC8FF"><rect x="19" y="22" width="29" height="11" rx="5.5"/><rect x="80" y="22" width="29" height="11" rx="5.5"/><rect x="16" y="96" width="31" height="11" rx="5.5"/><rect x="81" y="96" width="31" height="11" rx="5.5"/></g><g data-region="process" fill="none" stroke="#D9D7FF" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"><path d="M54 56 Q46 42 33 29M70 56 Q80 42 94 29M52 73 Q42 87 31 101M72 73 Q83 87 96 101"/></g><g data-region="soma" fill="#B8B5FF"><circle cx="63" cy="64" r="18"/><circle cx="63" cy="64" r="6" fill="#7B78C9"/></g><g data-region="axon" fill="#F4A261"><rect x="21" y="24.5" width="25" height="6" rx="3"/><rect x="82" y="24.5" width="25" height="6" rx="3"/><rect x="18" y="98.5" width="27" height="6" rx="3"/><rect x="83" y="98.5" width="27" height="6" rx="3"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="63" cy="64" r="18"/><path d="M54 56 Q46 42 33 29M70 56 Q80 42 94 29M52 73 Q42 87 31 101M72 73 Q83 87 96 101"/><rect x="19" y="22" width="29" height="11" rx="5.5"/><rect x="80" y="22" width="29" height="11" rx="5.5"/><rect x="16" y="96" width="31" height="11" rx="5.5"/><rect x="81" y="96" width="31" height="11" rx="5.5"/><rect x="21" y="24.5" width="25" height="6" rx="3" stroke-width="1.5"/><rect x="82" y="24.5" width="25" height="6" rx="3" stroke-width="1.5"/><rect x="18" y="98.5" width="27" height="6" rx="3" stroke-width="1.5"/><rect x="83" y="98.5" width="27" height="6" rx="3" stroke-width="1.5"/></g>'''
    if key == "schwann_cell" and index == 0:
        return f'''<g data-region="ensheathment" fill="#8EC8FF"><rect x="34" y="43" width="59" height="43" rx="16"/></g><g data-region="periaxonal_space" fill="#FFFFFF"><rect x="38" y="52" width="51" height="25" rx="10"/></g><g data-region="schwann_cytoplasm" fill="#D9F4E5"><path d="M39 43 Q53 29 76 36 L91 44 Q79 40 74 46 L48 46Z"/><ellipse cx="64" cy="38" rx="10" ry="6"/></g><g data-region="axon" fill="#F4A261"><rect x="17" y="58" width="94" height="13" rx="6.5"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><rect x="34" y="43" width="59" height="43" rx="16"/><rect x="38" y="52" width="51" height="25" rx="10"/><rect x="17" y="58" width="94" height="13" rx="6.5"/><path d="M37 47 Q53 31 76 36 L91 44M48 46 Q63 43 77 46"/><ellipse cx="64" cy="38" rx="10" ry="6"/></g>'''
    if key == "schwann_cell":
        cell = "M20 35 Q30 23 46 24 Q62 20 77 24 Q97 27 108 42 Q115 60 107 83 Q101 103 82 108 Q61 114 43 108 Q23 102 17 83 Q12 60 20 35Z"
        # Open, flared invagination walls leave each small axon naked; these
        # are not closed concentric myelin rings. Broad cell bridges connect
        # the pockets into one Schwann-cell cytoplasm.
        pockets = "M31 37 Q29 44 32 52 Q35 60 44 61 Q53 60 56 52 Q59 44 57 37 M71 37 Q69 44 72 52 Q75 60 84 61 Q93 60 96 52 Q99 44 97 37 M31 73 Q29 80 32 88 Q35 96 44 97 Q53 96 56 88 Q59 80 57 73 M71 73 Q69 80 72 88 Q75 96 84 97 Q93 96 96 88 Q99 80 97 73"
        spaces = "M34 40 Q33 46 35 52 Q38 57 44 58 Q50 57 53 52 Q55 46 54 40 M74 40 Q73 46 75 52 Q78 57 84 58 Q90 57 93 52 Q95 46 94 40 M34 76 Q33 82 35 88 Q38 93 44 94 Q50 93 53 88 Q55 82 54 76 M74 76 Q73 82 75 88 Q78 93 84 94 Q90 93 93 88 Q95 82 94 76"
        bridges = "M56 52 Q64 47 72 52 M56 88 Q64 83 72 88 M44 61 Q44 67 44 73 M84 61 Q84 67 84 73"
        return f'''<g data-region="schwann_cytoplasm" fill="#D9F4E5"><path d="{cell}"/><path d="{bridges}" fill="none" stroke="#D9F4E5" stroke-width="8" stroke-linecap="round"/></g><g data-region="ensheathment" fill="none" stroke="#8EC8FF" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"><path d="{pockets}"/></g><g data-region="periaxonal_space" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="{spaces}"/></g><g data-region="axon" fill="#F4A261"><circle cx="44" cy="46" r="5.8"/><circle cx="84" cy="46" r="5.8"/><circle cx="44" cy="82" r="5.8"/><circle cx="84" cy="82" r="5.8"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="{cell}"/><path d="{bridges}" stroke-width="2"/><path d="{pockets}" stroke-width="1.5"/><path d="{spaces}" stroke-width="1"/><circle cx="44" cy="46" r="5.8"/><circle cx="84" cy="46" r="5.8"/><circle cx="44" cy="82" r="5.8"/><circle cx="84" cy="82" r="5.8"/></g>'''
    if key == "dendritic_spine" and index == 0:
        spine = "M58 70 Q57 57 55 48 Q43 43 42 33 Q41 21 55 18 Q71 14 82 23 Q91 31 84 42 Q79 49 68 49 L68 70Z"
        return f'''<g data-region="dendrite" fill="#C7F2EC"><path d="M18 72 Q60 68 110 72 L110 104 Q63 109 18 102Z"/></g><g data-region="spine" fill="#8EC8FF"><path d="{spine}"/></g><g data-region="postsynaptic_density" fill="#F4A261"><path d="M72 22 Q84 25 85 34 Q84 41 77 44 L74 39 Q81 34 76 29Z"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 72 Q60 68 110 72 L110 104 Q63 109 18 102Z"/><path d="{spine}"/><path d="M72 22 Q84 25 85 34 Q84 41 77 44"/></g>'''
    if key == "dendritic_spine":
        spine = "M58 71 Q58 52 54 36 Q44 33 46 25 Q48 17 58 18 Q69 19 69 28 Q69 34 63 37 L66 71Z"
        return f'''<g data-region="dendrite" fill="#C7F2EC"><path d="M18 72 Q60 68 110 72 L110 104 Q63 109 18 102Z"/></g><g data-region="spine" fill="#8EC8FF"><path d="{spine}"/></g><g data-region="postsynaptic_density" fill="#F4A261"><path d="M60 20 Q68 22 68 28 Q68 32 64 34"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 72 Q60 68 110 72 L110 104 Q63 109 18 102Z"/><path d="{spine}"/><path d="M60 20 Q68 22 68 28 Q68 32 64 34"/></g>'''
    if key == "axon_terminal" and index == 0:
        return f'''<g data-region="axon" fill="#F4A261"><path d="M18 62 Q50 59 73 61 L80 56 Q90 52 100 59 Q110 67 102 77 Q96 85 83 80 L73 73 Q48 76 18 74Z"/></g><g data-region="terminal" fill="#F4A261"><ellipse cx="94" cy="68" rx="13" ry="15"/></g><g data-region="vesicles" fill="#FFFFFF"><circle cx="91" cy="63" r="3.5"/><circle cx="99" cy="69" r="3.5"/><circle cx="91" cy="74" r="3.5"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 62 Q50 59 73 61 L80 56 Q90 52 100 59 Q110 67 102 77 Q96 85 83 80 L73 73 Q48 76 18 74Z"/><ellipse cx="94" cy="68" rx="13" ry="15"/><circle cx="91" cy="63" r="3.5" stroke-width="1.5"/><circle cx="99" cy="69" r="3.5" stroke-width="1.5"/><circle cx="91" cy="74" r="3.5" stroke-width="1.5"/></g>'''
    if key == "axon_terminal":
        return f'''<g data-region="axon" fill="#F4A261"><path d="M17 62 Q46 61 65 64 L77 48 Q84 40 94 43 L103 49 Q107 54 101 58 L83 67 L98 80 Q104 85 98 91 Q89 97 81 89 L66 73 Q45 76 17 74Z"/></g><g data-region="terminal" fill="#F4A261"><circle cx="96" cy="51" r="10"/><circle cx="96" cy="88" r="10"/></g><g data-region="vesicles" fill="#FFFFFF"><circle cx="95" cy="50" r="3.5"/><circle cx="99" cy="55" r="3.5"/><circle cx="95" cy="87" r="3.5"/><circle cx="99" cy="92" r="3.5"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 62 Q46 61 65 64 L77 48 Q84 40 94 43 L103 49 Q107 54 101 58 L83 67 L98 80 Q104 85 98 91 Q89 97 81 89 L66 73 Q45 76 17 74Z"/><circle cx="96" cy="51" r="10"/><circle cx="96" cy="88" r="10"/><circle cx="95" cy="50" r="3.5" stroke-width="1.5"/><circle cx="99" cy="55" r="3.5" stroke-width="1.5"/><circle cx="95" cy="87" r="3.5" stroke-width="1.5"/><circle cx="99" cy="92" r="3.5" stroke-width="1.5"/></g>'''
    if key == "neuron_astrocyte_contact" and index == 0:
        post = "M18 81 Q40 79 58 82 L62 82 L62 72 Q57 69 58 64 Q58 58 66 57 Q73 54 81 58 Q87 61 86 66 Q85 70 81 72 L81 82 L107 82 L107 103 Q63 108 18 102Z"
        stem = "M68 25 V16 Q68 12 72 12 H76 Q80 12 80 16 V25Z"
        vesicles = '<circle cx="63" cy="35" r="3.2"/><circle cx="72" cy="30" r="3.2"/><circle cx="82" cy="36" r="3.2"/><circle cx="73" cy="44" r="3.2"/>'
        cleft = "M57 54 Q73 51 89 54 L88 58 Q73 55 58 58Z"
        astro = "M112 29 Q101 32 97 39 Q94 45 92 52 Q91 55 90 56"
        return f'''<g data-region="neuron" fill="#8EC8FF"><path d="{post}"/></g><g data-region="presynaptic" fill="#F4A261"><path d="{stem}"/><ellipse cx="73" cy="39" rx="20" ry="16"/>{vesicles}</g><g data-region="cleft" fill="#FFFFFF"><path d="{cleft}"/></g><g data-region="astrocyte" fill="none" stroke="#B8B5FF" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"><path d="{astro}"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="{post}"/><path d="{stem}"/><ellipse cx="73" cy="39" rx="20" ry="16"/><g stroke-width="1.5">{vesicles}</g><path d="{astro}"/><path d="M57 55 Q73 52 89 55M58 59 Q73 56 88 59"/></g>'''
    if key == "neuron_astrocyte_contact":
        post = "M18 89 Q41 86 63 90 Q84 86 110 90 L110 106 Q64 112 18 105Z"
        spine_left = "M43 90 Q46 78 45 69 Q44 62 50 60 Q57 60 59 67 Q60 73 55 76 L58 88Z"
        spine_right = "M78 88 Q81 77 80 68 Q80 61 86 59 Q93 60 94 67 Q95 73 89 76 L91 88Z"
        axon_paths = "M42 31 Q46 34 50 40 M87 28 Q84 33 86 40"
        boutons = '<ellipse cx="52" cy="48" rx="12" ry="8"/><ellipse cx="86" cy="48" rx="12" ry="8"/>'
        vesicles = '<circle cx="48" cy="47" r="2.8"/><circle cx="54" cy="44" r="2.8"/><circle cx="58" cy="49" r="2.8"/><circle cx="82" cy="47" r="2.8"/><circle cx="88" cy="44" r="2.8"/><circle cx="92" cy="49" r="2.8"/>'
        clefts = "M42 56 Q52 54 62 56 L62 60 Q52 58 42 60Z M76 56 Q86 54 96 56 L96 60 Q86 58 76 60Z"
        astro = "M68 101 Q66 84 69 72 Q72 62 69 53 Q67 43 72 33 Q76 25 86 20 M69 49 Q68 34 58 22 Q51 15 44 17 M70 46 Q79 34 92 23 Q98 19 105 22 M68 81 Q53 85 32 84"
        return f'''<g data-region="neuron" fill="#8EC8FF"><circle cx="33" cy="30" r="9"/><circle cx="96" cy="28" r="9"/><path d="{post}"/><path d="{spine_left}"/><path d="{spine_right}"/></g><g data-region="presynaptic" fill="#F4A261"><path d="{axon_paths}"/><g>{boutons}</g>{vesicles}</g><g data-region="cleft" fill="#FFFFFF"><path d="{clefts}"/></g><g data-region="astrocyte" fill="none" stroke="#B8B5FF" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"><path d="{astro}"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="33" cy="30" r="9"/><circle cx="96" cy="28" r="9"/><path d="{post}"/><path d="{spine_left}"/><path d="{spine_right}"/><path d="{axon_paths}"/>{boutons}<g stroke-width="1.5">{vesicles}</g><path d="{astro}"/><path d="M42 56 Q52 54 62 56M42 60 Q52 58 62 60M76 56 Q86 54 96 56M76 60 Q86 58 96 60"/></g>'''
    if key == "microglia_contact" and index == 0:
        return f'''<g data-region="neural_target" fill="#C7F2EC"><path d="M91 96 Q101 92 112 95 L112 105 Q102 108 91 104Z"/><path d="M99 96 Q98 88 103 85 Q108 87 107 95Z"/></g><g data-region="process" fill="none" stroke="#D9D7FF" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"><path d="M55 55 Q46 43 31 35M52 64 Q42 59 28 54M55 73 Q41 76 27 91M73 55 Q82 42 99 32M76 64 Q88 62 105 59M73 73 Q79 78 84 83M64 76 Q51 80 40 90"/></g><g data-region="microglia" fill="#B8B5FF"><circle cx="64" cy="64" r="12"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M55 55 Q46 43 31 35M52 64 Q42 59 28 54M55 73 Q41 76 27 91M73 55 Q82 42 99 32M76 64 Q88 62 105 59M73 73 Q79 78 84 83M64 76 Q51 80 40 90"/><circle cx="64" cy="64" r="12"/><path d="M91 96 Q101 92 112 95 L112 105 Q102 108 91 104ZM99 96 Q98 88 103 85 Q108 87 107 95Z"/></g>'''
    if key == "microglia_contact":
        return f'''<g data-region="neural_target" fill="#C7F2EC"><path d="M75 71 Q74 59 83 53 Q93 48 101 57 Q106 66 99 74 Q92 81 82 77Z"/><path d="M78 79 Q88 78 101 80 L101 96 Q87 99 78 95Z"/></g><g data-region="process" fill="none" stroke="#D9D7FF" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"><path d="M55 63 Q62 59 66 63 Q72 69 78 69M47 53 Q35 44 22 34M31 64 Q28 61 17 56M31 64 Q28 78 19 94M48 75 Q51 87 64 98M31 57 Q35 48 39 35"/></g><g data-region="microglia" fill="#B8B5FF"><circle cx="43" cy="64" r="12"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M75 71 Q74 59 83 53 Q93 48 101 57 Q106 66 99 74 Q92 81 82 77Z"/><path d="M78 79 Q88 78 101 80 L101 96 Q87 99 78 95Z"/><path d="M55 63 Q62 59 66 63 Q72 69 78 69M47 53 Q35 44 22 34M31 64 Q28 61 17 56M31 64 Q28 78 19 94M48 75 Q51 87 64 98M31 57 Q35 48 39 35"/><circle cx="43" cy="64" r="12"/></g>'''
    if key == "node_of_ranvier" and index == 0:
        return f'''<g data-region="axon" fill="#F4A261"><rect x="17" y="58" width="94" height="13" rx="6.5"/></g><g data-region="myelin" fill="#8EC8FF"><rect x="18" y="46" width="38" height="37" rx="14"/><rect x="72" y="46" width="38" height="37" rx="14"/></g><g data-region="nodal_region" fill="#D9F4E5"><rect x="57" y="51" width="14" height="28" rx="5"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><rect x="18" y="46" width="38" height="37" rx="14"/><rect x="72" y="46" width="38" height="37" rx="14"/><rect x="17" y="58" width="94" height="13" rx="6.5"/><path d="M56 51v28M72 51v28"/></g>'''
    if key == "node_of_ranvier":
        return f'''<g data-region="axon" fill="#F4A261"><rect x="17" y="57" width="94" height="14" rx="7"/></g><g data-region="myelin" fill="#8EC8FF"><path d="M17 43 H49 Q57 43 57 51 V77 Q57 85 49 85 H17Z"/><path d="M111 43 H79 Q71 43 71 51 V77 Q71 85 79 85 H111Z"/></g><g data-region="nodal_region" fill="#D9F4E5"><rect x="58" y="51" width="12" height="26" rx="4"/><g fill="#F4A261"><circle cx="61" cy="56" r="2"/><circle cx="67" cy="56" r="2"/><circle cx="61" cy="63" r="2"/><circle cx="67" cy="63" r="2"/><circle cx="61" cy="70" r="2"/><circle cx="67" cy="70" r="2"/></g></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 43 H49 Q57 43 57 51 V77 Q57 85 49 85 H17ZM111 43 H79 Q71 43 71 51 V77 Q71 85 79 85 H111Z"/><rect x="17" y="57" width="94" height="14" rx="7"/><rect x="58" y="51" width="12" height="26" rx="4"/></g>'''
    if key == "neural_circuit" and index == 0:
        return f'''<g data-region="connection" fill="none" stroke="#8EC8FF" stroke-width="4" stroke-linecap="round"><path d="M38 64 H51M76 64 H89"/></g><g data-region="arrow" fill="#F4A261"><path d="M39 59 L51 64 L39 69Z"/><path d="M77 59 L89 64 L77 69Z"/></g><g data-region="neuron" fill="#C7F2EC"><circle cx="26" cy="64" r="10.5"/><circle cx="64" cy="64" r="10.5"/><circle cx="102" cy="64" r="10.5"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="26" cy="64" r="10.5"/><circle cx="64" cy="64" r="10.5"/><circle cx="102" cy="64" r="10.5"/></g>'''
    if key == "neural_circuit":
        return f'''<g data-region="connection" fill="none" stroke="#8EC8FF" stroke-width="4" stroke-linecap="round"><path d="M39 35 Q46 38 52 51M39 93 Q46 90 52 77M82 64 H91"/></g><g data-region="arrow" fill="#F4A261"><path d="M45 46 L53 54 L43 53Z"/><path d="M45 82 L53 74 L43 75Z"/><path d="M84 59 L92 64 L84 69Z"/></g><g data-region="neuron" fill="#C7F2EC"><circle cx="27" cy="34" r="13"/><circle cx="27" cy="94" r="13"/><circle cx="68" cy="64" r="14"/><circle cx="103" cy="64" r="10"/></g><g data-region="outline" fill="none" stroke="{O}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="27" cy="34" r="13"/><circle cx="27" cy="94" r="13"/><circle cx="68" cy="64" r="14"/><circle cx="103" cy="64" r="10"/></g>'''
    raise KeyError((key, index))


def render_svg(key: str, index: int, title: str, description: str) -> str:
    """Render one accessible, safe, editable 128 px SVG drawing."""
    if key not in CONCEPTS:
        raise KeyError(key)
    if index not in (0, 1):
        raise IndexError("form index must be 0 or 1")
    t, d = escape(title), escape(description)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc" data-asset="neuro.{key}.{CONCEPTS[key]["forms"][index]["id"]}">'
            f'<title id="title">{t}</title><desc id="desc">{d}</desc>{_art(key, index)}</svg>')
