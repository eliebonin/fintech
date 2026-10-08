# Booking sign-off and lifecycle execution

**Status:** Scoped trade-side alpha acceptance completed; contractual lifecycle phase parked. **Started:** 2026-10-06. **Trade-side completion:** 2026-10-06.

**Current scope ruling (2026-10-06):** The user deferred settlement and accounting and authorized the remaining trade-side acceptance checks. Follow [the current checklist](trade-side-acceptance-2026-10-06.md). The lifecycle phase below records an earlier direction and is now parked; existing FX-delivery work is preserved but not signed off. Do not expand trade acceptance into delivery/accounting implementation.

User requested sequential execution, documentation and implementation without plan-approval checkpoints. This explicitly resumes the previously paused browser sign-off. Use isolated synthetic data only; no operating restart/data write, GitHub push or valuation/P&L expansion is included.

## Intent and execution order

1. Complete end-to-end creation/approval/booking/history/record-correction acceptance across supported product types. Distinguish browser observations from HTTP/component evidence. Reproduce acceptance defects with lightweight failing tests, fix them and run broader regressions.
2. Specify and implement bounded contractual lifecycle slices separately from cancel/replace of erroneous bookings. Preserve the original execution and append-only evidence. Start with explicit events and clear operational state, not automatic date-driven closure.
3. Verify the completed slices, update capability/scope documentation and report remaining limitations. Production deployment controls remain tracked in the API hardening report.

## Constraints

- Creation/approval: active TENANT_ADMIN + SECURITY_MASTER. Booking/correction: active TENANT_ADMIN + TRADING.
- No artificial opposite execution to represent delivery, expiry or redemption. A maturity date does not prove settlement.
- Effective and recorded dates, tenant isolation, exact retry protection and expected sequence checks remain mandatory.
- Settlement of a purchase does not extinguish the acquired holding. Option premium payment does not extinguish the option. Exercise/assignment and bond redemption require correct quantities/obligations; do not introduce guessed cash postings or lot allocation.
- Choose one authoritative cash/security movement path before adding postings. Separately booked cash trades must not double count generated movements.
- Existing record corrections must fail closed on contractual chains they cannot safely correct; a lifecycle workflow must not weaken that boundary.
- Preserve the dirty feature checkout. No subagents or independent-review claim. No commits solely to satisfy skill/Git-based checks.

## Task ledger

- [x] Supported browser access and isolated preview established.
- [x] Creation/approval/booking/history/correction acceptance recorded per product in the current checklist.
- [x] Acceptance defects fixed test-first and verified.
- [x] Contractual lifecycle design and product-slice plan grounded in existing schemas/snapshots.
- [x] First planned lifecycle slice implemented test-first, with history/detail controls and documented limits.
- [x] Final trade-side automated verification, sequential author review and delivery report recorded in the current checklist.

The earlier lifecycle implementation entries below describe preserved work, not current authorization to actuate events or a completed lifecycle sign-off. Final trade-side evidence:554 frontend tests,126 scoped isolated Python tests and TypeScript passed; all seven fresh creation/booking paths, six noncash correction/cancellation cycles and history/tenant-boundary checks are recorded in [the dated report](trade-side-acceptance-2026-10-06.md). User walkthrough, production readiness and lifecycle acceptance remain separate.

### Findings and rulings

- Existing cancellation/replacement is record correction, not contractual lifecycle. Its automated acceptance spans all seven booking paths; browser acceptance was interrupted and then explicitly paused.
- Browser inventory on resumption succeeds through the supported browser tool. No operating browser tab is present. A new isolated preview will be used; no workaround for a security refusal will be attempted.
- The two phases are separate deliverables. Lifecycle design follows actual booking acceptance rather than assuming a universal one-trade settlement/holding model.

## Evidence

- Isolated UI/API ports 3006/8006; database `fortem_fx_signoff_722336f2caf94ffca0fd6f9ca3f08701`. Copied UI source/build under ignored `logs/booking-signoff-20261006/app`; operating build/database untouched.
- Browser cash booking: HSBC demo listing, BUY 10 at GBP 12.50, governed HEDGE catalogue value, decimal 7.25 and tag saved and visible in detail. Original `33e58776-4231-46b9-be2b-9f7b813e86ca`.
- Acceptance defect: replacement reason confirmation crashed because `cloneElement` attempted to clone a server-supplied rendered slot. Changed the gate to accept serializable context/strategies and construct the appropriate ticket inside its client module graph. Seven new branch regressions failed first, then the gate/page tests passed 15 cases; TypeScript exit 0. Existing plain-element tests did not model the RSC boundary.
- Browser retest: replacement quantity 20 saved as `ca139a6b-c996-4920-b2d6-5b215581bb20`; BOOKED/CORRECTED lineage and reason displayed. Explicit cancellation appended CANCELLED, preserved economics and removed correction actions. Following the original link showed SUPERSEDED with original quantity 10 and all original properties/tags retained. Optional annotations were deliberately not copied to replacement.
- At this earlier stage all seven ticket execution/detail walkthroughs had passed, while browser creation/approval coverage was pending. The dated report now completes that trade-side coverage; contractual lifecycle acceptance is parked. This is not production certification.
- Browser execution/detail passes: FX `e0567578-6ab4-419c-ba68-38c99b3bc3b5` (EUR 1m receive/USD 1.1m pay); option `0928f870-34f3-421a-a26e-b2e9517ac00e` (10 BUY/OPEN, GBP 2.50 quote, multiplier 100, GBP 2,500 premium); future `69a851f3-2f81-4902-b160-78a160360fd7` (2 contracts at 5,000.25, USD 5/point, USD 50,002.50 reference value); OTC note `c5e56c7a-847a-4e74-9b71-1c19c2f57530` (100k nominal at 98.5, GBP 98,500); OTC bond `ab3f4e3a-ac65-47c5-9a15-2779c11d8a12` (100k nominal, CLEAN 98.5 + GBP 1,250 accrual = GBP 99,750). Saved snapshots and counterparty were inspected, not just successful POST responses. Reference fixtures were provisioned through test helpers/API; their creation is not browser-creation evidence.
- Full frontend regression after the boundary fix: **494 passed, 112 files**, 24.11 seconds, exit 0 (`logs/signoff-frontend-regression.log`).
- Swap browser trade `f6aa54fe-b1b2-419f-bb52-5172a915da92`: GBP 400,000 nominal at -1.5 / divisor 100 = -GBP 6,000 reference value; no cash entry or double leverage. Replacement reason gates rendered real tickets for FX, option, future, structured note, bond and swap; cash replacement/cancellation completed fully. Gate smoke coverage is not six additional complete replacement bookings.
- Lifecycle design selected: [FX delivery first](fx-delivery-lifecycle-alpha.md). Remaining product events require their own bounded designs rather than generic settled flags.
- FX delivery implementation: append-only CONFIRM/REVERSE evidence carries inherited booked-currency leg, actual effective UTC timestamp and source evidence. Both legs must be fully confirmed before delivery is `DELIVERED`; maturity is only `DUE`. The original trade remains `BOOKED`, cash postings and valuation remain out of scope, and booking correction fails closed once contractual evidence exists. OpenAPI/type checks and isolated API checks passed; interactive browser validation is pending because the browser policy blocked navigation to the disposable preview.
