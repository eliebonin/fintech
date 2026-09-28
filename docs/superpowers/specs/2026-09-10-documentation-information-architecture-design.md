# Documentation information architecture and preservation design

**Status:** Proposed — approved direction; implementation plan pending written-spec review  
**Date:** 2026-09-10  
**Scope:** Reorganise project Markdown into a navigable, maintainable documentation system without losing any prior information.

## 1. Problem and outcome

The project has accumulated a valuable architecture notebook, product research, UI specifications, implementation plans, quality reviews, and code-adjacent READMEs. As at 2026-09-10, the repository contains 89 content Markdown files (12,733 lines). The material is detailed, but navigation currently depends on knowing historic folder names:

- `security-master-notes/` mixes durable architecture, decisions, deferred questions, implementation notes, and dated research;
- `docs/architecture/` mixes current architecture with dated implementation reviews and instrument-onboarding records;
- `ui/` mixes ADR-like decisions, product specifications, contracts, and workflows;
- `docs/superpowers/` contains formal specifications and implementation plans; and
- `fintech-moduls/` contains product-commercial material beside technical architecture.

The new information architecture must make it clear which documents are current and authoritative, which are evidence or implementation records, and how a new contributor should navigate by system/domain. It must preserve every original Markdown document and its content.

## 2. Research basis

This design combines three complementary practices rather than treating one framework as a folder-template:

1. [Diátaxis](https://diataxis.fr/) separates documentation by reader need: tutorials, how-to guides, reference, and explanation. The project will label documents by purpose, while retaining a domain-led hierarchy for technical discovery.
2. [Write the Docs — Docs as Code](https://www.writethedocs.org/guide/docs-as-code/) advocates version-controlled plain-text documentation, code review, and automated checks. The migration will be manifest-driven, link-checked, and reviewable in small changes.
3. [Architectural Decision Records](https://adr.github.io/) preserve one architecturally significant decision with its rationale and consequences. Durable decisions will be promoted into ADRs; discussion history remains available in the archive.

## 3. Goals and non-goals

### Goals

- Provide one `docs/README.md` entry point, with short reading paths for architecture, operations, product/onboarding, frontend/API, and delivery work.
- Separate maintained canonical documentation from historical discussion, plans, research, and reviews.
- Preserve all Markdown content through an immutable pre-reorganisation archive and SHA-256 manifest.
- Preserve link traceability with an old-path-to-canonical-path mapping.
- Keep application/package/data READMEs beside the code they describe, but expose them from the documentation home.
- Keep the special `docs/superpowers/specs/` and `docs/superpowers/plans/` locations as compatibility locations for the project workflow.
- Create a clear home for future ADRs, research evidence, current domain architecture, onboarding specifications, and delivery reviews.

### Non-goals

- No change to database, API, frontend, seed data, or application behaviour.
- No rewrite of technical conclusions merely for style during the migration.
- No decision reversal. Contradictory or superseded material is retained and explicitly labelled rather than silently harmonised.
- No external documentation site, static-site generator, or publishing pipeline in this slice.

## 4. Information architecture

The primary navigation is by system/domain. Each document has a declared content type and status, instead of forcing a reader to choose a Diátaxis category before locating the relevant domain.

```text
docs/
  README.md                                  # documentation home and reading paths
  governance/
    documentation-governance.md              # lifecycle, status, ownership, contribution rules
    glossary.md                              # cross-domain language
    decisions/                               # durable ADRs
      README.md
  architecture/
    README.md
    system-overview.md
    security-master/
    market-data-and-valuation/
    trading-and-operations/
    tenancy-and-entitlements/
    integrations-and-data-rights/
  product/
    README.md
    onboarding/                              # per-instrument onboarding specifications
    fintech-modules/                         # service and commercial module propositions
  platform/
    README.md
    api/
    frontend/
    data-and-schema/
  delivery/
    README.md
    quality-reviews/
    implementation-plans/                    # index into docs/superpowers/plans
    specifications/                          # index into docs/superpowers/specs
  research/
    README.md
    evidence-register.md
    topics/
  archive/
    2026-09-10-pre-reorganisation/
      README.md
      manifest.md
      source/                                # byte-preserved source Markdown snapshot

  superpowers/                               # retained workflow-compatible locations
    specs/
    plans/
```

The numeric ordering in the old notebook is not retained as the primary navigation mechanism. It is preserved in the archive manifest and a legacy-notebook index.

## 5. Document taxonomy and status

Every new or promoted canonical document must declare:

```markdown
**Status:** Draft | Accepted | Implemented | Superseded | Deferred
**Content type:** Architecture | Decision | Reference | How-to | Research | Specification | Plan | Review
**Owner:** Role or team responsible for accuracy
**Last reviewed:** YYYY-MM-DD
```

The status is document status, not a claim that every described capability is implemented.

| Content type | Purpose | Location |
|---|---|---|
| Architecture | Current system/domain design and boundaries | `docs/architecture/`, `docs/platform/` |
| Decision | A durable choice, alternatives, consequences, supersession | `docs/governance/decisions/` |
| Reference | Vocabulary, schemas, governed catalogues, interface contract | Domain or platform subfolder |
| How-to | Repeatable operational task | Domain or platform subfolder |
| Research | External evidence, comparison, non-binding exploration | `docs/research/` |
| Specification | Proposed design approved for planning/implementation | `docs/superpowers/specs/` |
| Plan | Time-bounded implementation sequence | `docs/superpowers/plans/` |
| Review | Dated assessment of implementation quality or readiness | `docs/delivery/quality-reviews/` |

## 6. Source classification and mapping rules

The exact source-to-target mapping is written during implementation in `docs/archive/2026-09-10-pre-reorganisation/manifest.md`. The rules below are deliberately deterministic.

| Existing source | Canonical treatment |
|---|---|
| Root `security-master-architecture-notes.md` | Distil into `docs/architecture/system-overview.md`; retain original in archive and link it as the historical baseline. |
| `security-master-notes/01`–`29` and README | Promote maintained topics across `architecture/security-master`, `architecture/market-data-and-valuation`, `architecture/trading-and-operations`, `architecture/tenancy-and-entitlements`, `architecture/integrations-and-data-rights`, `research`, and `governance/decisions`; retain all originals intact in archive. |
| `docs/architecture/*` | Current architecture items become architecture/platform docs; dated checkpoints and quality assessments become `delivery/quality-reviews`; dated instrument onboarding becomes `product/onboarding`. |
| `docs/superpowers/specs/*` and `docs/superpowers/plans/*` | Remain in place; `docs/delivery` contains indexed navigation rather than duplicate content. |
| `ui/decisions/*` | Retain in place initially; produce canonical ADR copies or cross-links with an explicit migration/supersession note. |
| `ui/screen-specs/*`, `ui/workflows/*`, `ui/data-contracts/*`, `ui/mvp-scope.md` | Canonical platform/frontend documentation under `docs/platform/frontend`; retain original snapshot and compatibility pointers. |
| `fintech-moduls/*` | Canonical product-commercial docs under `docs/product/fintech-modules`; retain original snapshot and compatibility pointers. |
| `apps/*/README.md`, `packages/*/README.md`, `data/mockup/README.md` | Stay colocated with their code/data. The docs home indexes them; no duplicate canonical copy is created. |
| `AGENTS.md` and `CLAUDE.md` | Not documentation content for this migration; stay in their current paths and are omitted from archive manifest scope. |

## 7. Preservation and migration controls

The migration is two-pass and reversible until a later, explicitly approved cleanup.

### Pass 1 — Inventory and archive

1. Enumerate every Markdown file in scope, its current relative path, H1 title, line count, and SHA-256 checksum.
2. Copy every in-scope source Markdown file byte-for-byte under `docs/archive/2026-09-10-pre-reorganisation/source/`, retaining its relative path.
3. Write the manifest with source path, archive path, checksum, content type, canonical destination, and migration status.
4. Verify that every archived checksum matches the pre-migration checksum recorded in the manifest. A live document may later differ only through a non-destructive compatibility notice or canonical-navigation link.

### Pass 2 — Canonical navigation and promotion

1. Create the documentation home, section READMEs, governance page, glossary seed, ADR index, evidence register, and delivery indexes.
2. Promote content only where a stable, maintained canonical document is justified. Each promoted document links to its historical sources and declares status/owner/last-reviewed metadata.
3. Add compatibility notices in the old live locations only after link checks prove the canonical route works. A notice points to the canonical page and the immutable archive; it does not delete factual content in this migration.
4. Check internal Markdown links and re-run checksum verification.

The first migration does **not** delete old documents, even if their canonical successor is created. This deliberately creates temporary duplication to eliminate information-loss risk. A later explicit decision can retire or reduce duplicate live copies once ownership and review cadence are established.

## 8. Canonical source-of-truth rules

- A page under `docs/architecture`, `docs/product`, or `docs/platform` is canonical only when it has the standard metadata and an explicit source list.
- The newest dated review is evidence, not automatically the current architecture.
- A decision is current only when its ADR status is `Accepted` or `Implemented`; a superseded ADR remains immutable and points forward.
- Research can inform a decision but must not become normative architecture without a linked decision or canonical architecture update.
- Plans and specs record intended work. Completion is established only by an implementation/review record with verification evidence.
- The archive is immutable historical evidence; no new content is authored there after the migration snapshot.

## 9. Navigation design

`docs/README.md` will include five concise pathways:

1. **Understand the platform:** system overview → security master → market data/valuation → tenancy.
2. **Build or integrate:** API, frontend, schema/data, application READMEs, contracts.
3. **Operate data:** onboarding, work queues, data provenance, calendars/cuts, trade/valuation controls.
4. **Evaluate product modules:** commercial modules, UCITS/AIF controls, lifecycle and risk modules.
5. **Plan delivery:** current specs, implementation plans, quality reviews, decision log, research register.

Each section README contains: purpose, authoritative documents, current deferred decisions, related code/data, and historical sources. This avoids one giant index while making the hierarchy self-describing.

## 10. Validation and acceptance criteria

The reorganisation is accepted only if all of the following hold:

- The archive manifest contains every in-scope source file and its pre-migration SHA-256 checksum.
- Every archived copy matches its manifest checksum.
- `docs/README.md` reaches every canonical section within two clicks.
- Every current content file is classified as canonical, record, or archive; no orphaned live architecture document remains unexplained.
- All existing internal Markdown links resolve, or have an explicit compatibility redirect/notice and a recorded replacement.
- Code-adjacent READMEs remain in their current source locations.
- No database, API, frontend, or runtime file changes occur.
- A focused documentation consistency check completes; the full application test suite is not run solely for this documentation migration.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Information loss during consolidation | Archive-before-promotion, SHA-256 manifest, no deletion in first migration. |
| Duplicate documents create ambiguity | Canonical status metadata, source list, and compatibility notices identify authority. |
| Broken Markdown links | Link inventory before changes, compatibility notices, focused link check after changes. |
| Existing workflow expects `docs/superpowers/*` | Retain those folders and index them from `docs/delivery`; do not relocate workflow artefacts. |
| Code docs lose discoverability | Keep colocated READMEs and enumerate them from `docs/README.md`. |
| Over-large rewrite obscures historical decisions | Promotion is topical and source-linked; historic originals remain immutable. |

## 12. Deferred decisions

- Whether to add a static documentation site and search (MkDocs, Docusaurus, or equivalent).
- Whether ADRs use the existing `ui/decisions` numbering or a new project-wide sequence.
- Documentation ownership roles and review cadence once the project has a formal team model.
- Whether, after a verified migration period, compatibility documents should be reduced to short forwarding pages.
- Whether to automate link and metadata validation in CI.

## 13. Implementation boundary

This design authorises only a documentation migration. It does not authorise a code refactor, schema migration, application restart, dataset change, or delivery commit. A detailed implementation plan follows only after this written specification is reviewed and approved.
