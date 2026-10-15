# Protein Homeostasis asset review — 7 October 2026

## Scope

Eight original editable vectors extend the shared Figure and Present Library. This family fills gaps around protein states and interactions; it retains the existing standalone proteasome, ubiquitin-chain, lysosome and autophagosome concepts. No new Scene, app interaction, native build or publication is included.

| Asset | Biological meaning | Important limit |
|---|---|---|
| Unfolded Polypeptide | Illustrative extended polypeptide with a continuous protein backbone and sparse exposed hydrophobic-segment cues; no sequence or measured conformation is represented. | No sequence, residue count, end chemistry, atomic conformation or measured residue exposure. Do not relabel as an intrinsically disordered protein without biological context. |
| Misfolded Protein | Illustrative non-native partial protein fold with sparse exposed hydrophobic-patch cues. | Geometry and patches are explanatory cues, not measured tertiary structure or hydrophobicity. Do not imply inevitable aggregation. |
| HSP70–Client Complex | Illustrative HSP70-family chaperone with connected nucleotide-binding and substrate-binding domains holding an extended client region. | No species, isoform, nucleotide state or complete co-chaperone system. Association does not demonstrate successful folding. |
| HSP90–Client Complex | Illustrative two-protomer HSP90-family chaperone associated with a client segment at its central lumen. | No species, isoform, nucleotide state or co-chaperone composition. No universal activation, complete maturation complex or invariably unfolded client. |
| RING E3 Ubiquitination Complex | Illustrative RING E3 supporting an E2–ubiquitin conjugate beside a substrate for direct E2-to-substrate transfer. | No named enzyme, substrate or linkage. No E3–ubiquitin covalent intermediate. Attachment alone does not establish proteasomal degradation. |
| Deubiquitinase–Substrate Complex | Illustrative DUB engaging ubiquitin and the attachment joining it to a substrate protein. | Substrate backbone remains intact; cleavage concerns the ubiquitin attachment. No family identity, linkage specificity or automatic substrate rescue. |
| Proteasomal Substrate Processing | Illustrative proteasomal processing with one entering polypeptide and short peptides leaving the proteolytic core. | Depicts a processing relationship distinct from the existing standalone proteasome. No intact folded globule or attached polyubiquitin through the core. No exact conformation, identity, rate or chain linkage. |
| Amorphous Protein Aggregate | Illustrative irregular nonfibrillar grouping of interacting protein chains without a membrane boundary or repetitive amyloid architecture. | No amyloid, toxicity, measured insolubility or complete unfolding claim. Do not make aggregation an inevitable result of misfolding or chaperone association. |

## Original construction and scientific precedents

The six selected primary figures below were visually inspected before geometry authoring. They inform topology and biological relationships only. All paths, silhouettes and layouts were constructed anew; no published artwork, molecular coordinates or proprietary asset was copied or traced.

- [Qi R, Sarbeng EB, Liu Q, et al. Allosteric opening of the polypeptide-binding site when an Hsp70 binds ATP. Nature Structural & Molecular Biology. 2013;20:900–907.](https://pmc.ncbi.nlm.nih.gov/articles/PMC3772632/) Figure 1: Separate HSP70 nucleotide-binding domain, linker, substrate-binding domain and lid; retain an extended client segment. Figure and caption inspected.
- [Wang RY-R, Noddings CM, Kirschke E, Myasnikov AG, Johnson JL, Agard DA. Structure of Hsp90–Hsp70–Hop–GR reveals the Hsp90 client-loading mechanism. Nature. 2022;601:460–464.](https://pmc.ncbi.nlm.nih.gov/articles/PMC9179170/) Figure 4: Make the client's extended binding region visible and preserve client identity through chaperone handling. Figure and caption inspected.
- [Noddings CM, Wang RY-R, Johnson JL, Agard DA. Structure of Hsp90–p23–GR reveals the Hsp90 client-remodelling mechanism. Nature. 2022;601:465–469.](https://pmc.ncbi.nlm.nih.gov/articles/PMC8994517/) Figure 1: Show two HSP90 protomers, a central lumen and a client segment passing between them while most client mass remains outside. Figure and caption inspected.
- [Dou H, Buetow L, Sibbet GJ, Cameron K, Huang DT. BIRC7–E2 ubiquitin conjugate structure reveals the mechanism of ubiquitin transfer by a RING dimer. Nature Structural & Molecular Biology. 2012;19:876–883.](https://pmc.ncbi.nlm.nih.gov/articles/PMC3880866/) Figure 1: Keep donor ubiquitin attached to E2 and RING E3 separate; direct transfer originates from E2-bound ubiquitin. Figure and caption inspected.
- [Renatus M, Parrado SG, D'Arcy A, et al. Structural basis of ubiquitin recognition by the deubiquitinating protease USP2. Structure. 2006;14:1293–1302.](https://pmc.ncbi.nlm.nih.gov/articles/PMC7126176/) Figure 2: Use a DUB cleft engaging ubiquitin's body and C-terminal attachment region; leave the substrate backbone intact. Figure and caption inspected.
- [Dong Y, Zhang S, Wu Z, et al. Cryo-EM structures and dynamics of substrate-engaged human 26S proteasome. Nature. 2019;565:49–55.](https://pmc.ncbi.nlm.nih.gov/articles/PMC6370054/) Figure 6: Separate ubiquitin recognition/removal, translocation and degradation; depict an entering polypeptide and exiting short peptides. Figure and caption inspected.
- [Boatz JC, Whitley MJ, Li M, Gronenborn AM, van der Wel PCA. Cataract-associated P23T γD-crystallin retains a native-like fold in amorphous-looking aggregates formed at physiological pH. Nature Communications. 2017;8:15137.](https://pmc.ncbi.nlm.nih.gov/articles/PMC5424181/) Figure 8: Amorphous-looking aggregates may retain native-like folds; aggregation alone establishes neither amyloid nor toxicity. Primary summary and caption inspected; not in the six-image precedent set.

## Independent original-image review

A reviewer who did not draw the assets inspected all 24 original image boards individually: eight concepts × three treatments, with native 64 px and 256 px artwork in each board. All passed. The reviewer verified exact PNG hashes against the capture inventory; contact sheets were not substituted for original inspection.

The extended chain, compact partial fold and multichain aggregate remain distinct. HSP70 and HSP90 retain their different domain/topology cues. Ubiquitin transfer and removal do not depict protein-backbone cleavage. The processing cutaway preserves a continuous entering tail and separate short peptide products. Gold hydrophobic cues follow exact backbone intervals. No clipping was observed.

## Source/web editing status at registration

Registered in the shared Figure/Present source library on 8 October 2026. At registration, five permanent Python and three Node cases passed; actual source/web insertion, editing, Undo/Redo, export and Save/reopen were pending. Original-image acceptance did not establish those app behaviors. The subsequent contour refinement and app review are recorded in [the 11 October qualification](PROTEIN_HOMEOSTASIS_QUALIFICATION_2026_10_11.md). Scientific references and limits are retained in [the pack](../../assets/scientific-packs/protein-homeostasis/asset-pack.json) and [the reproducible science record](../../scripts/protein-homeostasis-science.json).

## Rights and release

At the original 7 October review, all eight were FS-ORIGINAL-DRAFT and explicit owner public-license selection remained pending. On 10 October the owner granted CC0 1.0 permission for all eight original vectors and their asset-specific metadata. That rights grant is separate from product acceptance; the 10 October pending catalog, rights record, notice and eight original SVGs are preserved in [the historical snapshot](../../assets/scientific-packs/protein-homeostasis/releases/2026-10-10-rights-cleared/asset-pack.json).

## Roadmap

This extends the asset library alongside the separate PDF-editing workstream. Figure/PDF v1 scope and milestones remain unchanged. A protein-homeostasis Scene can follow using these components and the existing ubiquitin/proteasome assets; named co-chaperones and linkage-specific chains remain separate slices.
