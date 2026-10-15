# Core Biology Provenance and License-Release Audit — 2026-07-19

This is the release record for the 103 production styles in Figure Studio's `core-biology` pack. It records the available ownership evidence, binds every disposition to the current SVG and provenance text by SHA-256, and records the owner's explicit CC0 selection.

This file preserves the initial release decision. The current 108-style audit revision is `PROVENANCE_LICENSE_RELEASE_AUDIT_2026_07_20.md`.

This repository record is an engineering/provenance audit, not legal advice or a non-infringement opinion.

## Decision

**Rights/provenance: PASS. CC0 release: APPLIED.**

| Gate | Result | Evidence |
| --- | --- | --- |
| Production scope | PASS | 103 styles / 85 concepts; every current SVG has one audit entry |
| Ownership basis | PASS by owner attestation | The workspace owner states that all 103 assets were produced in this Figure Studio/Codex workspace |
| OpenAI-output disposition | PASS with qualification | Current consumer and business terms assign OpenAI's interest, if any, in Output to the user/customer, to the extent permitted by applicable law |
| Owner-workspace redraw lineage | PASS | Four redraws are identified separately; two owner-workspace Illustrator source documents are recorded by redacted SHA-256 evidence |
| Third-party components | PASS on declared/structural evidence | Zero declared third-party components; SVG validation rejects embedded raster images, external links, scripts, `foreignObject`, and URL-backed paint servers |
| Asset integrity | PASS | SHA-256 recorded for every SVG and every provenance string |
| Visual/scientific quality | PASS | Canonical parity v28: 34/34 checks, zero console errors, independent reviewer PASS |
| Public redistribution | PASS | Owner selected `CC0-1.0`; `public_distribution_authorized` is `true` for the scoped asset material |

## Audited Lineage

| Lineage | Styles | Meaning |
| --- | ---: | --- |
| `workspace_generated_original` | 82 | Original vector output produced for Figure Studio |
| `workspace_generated_companion_or_redraw` | 17 | Original thin-line companions or in-workspace redraws of existing Figure Studio concepts |
| `workspace_output_redraw_from_owner_figure` | 4 | Reusable vectors redrawn from owner-workspace graphical abstracts that were also produced in the Figure Studio/Codex workflow |

The four owner-figure redraws are:

- `core.cell.astrocyte_like`
- `core.model.cell_spheroid_cluster`
- `core.model.tumor_glia_coculture`
- `core.model.mouse_simple`

Their source type is now `owner_workspace_original_vector_redraw`, replacing the ambiguous `user_provided_original_vector_redraw` label.

## Ownership References and Limits

- OpenAI Terms of Use, effective 2026-01-01: <https://openai.com/policies/terms-of-use/>, “Content — Ownership of content.”
- OpenAI Services Agreement, effective 2026-01-01: <https://openai.com/policies/services-agreement/>, section 4.1.

These references establish the ownership position only as between the user/customer and OpenAI and only to the extent permitted by applicable law. They also warn that output may not be unique. They do not independently warrant copyrightability, uniqueness, or non-infringement.

The pack contains generic scientific schematics rather than trademarks, branded products, identifiable people, or vendor-specific equipment. No asset metadata declares a third-party work, open-license dependency, attribution obligation, or protected library reference. The audit cannot prove a universal negative against every existing illustration; it records the owner attestation, creation lineage, self-contained SVG structure, and current manual visual review.

## CC0 Release Decision

On 2026-07-19, the workspace owner explicitly selected **CC0 for maximum-frictionless reuse**. The prior alternatives remain in the audit history but are not selected:

| Candidate | Attribution | Practical effect |
| --- | --- | --- |
| `CC0-1.0` | Not required | **Selected.** Maximum reuse through a permanent public-domain dedication where possible, with an irrevocable permissive fallback. |
| `CC-BY-4.0` | Required | Permits commercial reuse and adaptation but requires reasonable creator/license attribution and modification notice. Better when attribution matters. |
| Proposed BSD Studio asset-use license | To be defined | Could allow users to use and modify assets in exported scientific figures while retaining restrictions on redistribution of the standalone source library. Best product fit if the asset library is intended to remain a competitive BSD Studio resource, but no approved license text exists yet. |

Canonical references:

- CC0 1.0 Universal: <https://creativecommons.org/publicdomain/zero/1.0/>
- Creative Commons Attribution 4.0 International: <https://creativecommons.org/licenses/by/4.0/>

All 103 production asset records now use `CC0-1.0`. The effective date and owner selection are recorded in the machine-readable audit, and `LICENSE-ASSETS-CC0-1.0.md` defines the exact pack-only scope. No attribution is required, although users must not imply endorsement and remain responsible for rights outside CC0.

## Machine-Readable Evidence

- Audit manifest: `assets/scientific-packs/core-biology/license-release-audit.json`
- Pack-scoped notice: `assets/scientific-packs/core-biology/LICENSE-ASSETS-CC0-1.0.md`
- Deterministic generator/check: `scripts/generate-scientific-asset-license-audit.py`
- Enforced by: `scripts/validate-scientific-assets.py`

The manifest intentionally redacts external local paths. It stores only neutral source-record ids, byte lengths, and SHA-256 values for the two owner-workspace Illustrator files.

## Scope Boundary

This decision covers only the Core Biology SVG pack and its asset-specific metadata as defined in the pack-scoped notice. The BSD Studio repository has no repo-level `LICENSE` file, so this audit does not license Figure Studio application code, BSD Studio code, general documentation, fonts, bundled dependencies, or QA artifacts.
