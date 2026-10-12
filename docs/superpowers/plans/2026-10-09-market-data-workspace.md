# Market Data Workspace Implementation Plan

> Implement sequentially in this session using executing-plans; no subagents, per the user's standing instruction.

**Goal:** Replace the observation-card landing page with an operational overview, compact explorer and explicit, read-only coverage checks.
**Architecture:** Keep existing source/policy/calendar and history endpoints. Add a bounded catalogue projection with one latest accepted/display-permitted observation per series. Coverage reuses calendar-aware resolution-preview for 1–50 explicitly required references, retaining missing subjects in the denominator.
**Tech Stack:** FastAPI, SQLAlchemy/PostgreSQL, Next 16.3.4, React, existing MUI/native console styles.
**Spec:** User-approved recommendation in this conversation, 9 October 2026.

## Constraints
- Preserve concurrent edits and generated next-env bytes. No operating financial/configuration writes, source downloads, migrations, commits or subagents.
- No synthetic readiness metrics. Counts concern explicit requirements; no claim of automatic complete strategy-position or universe coverage.
- Current tenant/module/display rights apply to metadata and values. Coverage does not save snapshots/results.
- Existing history bookmarks remain usable. History loads only after selecting a reference.
- No ingestion activity counts without an established tenant-safe operational API; show that monitoring is not available rather than inventing success.

## Review focus
- Missing/no-series requirements remain visible; unseen resolver items become unknown.
- Restricted, private, superseded and future-dated values never leak through summaries.
- Catalogue query count stays independent of page size; no history arrays or per-series counts.
- Editing coverage context invalidates previous checks; stale requests cannot replace newer context.
- Module-denied and failed APIs show bounded recovery without falling back across tenants.

## Tasks
1. [x] Add tests for compact catalogue pagination, no-history payload, visibility, current accepted values and fixed query count; observe failure. Implement catalogue contracts/query/API and generate shared contracts. Run isolated integration regressions.
2. [x] Add page/model tests for an overview that never fetches observations, explorer search and legacy history bookmarks; observe failure. Implement navigation, overview and compact explorer; preserve detail history.
3. [x] Add coverage summary tests for missing/unknown inputs and immutable request context; observe failure. Implement explicit reference scope, policy/date/cutoff selectors, exception table and on-demand evidence via the existing read-only preview.
4. [x] Run focused and appropriate frontend regression tests/typecheck, isolated build, live read-only checks, final source review and delivery documentation. Preserve the current dev server if running.
