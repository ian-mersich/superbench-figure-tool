# Core Biology Provenance and License-Release Audit — 2026-07-20 Revision

This is the current release record for the 108 production styles / 90 concepts in Figure Studio's `core-biology` pack. It extends the initial 2026-07-19 CC0 release with five original model-organism assets and binds every current disposition to exact SVG and provenance SHA-256 values.

This repository record is an engineering/provenance audit, not legal advice or a non-infringement opinion.

## Decision

**Rights/provenance: PASS. CC0 promotion: APPLIED. Visual QA: PASS.**

| Gate | Result | Evidence |
| --- | --- | --- |
| Production scope | PASS | 108 styles / 90 concepts; every current SVG has one audit entry |
| New promotion | PASS | Five original model-organism vectors were created, independently reviewed, corrected, and promoted on 2026-07-20 |
| Ownership basis | PASS by owner attestation | The workspace owner states that the production assets were produced in this Figure Studio/Codex workspace |
| Third-party components | PASS on declared/structural evidence | Zero declared third-party components; SVG validation rejects raster embedding, external links, scripts, `foreignObject`, and URL-backed paint servers |
| Asset integrity | PASS | SHA-256 recorded for every SVG and every provenance string |
| Visual/scientific quality | PASS | Canonical parity v30: 35/35 checks, zero console errors; independent review found no remaining P0/P1 issue after the nematode terminal-cue correction |
| Search/discovery | PASS | 90/90 concepts have a bounded non-name search intent; model-organism, microbial-model, and invertebrate-model intent checks pass |
| Public redistribution | PASS | All 108 current records use `CC0-1.0`; public distribution is authorized for the audited asset material |

## Model-Organism Promotion

| Asset | Defining topology | Scope restraint |
| --- | --- | --- |
| `core.model.yeast_budding` | Oval mother cell, attached bud, narrow neck, vacuole, nucleus | No species, strain, ploidy, genotype, condition, or phenotype |
| `core.model.bacterium_rod` | Rounded rod envelope, unbound nucleoid, sparse ribosome dots | No species, Gram status, capsule, motility, sporulation, pathogenicity, or response |
| `core.model.zebrafish` | Slender lateral body, fins, fan tail, restrained stripes | No strain, sex, age, developmental stage, genotype, disease, or treatment |
| `core.model.fruit_fly` | Head/thorax/abdomen, one wing pair, six legs, antennae, compound-eye cues | No line, sex, age, developmental stage, genotype, or phenotype |
| `core.model.nematode` | Open C-shaped body, neutral terminal cue, restrained internal tract | No eye cue, species claim, sex, age, developmental stage, genotype, or phenotype |

The existing Mouse Model is included in `model organism` discovery, producing one six-concept family while retaining its Soft line and Manuscript style variants. No automatic manuscript companions were added for the new concepts.

## Current Lineage

| Lineage | Styles |
| --- | ---: |
| `workspace_generated_original` | 87 |
| `workspace_generated_companion_or_redraw` | 17 |
| `workspace_output_redraw_from_owner_figure` | 4 |

The five new assets are classified as `workspace_generated_original`. No third-party source, proprietary library reference, scraping, or tracing was used.

## CC0 Continuity

On 2026-07-19, the workspace owner selected **CC0 for maximum-frictionless reuse** of the Core Biology production pack. The 2026-07-20 promotion record explicitly includes the five new vectors in that owner-selected production release; new future drafts still require their own provenance, visual, and promotion review before appearing in the machine-readable released set.

Canonical reference: <https://creativecommons.org/publicdomain/zero/1.0/>

## Machine-Readable Evidence

- Current audit manifest: `assets/scientific-packs/core-biology/license-release-audit.json`
- Pack-scoped notice: `assets/scientific-packs/core-biology/LICENSE-ASSETS-CC0-1.0.md`
- Deterministic generator/check: `scripts/generate-scientific-asset-license-audit.py`
- Enforcement: `scripts/validate-scientific-assets.py`
- Canonical browser proof: `qa_artifacts/figure-studio-assets-parity-2026-07-20-v30/figure-studio-sidebar-assets-parity-proof.json`

The audit source records retain the original owner attestation, owner CC0 selection, OpenAI ownership references, redacted Illustrator source hashes, and the dated model-organism promotion record.

## Scope Boundary

This release covers only SVGs and asset-specific metadata explicitly listed with `released_under_cc0_1_0` dispositions in the current audit. It does not license Figure Studio or BSD Studio application code, general documentation, fonts, dependencies, imported content, templates, QA screenshots/artifacts, names, logos, or trademarks.
