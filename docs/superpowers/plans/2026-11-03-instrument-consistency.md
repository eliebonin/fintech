# Instrument consistency implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. The user authorized implementation in the order 3 → 1 → 2; do not request another plan approval.

**Goal:** Remove seed-specific creation choices, close valuation-source reassessment gaps, then align bond monetary previews with maintained accrued stocks.

**Architecture:** Keep reference lookup below HTTP and all writes behind existing authority, validation and audit. Add frozen source-dependency evidence to new valuation batches and compare current source state without rewriting results. Consume exact-date current maintained accrued balances in monetary previews without guessing missing values.

**Tech stack:** FastAPI/SQLAlchemy/PostgreSQL, Next.js/React/TypeScript, pytest/Vitest.

**Spec:** User-approved priority list and execution order in this conversation; this document records the bounded implementation decisions.

## Constraints

- Work in the existing clean feature checkout `codex/pnl-ops-review`, as previously selected by the user. Sequential implementation; no subagents.
- Preserve real operator identity, tenant/strategy scope, current rights, immutable booking/result evidence, Decimal arithmetic and explicit missing inputs.
- No operating trades, grants, prices, balances or published valuation values are changed by verification. Use owned disposable databases.
- No broad Python regression run. Start with failing focused regressions and broaden only for the changed dependency surfaces.
- No new pricing model, settlement/accounting engine or expansion into deferred derivative MTM.

## Task 1 — Creation choices and truthful scope

Files: `security_master_schema/creation_options.py`, `apps/reference_api/reference_creation_routes.py`, existing router registration; equity page and its small model/BFF helpers/tests; instrument creation picker.

- [x] Write failing tests for tenant-private source isolation, effective date/status/policy precedence, no seeded issuer/source defaults and payload selection.
- [x] Provide authorized, date-scoped automation source/policy/namespace options. Preserve automated submission validation and manual creation when none are configured.
- [x] Reuse organisation search for an explicit issuer choice, retaining the selection across searches; unresolved remains explicit.
- [x] Replace seed policy/source constants and stale futures copy; inspect other creation pages for equivalent seed assumptions.
- [x] Run focused backend/frontend/type checks and update capability/docs.

## Task 2 — Non-ledger source reassessment

Files: new `valuation/source_dependencies.py` and focused tests; `valuation/service.py`, `valuation/ledger_impacts.py`, `valuation/storage.py`; existing source-health UI/contracts only as necessary.

- [x] Trace exact frozen selections and relevant policy/calendar/action dependencies; write failing regressions for changed source, unrelated changes, status and publication.
- [x] Retain versioned dependency evidence for new batches using existing summary storage; scope current-state comparisons to relevant subjects, economic/pricing dates and actual selected policies.
- [x] Detect revised/new relevant market data, selected-policy/rule changes, applicable calendar and corporate-action changes in source health/history and publication guards.
- [x] Preserve frozen published financial amounts and require explicit replacement calculations; never automatically publish or silently choose a different policy version.
- [x] Verify batch/detail parity, current access, missing/legacy proof and amendments; document exact detection boundaries.

## Task 3 — Bond monetary preview stocks

Files: `valuation/measure_inputs.py`, focused bond stock adapter as needed, existing maintained history and measure tests.

- [x] Write failing tests for CLEAN plus current maintained stock, stale/missing history, source currency, eligible exposure and multiple compatible/incompatible position buckets.
- [x] Keep source DIRTY precedence; otherwise use the exact-date maintained closing balance with current-source proof and compatible ownership, currencies and nominal coverage.
- [x] Never reconstruct stocks in the preview, duplicate an instrument-level balance across listings, assume zero or use daily earned interest as the stock.
- [x] Verify local/reporting amounts and unchanged daily-P&L behavior; update methodology, register/map and findings.

## Final verification

- [x] Focused cross-layer regressions, generated API parity and TypeScript.
- [x] Read-only browser acceptance where available; distinguish tests from live activation and financial acceptance.
- [x] Update KNOWLEDGE/FIX and delivery evidence; report any remaining gaps candidly.

## Execution ledger

- 3 November 2026: clean starting commit `570b851`; existing feature checkout retained to preserve the running application context. Earlier preference authorizes work in place.

- Creation: ten onboarding/catalogue checks and five UI payload/BFF checks passed; no live source configuration was changed.
- Reassessment: shared SQL fingerprints now cover market candidates/vintages/corrections, selected policy/rules/cuts/priorities, pinned calendars/assignments/venues and visible quantity-changing action/review chains. A nested JSON scope correlation defect was reproduced with sequential batches and fixed. Fourteen initial and nineteen expanded focused checks passed; per-pricing-date window follow-up passed in the final regression.
- Bond measures: ten focused stock/monetary checks passed. Exact-date maintained stocks replace direct daily-payload balance consumption; DIRTY precedence and explicitly frozen zero-coupon semantics remain. Public proof retains scoped history/build IDs and a source hash, not other bonds' source catalogues.

- Final verification: 191 focused cross-layer Python regressions and the 1,151-test frontend regression passed, followed by 17 targeted client/model/BFF checks for the live browser findings. Frontend and generated-contract TypeScript, API schema parity, contract tests, source syntax and secret scan passed. The full Python suite was intentionally not run.
- Live acceptance found a stale Next.js export cache and, after restart, a missing exact permission mapping for the new read endpoint. Direct client and native HTTP regressions now cover these boundaries; the mapping uses the existing REFERENCE_PROPOSE action. No permission is granted by this change. Issuer labels also omit absent legal names.
- Scope of acceptance: read-only local creation workflow and disposable financial/source-health tests. No operating valuation was calculated or published, and no source configuration was seeded to manufacture a live automation example.

- Final live boundary follow-up: 24 disposable HTTP/access checks passed. API restarted after verifying zero RUNNING attempts; health returned 200. Live options returned 200, manual fallback was truthful, and issuer labels/search retention were verified.
