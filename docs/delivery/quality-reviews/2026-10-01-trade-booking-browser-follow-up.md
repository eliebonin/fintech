# Trade booking browser follow-up

Date: 2026-10-01, Europe/London. Scoped follow-up to the
[initial browser cycle](2026-10-01-browser-trade-configuration-cycle.md).
This is alpha acceptance evidence, not production or accessibility sign-off.

## Delivered changes

- Booking review and saved detail share a presentation-only formatter: Boolean
  values display Yes/No; zero and exact decimal strings are retained. Empty
  values remain unspecified; governed references keep their booked display label.
  Stored values and booking payloads are unchanged.
- Detail distinguishes NOT FOUND (404), ACCESS DENIED (401/403), REQUEST FAILED
  (other client responses) and API UNAVAILABLE (server/transport failure).
  Existing tenant-safe explanatory messages remain in place.
- Editing a previously errored field revalidates that field without hiding
  unrelated errors. Basic validation collects all invalid fields rather than
  only the first. Submit still performs complete validation.
- Error-summary focus is requested for validation/submission failures, not every
  edit. Rapid scalar edits merge into the latest draft rather than a stale render
  closure. Frozen payload/key/tenant and uncertain-retry guards remain unchanged.
- `scripts/browser_trade_configuration_cycle.mjs` provides staged, reusable
  assertions against the real UI through the documented Codex Cua Tab API.
  There are no mocked booking responses or hidden HTTP calls in the regression.

## Fresh verification

Frontend commands, run from `apps/ops-console`:

```powershell
pnpm test --maxWorkers=1
pnpm typecheck
pnpm build
```

235 tests in 63 files passed; TypeScript checking and the production build passed.
The first test run reproduced raw Boolean detail output and misleading error
labels, and failed on the missing revalidation/formatting helpers. One cold
dynamic import also exceeded the existing five-second test timeout; a subsequent
focused run passed without raising the timeout or weakening an assertion.

No backend/schema/contracts changed in this follow-up; the full Python suite was
not rerun. The real API/database were exercised by the browser cycle below.

Independent read-only review identified overbroad edited-field classification:
an unchanged manual settlement date and untouched reference rows could lose
server-only errors. Actual value/row comparison now prevents this. Two additional
tests cover those cases and removal/index shifts. Re-review found no remaining
issues in the scoped fix. The verification totals above include those tests.

## Isolated browser acceptance

Used the retained synthetic database
`fortem_browser_review_c3b17aa3e76e41159d97e2e9dab8feb2`, API port 8001 and
production frontend port 3001. Only the verified isolated frontend process was
restarted. The live database was untouched; port 3000 was not restarted.
Synthetic bookings record executed-trade fixtures and do not send orders.

Final complete staged run: `UI_20261001_1145`. Saved trade:
`b267a4b8-680d-47a2-afc9-6541193b22d1`.

After the independent-review fix and final 235-test build, booking/lifecycle/
isolation were repeated using the still-active UI-created `UI_20261001_1138`
fixtures. All assertions passed; final-build saved trade:
`175422a8-2b57-4114-a5bb-96b16d72ba02`. Its final browser tab returned no captured
warning/error entries. This is not a claim about every abandoned tab or server log.

| Check | Verified result |
| --- | --- |
| Configure through UI | Decimal field, required Boolean, draft catalogue with CORE/HEDGE, publication, catalogue-bound dropdown. |
| Independent validation | Invalid quantity remained visible while correcting a required Boolean; correcting quantity then cleared its error. |
| Editing focus | A keyboard-focused Boolean stayed focused while its required error cleared. |
| Representative ticket | BUY 12 HSBC demo shares at GBP 8.125; Demo Income Strategy; HSBC counterparty, Fortem broker, MVP Operations Booker trader; Acceptance test tag and source reference. |
| Review/back/save/history | Zero, No and governed selection survived review/back. Saved detail showed parties, trader, tag and reference; ledger linked the exact saved trade ID. |
| Catalogue correction | Fresh ticket showed corrected CORE label; historical detail retained original label and record v1. |
| Retirement | Retired CORE unavailable on fresh search; HEDGE remained available. Retired decimal field absent from fresh ticket; historical zero remained readable. |
| Tenant isolation | Equally privileged second synthetic tenant saw no foreign trades or custom fields. Foreign detail displayed NOT FOUND, without trade values or outage badge. |

An earlier development run saved one additional synthetic trade,
`55f12b61-d717-4ade-a72d-c61adc9bdc64`. Failed assertions before confirmation
did not submit bookings. All review fixtures are retained, not deleted.

## Property-heavy density walkthrough

Twenty additional optional TEXT definitions were created through configuration UI.
With retained prior fixtures, the ticket had 29 properties: four required and
25 optional. At 1280×720:

- Document height: 8,493 px, approximately 11.8 viewport heights.
- Required group began around 1,495 px; optional group around 2,342 px.
- Document scroll width 1,265 px: no horizontal overflow at this viewport.
- First/last labelled test values (`Sample 00`, `Sample 19`) survived review and
  back-to-edit. This density draft was not booked.
- One error-link jump was visibly verified to focus the intended required input.
  The repeatable keyboard-link step encountered Cua CDP timeouts, including one
  after the jump succeeded and another preventing follow-on observation. Treat
  that optional automation step as transport-limited, not a clean automated pass.

The core lifecycle regression passed independently of the optional density step.
Some early automation actions also ran before UI readiness; the runner now waits
for navigation readiness and uses keyboard activation where appropriate. Space
activation completed the heavy-ticket review where Enter/mouse activation had
not transitioned it. These are recorded browser-run limitations, not evidence
that every interaction method/device has passed.

Conclusion: required-first grouping remains useful, but 29 properties make a long
ticket. Consider compact optional grouping or a review-oriented workflow in a
separate design discussion. No collapse, column, or layout redesign is delivered.
Human operator feedback is still needed before settling density.

## Follow-up priorities and user decision

Recorded 2026-10-01: the user requested that the proposed next steps be documented
and that frontend/UX improvements be handled later. Ticket usability and density
work are therefore **deferred**, not the next implementation task. Keep the
current layout; no compact mode, optional-field collapse or other redesign is
approved by this documentation decision.

Proposed sequence for subsequent discussion:

1. Review the booked-trade correction/cancellation workflow: reasons, permissions,
   lifecycle transitions and preserved historical evidence. Inspect existing
   capabilities before deciding what needs implementing.
2. Review market-data inspection and valuation-policy selection, including which
   time series and cutoff policy a strategy uses.
3. Move into strategy valuation and P&L once the trade lifecycle and market-data
   policy path are understood and agreed.

Return to frontend/UX later with realistic sparse, typical and property-heavy
tickets and operator feedback. The measured 29-property/~12-screen ticket remains
an open usability finding, not a blocker that must be redesigned before the
functional reviews above. Preserve required-field visibility, validation
navigation, entered values and governed selection rules in any later refinement.

These are documented discussion priorities, not an approved implementation plan
or a claim that correction/cancellation features are absent. No new module work
is started by this decision.

## Re-running the UI regression

Prerequisites: verify the isolated metadata's database/ports and synthetic-only
flag; use a migrated demo database, configured peer tenant with equal test
permissions, and the provisioned Acceptance test tag described in the initial
review. Select Fortem Demo Tenant through the UI before the configuration stage.
The runner deliberately rejects any base URL except `http://127.0.0.1:3001`.
Supply a fresh `UI_...` run code; definitions are not silently reused/deleted.

In Codex `cua_repl`, import the module as a file URL and pass a documented Tab:

```javascript
const cycle = createCycle({baseUrl: "http://127.0.0.1:3001", syntheticOnly: true, runCode: "UI_FRESH_RUN"});
await configureCycle(tab, cycle);
await bookCycle(tab, cycle);
await lifecycleCycle(tab, cycle);
await isolationCycle(tab, cycle);
```

Use `densityFields(tab, cycle, start, count)` in small batches for optional density
fixtures, then `inspectDensity` and `densityReview`. Keep the known native-link
transport limitation above visible when reporting those optional results.
This is an agent-driven, assertion-based browser runner, **not a headless CI job**.
Do not replay confirmation automatically after an uncertain booking result.

Remaining checks: large-catalogue paging, formal screen-reader/device testing,
concurrent lifecycle/booking races and stale-page tenant-switch writes. Tag
creation management remains outside this UI slice. No production booking,
automatic merge or commit was performed.

## Saved local evidence

Final historical-detail screenshot after correction and retirement:
`C:/Users/forte/Documents/ChatGPT/Tech V2/browser-followup-final-detail-20261001.jpg`.
Structured cycle results and measured density:
`C:/Users/forte/Documents/ChatGPT/Tech V2/browser-followup-result-20261001.json`.
The isolated instance metadata/logs remain in the same directory. Do not delete
or stop unrelated databases/processes when later cleaning up this review instance.
