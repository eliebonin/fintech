# Trade-side acceptance checklist and evidence

**Date:** 2026-10-06. **Status:** Completed for the scoped trade-side alpha acceptance. Sequential execution on isolated synthetic data only; not production certification or user acceptance.

## Scope and researched approach

Finish instrument creation/approval, booking, history, historical booking and record cancellation/replacement. Settlement, accounting, valuations/P&L and contractual delivery/expiry/redemption are deferred. Existing FX-delivery work is preserved but not signed off here. No operating-data writes, deployment or GitHub push.

Primary sources opened and reviewed on 2026-10-06 (living guidance; publication dates not displayed):

- [Playwright best practices](https://playwright.dev/docs/best-practices): verify user-visible outcomes using role/label locators and waiting assertions, with controlled isolated data. Applied here by inspecting saved detail/history rather than counting successful requests as browser passes. Independent workflows use uniquely named synthetic references; fixture-provisioned references are not browser-created evidence. Use only the supported browser-control tool.
- [OWASP authorization regression testing](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Regression_Testing_Cheat_Sheet.html): explicit actor/resource/action coverage, API-enforced authorization and tenant boundaries. Applied to TENANT_ADMIN + SECURITY_MASTER for creation/approval, TENANT_ADMIN + TRADING for booking/correction and opaque foreign-record access. Automated regression cases supplement browser checks.

These are engineering recommendations, not financial/accounting standards or production certification. The product-specific checklist below is our application of that guidance.

## Acceptance matrix

| Workflow | Required observable result | Current evidence / remaining work |
| --- | --- | --- |
| Cash canonical/listing | Browser creation, request, approval, contextual listing creation/approval, readiness, booking/detail/history | PASS — fresh browser reference cycle and saved detail/history; cash correction cycle also recorded |
| FX forward | Browser terms creation/approval, dated search, booking, currency/maturity snapshot | PASS — fresh browser reference/booking cycle and full replacement/cancellation |
| Option/listing | Browser canonical/listing creation/approval, readiness, intent/premium/factors saved | PASS — fresh browser canonical/listing/booking cycle and full replacement/cancellation |
| Structured security listed + OTC | Browser creation/approval and each supported execution route; nominal/quote convention saved | PASS — fresh browser autocall parent, conventions/listing, both routes and full OTC correction cycle |
| Future family/expiry/listing | Browser family creation, canonical expiry/approval, listing/approval, correct symbol/dates/monetary multiplier, booking | PASS — fresh browser family→expiry→listing→booking; full correction cycle |
| Bond listed + OTC | Browser creation/approval, both routes, CLEAN and DIRTY accrual without double counting | PASS — missing creation fields fixed; fresh complete bond, convention/listing, listed CLEAN + OTC DIRTY; full correction cycle |
| Generic swap | Browser terms creation/approval, funding/reference readiness, permitted partial/full booking, saved convention | PASS — fresh browser funded terms/approval, partial-notional booking/detail; full correction cycle; full-contract notional rules also automated |
| Six noncash correction cycles | Required reason; replacement linked; original SUPERSEDED with facts unchanged; replacement cancellation preserves facts/history and removes invalid actions | PASS — all six browser cycles with UUIDs below, immutable originals and append-only lineage |
| Historical booking | Date changes before search; valid historical booking; stored date/history filtering; actionable future/out-of-terms rejection | PASS — browser valid dated future, rejection feedback and default/custom history filters; broader product date rules automated |
| Failure/retry | Failed replacement leaves original active; stale conflict usable; uncertain retry preserves frozen bytes/key; stale tenant cannot submit | PASS — browser stale-sequence/stale-tenant rejection and guarded full-navigation exit; history contains no orphan replacement or rejected execution. Rollback/uncertain network/key replay automated, not claimed as browser faults |
| Authority | Authorized active tenant succeeds; unqualified role/module rejected; foreign detail opaque and history contains no foreign records | PASS — legacy BFF demo-tenant fallback fixed; browser OPERATIONS creation403, booking redirects, foreign detail opaque, all-history0. API role/module matrix and46 BFF/page boundary regressions passed |

A rendered gate is not a completed replacement. Record request/reference/trade/replacement UUIDs and evidence type. Automation-infrastructure failure is not an application defect unless independently reproduced. Nondeterministic races/network loss may remain automated evidence rather than requiring an oversized browser fault harness.

## Execution order

1. Re-run focused correction, historical, authority and integrity tests on a fresh disposable database; confirm actual exit status.
2. Execute browser reference and correction cycles. Reproduce defects with lightweight failing tests, fix them, run relevant broader verification.
3. Complete historical and deterministic failure/authority checks.
4. Update this dated report with passed/pending/blocked coverage, limitations and test totals. Do not call trade-side sign-off complete from API/component suites alone.

## Evidence ledger

- Previous browser trade UUIDs and cash correction/cancellation evidence: [execution record](booking-signoff-and-lifecycle-execution.md). These are previous observations, not fresh retests.
- Initial browser and documentation attempts were blocked by automatic approval-review model capacity; neither action executed. This was infrastructure unavailability, not an unsafe-action determination. User requested retry; browser documentation restoration then succeeded.
- Read-only TypeScript check passed (exit 0); pure historical-date checks: 3 passed, 7 database cases deselected (exit 0). These do not establish whole-suite or browser acceptance.
- Subsequent verification and fixes are recorded chronologically below; the matrix above reflects the current result, not the initial stage.

### Fresh verification and correction cycles

- Focused isolated Python suite: **126 passed, 11 warnings**, 37.85s, exit 0. Covers corrections, historical rules, cash integrity, approval integrity, reference authority and proposal retry integrity. Warnings include existing SQLAlchemy/Pydantic deprecations and sandbox-denied pytest-cache writes; database was disposable.
- Correction-gate hydration regression failed first: pre-hydration submit/input were enabled. Early native GET submit lost the correction query; reason input could also be reset by hydration. Input and continuation now remain disabled until client handlers mount. Browser immediate-load retest preserved the reason and replacement context. Gate/page checks: **16 passed**, TypeScript exit 0.
- Initial full frontend run: **500 passed, 1 timed out**, 113 files. `trade-history-page.test.tsx > displays correction lineage, reason and separate effective/recorded dates` exceeded 5s during cold import. Its isolated rerun passed 18 tests. Full rerun with two workers: **501 passed, 113 files**, 22.66s, exit 0. No assertions were weakened or test timeouts raised.
- All six noncash replacement/cancellation cycles completed through the browser. Original records retain quantities/quotes/snapshots and become SUPERSEDED; replacements have BOOKED + CORRECTED lineage, then CANCELLED with facts retained and invalid correction actions absent. These are record-error corrections, not contract termination.

| Product | Original trade | Replacement trade (subsequently cancelled) | Reviewed replacement economics |
| --- | --- | --- | --- |
| FX | `e0567578-6ab4-419c-ba68-38c99b3bc3b5` | `93266c56-9942-4b40-9afb-7b2fc7d15a99` | Receive EUR 900k / pay USD 990k, rate 1.1 |
| Option | `0928f870-34f3-421a-a26e-b2e9517ac00e` | `8bb47eb3-c333-4d2c-868c-7f8c41cb49c4` | BUY/OPEN 12, premium 2.5, multiplier 100, GBP 3,000 |
| Future | `69a851f3-2f81-4902-b160-78a160360fd7` | `5ffa7ed2-f31d-4634-a715-cb258252b1aa` | 3 contracts at 5,000.25 × USD 5 = USD 75,003.75 reference value |
| Structured OTC | `c5e56c7a-847a-4e74-9b71-1c19c2f57530` | `ea35ca97-cbd2-4fca-8e24-61744133af43` | GBP 110k nominal, 98.5 / 100, GBP 108,350 |
| Bond OTC | `ab3f4e3a-ac65-47c5-9a15-2779c11d8a12` | `5084ab4d-5ca4-483d-8c23-16572bec956c` | GBP 110k, DIRTY 99.75 = 109,725; separate accrual 1,375, not added again. Original CLEAN 98.5 + 1,250 retained |
| Swap | `f6aa54fe-b1b2-419f-bb52-5172a915da92` | `f6bd74c8-16a7-4049-aa52-e6a8ea6aa0dc` | GBP 500k nominal at -1.5 / 100 = -7,500 reference value; no doubled leverage or cash entry |

### Historical booking and final frontend regression

- Shared futures/bond/structured/swap ticket lacked a search-date control before reference selection. Four lightweight regression cases failed first. Added an explicit UTC search date; changing it invalidates old results and outstanding responses. The execution timestamp remains explicitly entered in the ticket. Focused historical-search/state checks: **21 passed**, exit 0.
- Browser future search on 2026-09-15 selected the approved dated reference. A 2099 execution was rejected locally; execution on 2026-08-01 was rejected by the API as outside the approved definition, returning the editable ticket with values retained. Valid execution on 2026-09-15 saved as `38918e48-b925-46f6-a5ea-042c0d35b387` with separate effective and recorded audit dates.
- Default 14-day history (2026-09-23 through 2026-10-06) excludes that trade. Exact 2026-09-15 filters with `FUTfeb864` show one matching BOOKED record and its original execution time.
- Full frontend regression after both fixes: **505 passed, 113 files**, 22.99s, exit 0, using two workers. TypeScript also exit 0.

### Fresh cash reference cycle and conflict recovery

- Browser-created equity request `01a1116c-fda6-7a43-9ccb-6806dd0c0b3d`, approved canonical `01a1116d-caf0-7f7d-9d41-0161691edba6`. Contextual Add listing preserved that parent; listing request `01a1116e-b6de-7f4c-b69f-b3eb8b7c4170` appeared in Operations and was approved as `01a1116f-0c84-7d96-94d5-c6faf2974b03` / `ACAS261006` / XLON / GBP.
- Booking search showed Ready to book. Browser execution saved `911e3fa4-645e-4d63-bee0-436f972dc463`, 10 shares at GBP 12.5, expected settlement 2026-10-08. Detail displayed saved identity and metadata.
- Two-tab concurrency: one tab froze a replacement, the second cancelled the original. Stale replacement was rejected without resubmission; cancelled original retained quantity 10 and original execution. This exposed a cash-specific UI trap: blocked state prevented navigation without offering recovery. Added history inspection in another tab and a confirmation-gated exit to history; no replay or automatic second ticket. Regression failed first; **29 focused cash cases passed**, exit 0. Recovery retest was pending at this stage; the final retest below passed.

### Fresh FX reference cycle

- Browser FX request `01a11175-dd2f-7a06-bf3a-53102ba2c5f1` reviewed and approved as canonical `01a11176-c185-779e-a948-f0f77e2c6055`. EUR/USD deliverable, USD_PER_EUR 1.1, maturity 2027-03-15, no distinct settlement override.
- Ready to book after approval. Browser trade `8c8c543e-6ef6-4438-a40f-afa087e1b450` saved BUY EUR 100,000 / USD 110,000 with Bank A Demo counterparty; detail retained the March date and immutable obligation snapshot. No delivery evidence was entered.
- Native browser date-entry automation initially failed to complete a controlled MUI date input. UK-format segmented keyboard input successfully set the date; this is automation evidence, not a reproduced application defect.
- Full frontend after recovery fix: **506 passed, 113 files**, 22.29s, exit 0; TypeScript exit 0.

### Fresh option and futures references

- Option request `01a11179-a4ac-7042-ad09-8ee27ac7b3f2` appeared in instrument-only Requests and approved to `01a1117a-4d91-7795-a1ad-83c442495a72`, underlying the new acceptance equity. CALL/EUROPEAN/CASH, strike GBP 10, expiry 2027-09-17, premium multiplier 100 and deliverable units 100 remained distinct.
- Contextual option listing request `01a1117b-0e8e-77e6-978c-8b1b4f81ab50` / `AOPT261006` was separately approved. Ready-to-book selection and trade `d05341c0-63a1-4379-88c6-9b67558bd875` saved BUY/OPEN two contracts at 2.5, GBP 500 premium and expected payment date 2026-10-08.
- Futures family request `01a1117d-7815-714f-af73-6790d0b7ddad` approved non-tradable family reference `01a1117e-02f2-74c1-a86e-cbecf45aa8a5` (family row `01a1117e-02fd-73cb-8608-79f3c2d142aa`). Quarterly H/M/U/Z months, one-digit year display, USD 50 per index point, tick 0.25; no expiry/listing silently created.
- March 2027 expiry request `01a1117e-c1db-76eb-9ad0-9ea843490251` approved canonical `01a1117f-59e6-7ed5-aa0f-aa7aa2a2e1b8`. Review preview AXH7, canonical month 2027-03-01, exact final trading/settlement 2027-03-19. Detail shows USD 50/point and USD 12.5 tick value.
- Contextual futures listing request `01a11180-0685-76f8-b9fc-fa54bd4e1142` / AXH7 approved with unit multiplier 1 and quote factor 1. Search showed Ready to book. Saved execution is recorded below.

### Futures execution and bond reference

- Futures trade `ab320374-1efd-4aca-9ce7-dae74e6eb87c` saved through the browser: BUY/OPEN 2 contracts × 5,000.25 × USD 50 = USD 500,025 reference value. Detail retained the contract multiplier, separate listing conversion of 1, exact expiry and source. No payment or margin entry.
- Bond request `01a11182-905a-79ba-b067-c404f55873e7` approved canonical `01a11183-16a0-740f-b733-8fe6b85cd1b5`; fixed 3.25%, semiannual, ACT_ACT_ICMA, GBP, issue 2026-01-01/maturity 2030-01-01.
- Explicit separate convention request `01a11184-235e-70e0-8c0a-099b6d9beeb9` approved: unadjusted NOMINAL, PCT_OF_PAR / 100, minimum/increment 1,000, manual signed accrued interest, OTC allowed. Definition approval alone did not manufacture booking conventions.
- Browser session reset removed existing agent tabs and tenant cookie. A fresh tab on the same browser restored the demo tenant through Select tenant, then resumed the persisted request; no reference data was lost or recreated.

At this stage derivative reference creation and recovery/authority remained pending; later sections record their subsequent results.

### Bond creation gap found and corrected

- The first bond and listing ABND261006 were approved, but readiness correctly rejected booking: sourced positive par and redemption at par were absent. The creation form had no controls for these existing API terms. Definition/convention approval must not be confused with readiness.
- Added optional Par amount and Redemption per 100 par inputs, exact decimal-string payload fields, positive native validation and explicit no-inference help. Sparse provider-enrichable submissions remain supported; no defaults or readiness relaxation.
- Regression first failed for missing fields/payload, then all five bond-creation tests passed. Fresh browser request `01a1118c-9fd4-7b56-a460-5d3a640c03d8` visibly retained par 1000 and redemption 100 in Operations and approved canonical `01a1118d-3cd7-72ab-b076-f067455e093b`. The incomplete first instrument is retained as negative-readiness evidence, not mislabelled a successful booking cycle.
- Complete-bond convention `01a1118d-b807-74d8-9658-bb4aa89bfa09` and contextual GBP/100 listing ABNC261006 (`01a1118e-d3b5-7f0f-bfc9-367e34a31681` request) approved separately. Both LISTED and OTC searches show Ready to book.
- Listed CLEAN trade `9f7f7b24-315d-45e4-a45d-208aa09e45eb`: nominal 100,000 × 98.5 / 100 + signed accrual 1,250 = GBP 99,750, immutable detail confirmed. OTC DIRTY trade `96ecc940-6d0d-48d8-9949-0a907f99f26c`: nominal 100,000 × 99.75 / 100 = GBP 99,750; separately recorded accrual 1,250 is not added again. Bank A explicitly selected from governed search; expected settlement 2026-10-08, no payment recorded.
- After the additional fix: full frontend **508 passed, 114 files**, 22.96s; TypeScript exit 0.

### Fresh structured parent creation

- Browser-generated autocall request `01a11192-34b6-71aa-83fc-8067ce385328` approved parent `01a11192-abbd-79cc-bf39-4b0684497964`, GBP issue nominal 1,000,000, SINGLE FTSE reference with manual initial fixing 8,000 on 2026-10-06, flat 100% annual autocall/coupon barriers, 6.5% period coupon, 65% KIP, maturity 2028-10-06.
- Review showed two observations, three payoff components, two parent actions. Approval evidence materialised three fresh component instruments, versioned schedule/conditions/actions and fixing provenance. Components are contractual composition, not separate trade bookings. No action execution or pricing performed.
- Booking convention request `01a11193-ba91-756a-a1e2-a6b4a9f77110` and contextual listing request `01a11194-f10a-7746-8db3-47858ec43641` / ASTR261006 approved separately. Both routes Ready to book. Listed trade `a362073b-81af-483a-b3d3-49bc80aff933` and OTC trade `5ef547e6-a0b2-4670-9368-5c5a2e197823` saved and detail verified: GBP nominal100,000 at98.5/100 =98,500, expected settlement Oct8, one parent trade each. OTC required governed Bank A counterparty even though a listing exists.
- Between turns, browser/runtime reset and both isolated application listeners stopped. PostgreSQL retained all evidence. Restarted only UI3007/API8007 against the same explicitly named synthetic database and restored tenant through UI; no operating app/data change or duplicate reference creation.

### Fresh generic swap creation

- Browser request `01a1119b-077e-72ea-aeb9-e7d914000527` approved canonical `01a1119b-9be0-7671-8015-f6ecc93f1b0e`: new structured parent performance reference, RECEIVE/TOTAL/Gross total return, contractual GBP1m, leverage2, Oct6'26–Oct6'28, quarterly performance resets and termination at reference redemption.
- Explicit separate SONIA funding: PAY direction,150bp stored exactly as0.015, BOOKED_NOMINAL basis, ACT365F, sourced compounded-in-arrears description, monthly resets/quarterly payments. Whole-swap GBP quote divisor100 already includes funding/leverage. No lifecycle processing or cash generation.
- Browser trade `077df544-f20a-4308-b747-6040b92c5ecb` saved and detail verified: partial booked nominal GBP400,000 against contractual GBP1m, quote -1.5/100 = -GBP6,000 entry reference value. Leverage is not applied again; no payment or settlement date generated. Bank A counterparty and funding/reset/redemption terms retained in the immutable snapshot.
- Searching the swap's tenant identifier `ACCEPT_SWAP_261006` did not find it; searching its canonical name did. Identifier discoverability is a follow-up, not a passing identifier-search claim.

### Fresh conflict, stale-tenant and authority checks

- Cash trade `7d34efcc-c35f-42b5-a8e6-9e0829c50d0c` saved10 shares at12.5, then a second tab cancelled that erroneous record while the first froze a20-share replacement. Replacement was definitively rejected for stale history; history showed the original CANCELLED with10 shares and no20-share orphan replacement.
- New history link opens a separate tab (`target=_blank`). Native confirmation prompted a browser-control transport timeout; the API conflict was already visibly rejected. Replaced only this recovery prompt with an explicit on-page history-reviewed checkbox: exit is disabled until checked and the handler independently enforces it. No replay, key rotation or silent new ticket. Regression failed first, then passed; other discard prompts are unchanged and remain outside this bounded adjustment.
- A frozen15-share demo-tenant cash review was submitted after a second tab switched to Fortem Second Tenant/OPERATIONS. It was blocked with “The active tenant changed. Restart the ticket before booking.” No booking success/redirect occurred. Foreign swap detail returned NOT FOUND without facts. Second-tenant default and All history both showed0 records. Its Book trade route redirected to history rather than exposing an editable ticket.
- A browser bond creation probe under Second Tenant/OPERATIONS unexpectedly queued proposal `01a111a4-8b1b-799e-94d3-65a717d23bc4`. Investigation found eleven legacy instrument BFF adapters used environment/default demo identity, bypassing the selected session while the API correctly enforced its received identity. This proposal is unapproved synthetic negative evidence; it was not deleted or approved.
- Removed that fallback from bond/equity/ETP/FX/structured/crypto/index/index-family creation and the legacy crypto detail/decision and index-family decision adapters. They now use signed selected-session tenant/actor; absent session returns401 without upstream calls; upstream403 is retained. Existing API authority remains TENANT_ADMIN + SECURITY_MASTER. No new authority grants or production identity claims.
- New BFF regression matrix:22 expected failures first (wrong tenant/missing-session boundary), then **33 passed** across11 adapters. Browser same OPERATIONS submission retest returnedHTTP403. Full frontend after fixes: **541 passed,115 files**,25.25s, exit0; TypeScript exit0.
- Extended the same boundary to the operations-queue adapter and five remaining legacy instrument server pages (crypto review and crypto/FX/index/index-family creation catalogues). Queue denial/unavailability now returns an honest error, not a successful synthetic queue.13 additional cases failed first; all **46 focused boundary cases passed** after the fixes. No environment-tenant fallback remains under instrument pages/adapters or this queue adapter.
- Recovery acknowledgement initially reached `/trades` by soft navigation but stayed on its loading screen despite server200. Full reload immediately displayed history. The guarded exit now clears the dirty guard and performs full-document navigation, reacquiring the current signed tenant session. Regression failed first and passed after the change.
- Final browser retest: a frozen17-share ticket was rejected after switching to the second tenant. Confirmation/back remained disabled; history acknowledgement was initially unchecked and exit disabled. Restored the demo tenant separately and inspected filtered history: exactly two original10-share cash records, both CANCELLED, with no15/17-share rejected bookings or20-share orphan replacement. Explicitly checking the acknowledgement enabled exit; Leave blocked ticket immediately rendered `/trades` with the current tenant and24 matching records, without another reload, prompt or submission. This is agent-verified history, not a claim that the user has reviewed it.

## Final verification and handoff

- Full frontend regression after all code changes: **554 passed,116 files**,26.28s, exit0. Final handoff rerun again passed **554 tests in116 files**,25.34s, exit0 (`node node_modules/vitest/vitest.mjs run --maxWorkers=2`).
- Final TypeScript check: exit0 (`node node_modules/typescript/bin/tsc --noEmit --incremental false -p tsconfig.json`).
- Scoped isolated Python regression: **126 passed,11 warnings**,37.85s, exit0, as recorded above. This was not the full Python suite. No backend code was changed in the final frontend/session-recovery fixes.
- Sequential author review covered the correction boundary, hydration guard, dated-search invalidation, cash recovery, exact-decimal bond terms and selected-session adapters. No independent reviewer or production deployment check is claimed. Final `git diff --check` passed.
- Browser environment: UI `http://127.0.0.1:3007`, API `http://127.0.0.1:8007`, database `fortem_fx_signoff_722336f2caf94ffca0fd6f9ca3f08701`. The UI preview is a source copy under `C:\Users\forte\Documents\ChatGPT\Tech V2\fx-delivery-preview`; operating data/builds were untouched. No commit or push was performed.

Acceptance-driven fixes in this work:

1. Correct the server/client boundary and pre-hydration guard on replacement-reason gates.
2. Expose a UTC readiness-search date for shared product tickets and invalidate stale results when it changes.
3. Provide explicit history inspection and an acknowledgement-gated, full-navigation exit from blocked cash tickets without replaying a booking.
4. Expose existing bond par/redemption terms without guessing defaults or relaxing readiness.
5. Remove legacy default-demo identity from instrument adapters/pages and the operations-queue adapter; retain signed selected-session identity and honest authorization/service errors instead of synthetic success fallback.

Best-practice research influenced the distinction between browser-visible outcomes and automated fault coverage, the isolated fixtures, and explicit tenant/actor/action regression tests. The evidence ledger records failed-first regressions and limitations rather than equating HTTP success with acceptance.

## Remaining work outside this sign-off

- User walkthrough/sign-off has not been asserted. All seven supported product paths were exercised, not every possible contract, exchange, jurisdiction or instrument subtype. Full-contract swap restrictions and nondeterministic retry/rollback cases have automated rather than exhaustive browser coverage.
- The previously listed swap tenant-identifier search and permission-aware creation/booking UI follow-ups were subsequently implemented and browser-verified; see [the follow-up delivery record](swap-search-and-permission-ui-2026-10-06.md) for regression evidence and scope. Backend authorization remains authoritative; hidden forms/actions are presentation safeguards, not permission grants.
- T+2 weekday defaults are alpha defaults, not exchange/currency holiday-calendar settlement scheduling.
- Contractual delivery/expiry/exercise/redemption, settlement, accounting and valuation/P&L remain deferred. Existing FX-delivery implementation is preserved but not interactively signed off or actuated here.
- This removes default identity from the instrument and queue paths reviewed here, not every legacy market-data/catalogue adapter in the repository. Broader production authentication, deployment and API hardening remain separate work; do not read this as “all APIs are production ready.”
