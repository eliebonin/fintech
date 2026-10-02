# Listed option booking alpha — quality review

**Date:** 2026-10-01  
**Outcome:** Booking-alpha acceptance in an isolated synthetic environment  
**Delivery:** [Listed option booking alpha](../listed-option-booking-alpha.md)

## Automated evidence

| Check | Result |
| --- | --- |
| Lightweight option domain rules, written first | 9 passed |
| Expanded option API coverage | 22 passed |
| Complete Python suite | 431 passed; 471 warnings; 437.65 seconds |
| Final focused Python rerun after queue/attribution refinements | 35 passed; 8 warnings |
| Complete frontend suite | 277 passed across 75 files |
| Typecheck and production build | Passed |
| API contract export check | Passed |
| Generated contract reproducibility | Regeneration left content hashes unchanged |
| Diff whitespace check | Passed |

The full Python run initially had two failures: an option P&L fixture shared a strategy containing FX, and a historical revision-52 migration fixture used the latest writer requiring revision-55 columns. Fixtures were corrected to isolate the option strategy and seed historical rows through the historical schema. The complete rerun passed. Later small backend queue/actor refinements received the final focused rerun, not another full suite.

Coverage includes BUY/SELL and OPEN/CLOSE, exact/minor-unit/zero premium, invalid quantities/dates/terms, hidden tenant references, unsupported conventions, stale terms, permissions, immutable snapshots, duplicate/concurrent replay, transactional annotations, cash-writer derivative rejection and fail-closed P&L. Frontend tests cover model validation, review/edit/retry and tenant-bound proxying. Existing cash/FX regressions ran in the complete suites.

`contract:generate:check` compares generated files to Git HEAD and therefore reports an uncommitted difference. That is not a clean-tree claim: independent before/after regeneration hashes were identical, and the export check passed. No commit was made merely to satisfy this check.

## Synthetic browser evidence

Database: `fortem_fx_signoff_d07737a03c2b43eca72b74953fe0b44b`. API/UI: localhost ports 8001/3001. Prepared with `scripts/prepare_option_signoff_fixture.py`; no operator-database migration or live trade mutation.

- American CALL: BUY/OPEN ten contracts at 2.5, factor 1, multiplier 100 → PAY GBP 2,500. A decimal property of zero, governed HEDGE choice and tag survived review/back-to-edit and persisted in history. Trade `6d054ac4-0b86-4cfb-95d7-49f3992eec1b`.
- Created European cash-settled PUT through the UI; approved in Instrument Requests. Request `01a0f83e-f767-7ae5-b6b3-6a8f15f222ba`; instrument `01a0f83f-7c05-74ea-aa22-6cf473960579`.
- Added XLON listing from the instrument without losing context; reviewed/approved in Operations. Request `01a0f840-8271-75ce-a914-9b5312c2a84b`.
- Booked SELL/CLOSE ten contracts at quoted premium 250, factor 100, multiplier 100 → RECEIVE GBP 2,500. Trade `7f141546-5cf3-4635-be29-743782f14d98`.
- Final detail reload confirmed positive contract count, explicit quoted-unit premium/factor, premium settlement and frozen economics. Captured console error log was empty.
- Compatibility smoke: the existing FX search selected the synthetic EUR/USD contract and loaded its execution/properties form. The cash ticket loaded; its HSBC search displayed no selectable result in this fixture, so no additional cash browser booking is claimed. Cash/FX automated regressions passed in the full suites.

Switching from a selected FX draft hit an embedded-browser navigation timeout. A clean tab loaded the cash ticket; this is not recorded as a passed cross-product dirty-navigation browser check. Existing automated navigation coverage remains green.

Browser testing found the controlled native date input unreliable in this embedded browser. Premium settlement now uses an ISO-date text input with strict real-calendar validation. The final detail labels also avoid implying that a minor-unit quote is a monetary amount.

Local proof files: `C:/Users/forte/Documents/ChatGPT/Tech V2/option-booking-signoff.png` and `C:/Users/forte/Documents/ChatGPT/Tech V2/option-booking-signoff-sell.png`.

## Acceptance boundary

This accepts governed option creation/listing and execution capture, review/retry and immutable history. It does not certify positions, lots, exercise, assignment, contractual close-out, premium payment or valuation. No live deployment was performed. Legacy mock sidebar/generic instrument-detail presentation remains a documented frontend follow-up.

## Subsequent cleanup and local activation

The earlier acceptance boundary above describes the original delivery. The approved follow-up implemented the heading rename, verified tenant presentation, selected-tenant instrument requests, current option-term inspection and cash-ticket derivative filtering. See the [delivery record](../listed-option-booking-alpha.md#completed-booking-and-ux-cleanup) for the current state and deployment limits.

The final follow-up frontend suite passed 290 tests in 80 files, with typecheck/build and contract export checks green. The option/instrument API regression run passed 34 tests, including hidden-underlying redaction and missing-convention preservation. Seven reconciliation/migration tests passed. FX navigation tests passed both cancel and confirm branches. No claim is made that the earlier full 431-test Python suite was rerun for these changes.

Browser checks on the final build confirmed the option term panel and actual tenant context, contextual listing form and cash-only listing results. A complete synthetic cash booking used HSBC, BUY 12 at 8.125 GBP, settlement 2026-10-05, and Acceptance score zero. Review/back-to-edit preserved facts and history persisted the trade as `07e87bf8-317d-43b4-a5b7-f6676bc927f3`. Proof files are `C:/Users/forte/Documents/ChatGPT/Tech V2/option-terms-cleanup.png` and `C:/Users/forte/Documents/ChatGPT/Tech V2/option-cleanup-cash-regression.png`.

The cross-product discard check remains unresolved in the embedded browser. Triggering its native prompt timed out browser input; the exposed dialog API returned no dismissible dialog, and closing the affected synthetic tab also timed out. Automated guard branches passed, but this does not replace manual browser confirmation. The limitation was raised to the user; no fake pass or disabled guard was introduced.

The local `fortem_secm` database was backed up before upgrade. It had revision-53 metadata with compatible pre-existing revision-54 bond columns; migration 54 now preserves compatible fields and refuses incompatible types/nullability/defaults. Upgrade reached revision 55 without changing the nine trades or 271 instruments. The local API and frontend started on ports 8000/3000; API health and tenant-selection HTTP checks succeeded. After browser recovery, the operator tenant selection, Strategies page and creation picker were verified, including the actual tenant label. Proof: `C:/Users/forte/Documents/ChatGPT/Tech V2/option-cleanup-local-app.png`. Synthetic booking tests stayed in the separate acceptance database, not the operator database. This is local activation, not production deployment.
