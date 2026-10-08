# Booking readiness alpha

Status: implemented and verified alpha slice (2026-10-05). Operating app not restarted; changes not pushed.

## Approved design and scope

The tenant booking searches default to ready results, with a Show unavailable filter, readable status/reason and inspection links. Empty results distinguish no matches from loaded matches that are not bookable. Search progress/counts are accessible status messages. Selection refreshes readiness; only the existing locked booking writer authorizes a new trade. This does not add products, valuation, historical version resolution or lifecycle automation.

Cash needs an additive read-only search/detail API that reuses the cash writer validator without row locks. Existing specialist endpoints already return eligibility and refusal reasons; unknown categories remain Not ready, never inferred from message wording. Pagination continues over all raw matches even when the loaded results are filtered. Counts are explicitly loaded-result counts, not a claim to have assessed the whole catalogue.

## Research (accessed 2026-10-05)

- [GOV.UK Design System: disabled buttons](https://design-system.service.gov.uk/components/button/#disabled-buttons): disabled controls can confuse users. Application: unavailable rows retain readable reasons and an active inspection link instead of a dead select button.
- [W3C WCAG 2.2: status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html): search progress, counts and empty messages should be programmatically identifiable without moving focus. Application: a concise role=status summary, not a live region around the whole results list.
- [IBM Carbon: data table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines): search/filter controls belong near the data; additional detail can be disclosed progressively. Application: one filter near results, compact identities/statuses and drill-down links. Default-ready filtering is our task-specific choice, not a universal mandate from Carbon.

## Execution record

Sequential work in the user-selected feature checkout; earlier integrity changes preserved. No subagent review, operating data edits, operating-application restart or push included. The code-review skill was applied as an author review because the user explicitly requested sequential work without subagents; this is not independent sign-off.

- Backend tests first: readiness versus draft, selected date, inactive listing, foreign-parent non-disclosure, pagination and no writer locks/no trade insertion.
- Frontend RED: the cash search lacks the Show unavailable readiness control (20 existing tests passed, one new assertion failed).
- Initial backend test attempt had two invalid helper arguments; corrected to the existing listing_status fixture parameter before implementation.

## Delivered implementation

- Shared ready-first result view across listed cash, deliverable FX forwards, listed options, structured securities, futures, bonds and swaps. Show unavailable reveals backend reasons and inspection links; unavailable rows never offer selection.
- Typed readiness categories for cash and the extended product API: Ready, Missing configuration, Inactive, Creation-only and Not ready. Existing FX/option eligibility is shown as Ready/Not ready; their free-text reasons are not parsed into guessed categories. Unknown status codes fail closed in the shared view.
- Physical/crypto futures remain creation-only. Presentation metadata is added after the existing execution fingerprint is computed; no economics, quantities, quotes or replay facts are changed.
- Additive read-only cash endpoints: `GET /v1/trades/cash-listings` and `GET /v1/trades/cash-listings/{listing_id}`. They use current membership/booking authorization, active tenant-visible scope on both listing and parent, selected UTC execution date (defaulting to the current UTC day, not server-local day) and the same cash eligibility validator as the writer. Reads disable writer row locks; writes still default to locked validation.
- Cash search supports names, codes, symbols, identifiers and venues. Visible inactive references can be explained; foreign/revoked references are not inspectable. Cash selection revalidates before opening execution, including when the service fails or readiness has changed.
- Raw API offset/limit advances pagination independently of the number of visible/ready rows, including concurrent scope revocation. Loaded counts do not pretend to count every eligible reference in the catalogue. Query/date edits invalidate cash results and late requests; changing listing resets the search.
- Cash deep links explain non-readiness without opening execution. The readiness API returns 404 for missing/invisible listings; the UI renders the not-found page (streamed Next.js pages may still have HTTP 200). The venue MIC and display name are preserved in the selected ticket.
- BFFs use trusted session identity and no-store reads. API contracts regenerated. The shared status summary uses `role=status`, with keyboard-focus treatment for action links/buttons.

## Verification evidence

- Focused cash readiness, writer integrity, lock order and futures specification regression run: **38 passed**. This includes the existing physical/crypto booking refusal with the new Creation-only status.
- First combined ticket/BFF frontend run found **14 shallow-harness failures**, not booking failures: the product harness did not descend into the new shared result component. Updated it to exercise the real controlled view while preserving execution/retry assertions. Rerun: **143 passed**.
- Pagination RED: the shared view continued offering Load more after a raw page had been exhausted but scope-revoked rows were omitted. Added explicit raw-cursor completion; regression is green.
- Browser RED: the cash readiness response omitted the venue MIC. A backend assertion reproduced `None != XLON`; corrected the read projection. Final isolated cash-readiness run: **6 passed**, including lock/write assertions and venue identity.
- Added five cash state regressions: stale query response, changed readiness on selection, selection-service failure, raw pagination after omitted rows, readiness-date invalidation. Combined shared-view/state run: **12 passed**.
- Final review RED: malformed legacy family metadata re-raised a Pydantic error while classifying an already-refused future (**1 failed, 1 passed**). The classifier now safely returns Not ready for invalid family configuration; foreign families remain opaque. A UTC-boundary RED also reproduced the server-local default date rather than the writer's UTC day; both cash endpoints now use a UTC clock. Final targeted cash/product-readiness/futures run: **12 passed in 13.71s, exit 0**; subsequent OpenAPI drift check exit 0.
- Final full frontend: **453 passed in 101 files**, `--maxWorkers=2`; frontend typecheck exit 0. Contract package: **3 passed**, typecheck exit 0. OpenAPI exporter `--check`: exit 0.
- Full Python regression run: **784 passed, 480 warnings in 1634.15s (27m14s), exit 0**, using `scripts/run_isolated_python_tests.py -q --tb=short`. There was only one full-suite process; the runner removed its disposable database on exit. The run started before the venue-MIC display correction, defensive legacy-metadata classification and UTC-default correction. The final **12-test targeted run** covers those late changes explicitly, including the three additional late tests; the full run is not final-code coverage of those added assertions. Warnings concern existing SQLAlchemy tuple deprecations, Pydantic field-alias metadata and Starlette status-name deprecations; this is not a warning-free acceptance claim.
- Final frontend typecheck after restoring preview-generated Next.js paths: exit 0. `git diff --check`: exit 0. Author review completed against the approved scope; no independent subagent sign-off.

### Isolated browser acceptance

Preview only: UI port 3004, API port 8004, disposable databases named `fortem_readiness_browser_<random UUID>`. Synthetic seed data and test-only draft listings; no trade submission, approval or operating-data edits.

Verified through the real browser:

1. Select the synthetic tenant, open booking through the menu, search cash.
2. Ready-only default and loaded counts; Show unavailable exposes draft refusal and an inspection link, without a select action.
3. All-unavailable versus no-match messages; query edits clear old results.
4. Ready selection refreshes through the API and opens the locked execution ticket; corrected MIC shows XLON, not Venue unavailable. Change listing resets search state.
5. Twenty-five unavailable first-page matches still offer Load more. Loading page two reveals the ready listing; final counts are one ready and 26 unavailable in 27 loaded matches, with no further pagination action.
6. Futures show missing approved conventions as Missing configuration with reasons/inspection links. Physical/crypto Creation-only status is backend/unit-tested, not a browser-created approval in this acceptance run.
7. Draft cash deep link refuses execution safely; an absent listing deep link renders the proper 404 page.

Both isolated preview databases were removed by their fixture runner after shutdown. The temporary API/UI processes were stopped; no operating app restart was performed. Next.js-generated development path changes in `next-env.d.ts` were restored to the pre-preview state.

## Boundaries and remaining separate work

- Readiness is advisory and instrument-specific, not credit approval or a promise that every strategy/execution can be booked. The existing writer remains authoritative after execution/date/configuration changes.
- Show unavailable only covers references returned by the existing tenant-visible product searches. It is not a universal catalogue/draft-request queue: specialist searches retain their existing active-node/product/route restrictions.
- Cash exposes a selected UTC execution date. Specialist searches retain their existing date behavior; this is not historical version resolution across all products.
- No schema migration or stored readiness flag: readiness is derived from live approved reference facts. No new valuation/P&L, product support, lifecycle, amendment/correction or automatic cash posting.
- Verification is author review plus regression tests and bounded browser acceptance, not a full accessibility audit or production-load certification.
