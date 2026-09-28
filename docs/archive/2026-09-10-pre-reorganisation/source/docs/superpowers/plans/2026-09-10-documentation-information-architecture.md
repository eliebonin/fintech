# Documentation Information Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a navigable, domain-led project documentation system while preserving every source Markdown document in a checksum-verified archive.

**Architecture:** Preserve the pre-migration Markdown corpus as an immutable archive first. Then create a small set of canonical, source-linked navigation and governance documents. Keep `docs/superpowers/*` and code-adjacent READMEs in their current paths, and use indexes rather than duplicate those workflow artefacts.

**Tech Stack:** Markdown, PowerShell read-only inventory/check commands, repository-relative links, SHA-256 (`Get-FileHash`).

**Spec:** `docs/superpowers/specs/2026-09-10-documentation-information-architecture-design.md`

## Global Constraints

- Documentation-only change: do not modify database, API, frontend, tests, seed data, or runtime configuration.
- Preserve every pre-migration content Markdown file, excluding instruction files named `AGENTS.md` and `CLAUDE.md`.
- Create the archive before creating compatibility notices or changing any existing live documentation.
- Do not delete source Markdown files in this migration.
- Retain `docs/superpowers/specs/` and `docs/superpowers/plans/` as workflow-compatible locations.
- Retain `apps/*/README.md`, `packages/*/README.md`, and `data/mockup/README.md` beside code/data.
- Do not run the full application test suite; use focused documentation checks only.
- Do not create a git commit because the working tree has no established committed baseline.

---

### Task 1: Freeze and verify the Markdown source corpus

**Files:**
- Create: `docs/archive/2026-09-10-pre-reorganisation/README.md`
- Create: `docs/archive/2026-09-10-pre-reorganisation/manifest.md`
- Create: `docs/archive/2026-09-10-pre-reorganisation/source/<original-relative-path>.md` for every in-scope source file

**Interfaces:**
- Consumes: repository Markdown files discovered by `rg --files -g '*.md'`, excluding `AGENTS.md`, `CLAUDE.md`, and the archive destination.
- Produces: an immutable source snapshot and a Markdown manifest with `source path`, `archive path`, `H1`, `line count`, `SHA-256`, `content classification`, and `planned canonical destination`.

- [ ] **Step 1: Produce the pre-migration source list**

Run:

```powershell
$scope = rg --files -g '*.md' |
  Where-Object { $_ -notmatch '(^|[\\/])(AGENTS|CLAUDE)\.md$' } |
  Where-Object { $_ -notmatch '^docs[\\/]archive[\\/]' } |
  Sort-Object
$scope.Count
$scope
```

Expected: a stable ordered list of all source documentation, including `security-master-notes`, `docs`, `ui`, `fintech-moduls`, code/package/data READMEs, and the approved design specification.

- [ ] **Step 2: Copy each source file into the archive without changing source files**

For every file in the list, create the matching path below `docs/archive/2026-09-10-pre-reorganisation/source/` and copy it byte-for-byte. Do not overwrite an archived copy if it already exists; stop and investigate a mismatch instead.

- [ ] **Step 3: Create the archive README and manifest**

The archive README must state the snapshot date, scope exclusions, immutability rule, checksum procedure, and that it is historical evidence rather than canonical guidance. The manifest must map every source file to its archived copy and planned canonical treatment using the mapping rules in the approved design.

- [ ] **Step 4: Verify archive preservation**

Run a PowerShell comparison that checks each manifest source/archive pair by SHA-256 and fails if any count, path, or hash differs.

Expected: every source file has exactly one archive copy with an identical SHA-256 hash.

### Task 2: Create the documentation home, governance layer, and shared indexes

**Files:**
- Create: `docs/README.md`
- Create: `docs/governance/documentation-governance.md`
- Create: `docs/governance/glossary.md`
- Create: `docs/governance/decisions/README.md`
- Create: `docs/architecture/README.md`
- Create: `docs/product/README.md`
- Create: `docs/platform/README.md`
- Create: `docs/delivery/README.md`
- Create: `docs/research/README.md`
- Create: `docs/research/evidence-register.md`

**Interfaces:**
- Consumes: archive manifest and current documents.
- Produces: the project’s canonical entry point, definitions for document status/content types, section navigation, an ADR index, and a research register pointing to existing evidence.

- [ ] **Step 1: Write `docs/README.md` as the entry point**

Include five reading paths exactly as specified: understand the platform; build or integrate; operate data; evaluate product modules; plan delivery. Each path must link to a section README and expose code-adjacent READMEs without relocating them.

- [ ] **Step 2: Write governance documents**

`documentation-governance.md` must define the metadata block, canonical/source-of-truth rules, archive policy, review lifecycle, and link-check expectation. `glossary.md` must seed unambiguous definitions for canonical instrument, financial-reference node, listing, provider mapping, dataset, licence, valuation cut, observation, valuation mark, strategy, tenant overlay, and archive. The ADR index must document the one-decision-per-record convention and link to current UI decisions as historical records.

- [ ] **Step 3: Write section READMEs**

Each section README must identify its purpose, authoritative current pages, historical sources, deferred decisions, and adjacent code/data where relevant. It must avoid copying the source material wholesale.

- [ ] **Step 4: Write the evidence register**

Index external-evidence and research material already held in `security-master-notes/24-external-evidence-and-research.md`, structured-product research/specifications, module research, and dated product research. State that research is non-normative unless cited by an ADR or canonical page.

- [ ] **Step 5: Verify navigation depth**

Manually trace each of the five `docs/README.md` reading paths. Every section must be reachable in at most two Markdown links from `docs/README.md`.

### Task 3: Promote canonical architecture, platform, product, and delivery navigation

**Files:**
- Create: `docs/architecture/system-overview.md`
- Create: `docs/architecture/security-master/README.md`
- Create: `docs/architecture/market-data-and-valuation/README.md`
- Create: `docs/architecture/trading-and-operations/README.md`
- Create: `docs/architecture/tenancy-and-entitlements/README.md`
- Create: `docs/architecture/integrations-and-data-rights/README.md`
- Create: `docs/platform/api/README.md`
- Create: `docs/platform/frontend/README.md`
- Create: `docs/platform/data-and-schema/README.md`
- Create: `docs/product/onboarding/README.md`
- Create: `docs/product/fintech-modules/README.md`
- Create: `docs/delivery/quality-reviews/README.md`
- Create: `docs/delivery/implementation-plans/README.md`
- Create: `docs/delivery/specifications/README.md`

**Interfaces:**
- Consumes: the historical archive, domain notebooks, UI documentation, dated architecture records, and `docs/superpowers/*`.
- Produces: maintained entry pages linking to the detailed current or historical source documents with status and provenance.

- [ ] **Step 1: Write the system overview**

State the current platform boundary: canonical reference-data plane, tenant overlays, market-data provenance/entitlements, valuation/Soft-NAV snapshots, trade storage, API/BFF/frontend, and the separation of reference data from tenant-held positions/trades. Cite the existing source documents and the 2026-09-10 global review; do not introduce new architectural choices.

- [ ] **Step 2: Create architecture-domain indexes**

For each architecture subdomain, list the specific existing notebook documents that provide detailed coverage, identify its current canonical conclusions, and list deferred decisions. Use links, status labels, and provenance—not copied paragraphs.

- [ ] **Step 3: Create platform and product indexes**

The platform indexes must link API contracts/application README, frontend decisions/screen specifications/workflows, database schema/model/seed documentation, and current cross-layer reviews. The product indexes must link per-instrument onboarding records and the commercial fintech module documents.

- [ ] **Step 4: Create delivery indexes**

The delivery indexes must classify and link existing dated quality reviews, `docs/superpowers/plans`, and `docs/superpowers/specs`. They must explain that these are records of assessment or intended work, not automatically current architecture.

- [ ] **Step 5: Confirm no false implementation claim**

Scan the new index files for language that labels planned or reviewed functionality as implemented. Correct any ambiguous status statement before proceeding.

### Task 4: Add compatibility pointers and migration traceability

**Files:**
- Modify: `security-master-notes/README.md`
- Modify: `ui/README.md`
- Modify: `fintech-moduls/README.md`
- Modify: `docs/architecture/README.md` if needed to link legacy records
- Modify: `docs/archive/2026-09-10-pre-reorganisation/manifest.md`

**Interfaces:**
- Consumes: canonical indexes produced in Tasks 2–3.
- Produces: clear notices in legacy landing pages that distinguish the historical notebook from current canonical documentation.

- [ ] **Step 1: Add non-destructive notices to legacy landing pages**

At the top of each legacy landing page, add a short notice linking to `docs/README.md`, its closest canonical section, and the immutable archive. Retain the existing notebook/module/UI index below the notice.

- [ ] **Step 2: Complete manifest canonical mappings**

For every archived source document, set `planned canonical destination` to one of: a canonical maintained page, an indexed record, a colocated code/data README, or archive-only historical evidence. No row may be blank.

- [ ] **Step 3: Preserve old paths**

Do not rename or delete `security-master-notes`, `ui`, `fintech-moduls`, or `docs/superpowers`. Existing relative links must remain valid.

### Task 5: Validate the migrated documentation system

**Files:**
- Modify: `docs/archive/2026-09-10-pre-reorganisation/manifest.md` only if validation identifies a missing mapping.

**Interfaces:**
- Consumes: archive manifest, all Markdown files, and canonical navigation files.
- Produces: verified preservation, link integrity evidence, and a concise implementation summary.

- [ ] **Step 1: Re-run checksum verification**

Compare every source entry in the manifest with its archive copy using `Get-FileHash -Algorithm SHA256`. Expected: same file count and identical hashes for every pair.

- [ ] **Step 2: Check Markdown link targets**

Parse local Markdown links in project documentation. For each non-HTTP target, resolve the path relative to the source file and fail/report if the target does not exist. Ignore fragment-only anchors after confirming the referenced file exists.

- [ ] **Step 3: Check canonical metadata and manifest completeness**

Confirm all new canonical pages declare status, content type, owner, and last-reviewed date. Confirm the archive manifest contains a nonempty canonical treatment for every source document.

- [ ] **Step 4: Check documentation scope**

Review changed paths. Expected: only Markdown documentation and archive snapshot files changed; no database/API/frontend/runtime files changed.

- [ ] **Step 5: Report evidence**

Report the archive file count, checksum result, link-check result, canonical-page count, compatibility locations retained, and any deliberate archive-only records. Do not claim the full application test suite was run.
