# Option lifecycle notifications and read-only inspection — 11 November 2026

## Use in the portal
Under **Strategy → Overview → Lifecycle assistance → Option expiry**, select manual0 or notifications1. Existing subscription, explicit LIFECYCLE_READ/CONFIGURE and strategy permissions still apply. The strategy setting is independent of bonds and futures; no positive selection, grant or subscription is provisioned by the feature.

Open `/lifecycle`, choose **Option expiry** or **All events**, then apply the strategy/instrument/date filters. Rows distinguish the sourced last-trading cutoff, expiry and any supplied final settlement date. **Inspect option** opens the existing modal side panel without losing filters, pagination or keyboard focus.

Inspection presents underlying name, call/put, fixed strike/currency, American/European exercise style, cash/physical terms, signed contracts, gross opposing allocations, premium multiplier and reference deliverable units. Exact inputs remain decimal strings; thousands separators are display-only. Current source identities and approval evidence are collapsed. An inaccessible underlying is never disclosed through its name or UUID.

Expiry is an Ops review notice, not proof of exercise, assignment, lapse, settlement or financial closure. American-style early exercise/assignment is explained without inventing daily exercise events. A zero net holding with nonzero classified allocations remains visible; flat/cancelled holdings disappear without being labelled settled. Missing evidence is unknown/blocked rather than zero.

## Scope and trade-offs
- Supported native listed-option bookings and immutable original premium evidence are reused. This does not add an OTC option-creation/booking workflow.
- Only manual0 and notifications1 are supported. Purchased Tier2/3 does not create an option financial handler. API and database constraints reject unsupported selections; downgrade previews respect this per-event ceiling.
- Exact `option_terms.last_trading_at_utc`, common expiry and supplied final settlement remain distinct. Expiry does not imply last trading or a T+1/T+2 settlement lag. Date-only deadlines remain day-level, without an invented time.
- Broker exercise-instruction cutoffs, AM/PM settlement fixing designations, Bermudan exercise-window assessment, exercise/assignment confirmations and economic outcomes remain unimplemented. They are displayed as not recorded/unassessed where relevant.
- Current terms are compared with the original BOOKED contract facts, including strike, underlying, style, settlement, currencies, multipliers and dates. Conflicts block source-dependent notice assessment; original evidence is never rewritten. Current versus original premium/deliverable units are not turned into an expected cash flow or underlying exposure.
- Notifications never prepare, book, exercise, assign, settle, pay, deliver, alter cash/accruals or run valuation. The dashboard has no persisted task acknowledgement/assignment queue or notification-delivery scheduler.

## Implementation
[Option domain reader](../../lifecycle/worklist_options.py) owns product sources, current ledger/allocation reconstruction, original-contract comparisons and lazy source inspection. [Shared held-candidate/deadline helpers](../../lifecycle/worklist_holdings.py) retain the existing futures predicates and serve options with explicit product/event pairs. Candidate search and permission scope precede full-population state/count/pagination. Cancellation facts retain their original trade identity.

[GET adapter](../../apps/reference_api/lifecycle_worklist_routes.py) and [BFF](../../apps/ops-console/src/app/api/lifecycle/%5B...segments%5D/route.ts) recheck current tenant/strategy/notification scope and allow only read inspection. The expected-tenant header, allowlisted milestone inputs, read-workload admission, obsolete-read abort and changed-source fingerprint rejection remain active. [Option inspector](../../apps/ops-console/src/features/lifecycle-worklist/option-inspection.tsx) never mounts native financial controls; shared contract styling is also used by futures.

[Migration114](../../alembic/versions/20261111_114_option_lifecycle_notifications.py) extends only the retained strategy assistance CHECK constraint. No financial table, backfill, permission, subscription or strategy default is added. [Specification/research](../superpowers/specs/2026-11-11-option-lifecycle-notifications.md) and [execution plan](../superpowers/plans/2026-11-11-option-lifecycle-notifications.md) preserve the approved boundary.

## Verification and activation
Initial lightweight event/deadline, BFF and mounted UI tests failed before their implementation. The first real-booking reader group passed 25 tests, including existing futures deadline checks.38 focused frontend/BFF/help tests and TypeScript passed.18 mounted Edge journeys passed across option/futures/coupon/FX inspection, assistance settings and existing closing-drawer behavior. Browser scenarios use mounted components with mocked HTTP; real booked-source/domain and scope checks use disposable PostgreSQL databases, not operating financial data. Desktop/mobile captures were visually inspected for readable contract facts, signed contracts and overflow containment.

The final bounded group covered63 backend cases:62 initially passed and one old negative assertion still expected options to be unsupported. That assertion now uses a genuinely unknown event type; all4 scoped API cases passed on rerun. An additional focused run passed both valid cash/physical option cases with an explicit assertion that their notices are unblocked. Groups overlap; counts are not added as independent tests. The checks include private-underlying nondisclosure, notifications-only database enforcement, selected read scope, cancellation, net-zero allocations, original-source changes, downgrade behavior and54 notices across27 strategies created with native bookings before pagination.

TypeScript/OpenAPI checks and byte-exact generated contract reproduction passed. Desktop/mobile captures were inspected. The native-read model uses disposable real data, while mounted browser HTTP responses are mocked; no new full-stack financial option lifecycle is claimed. No full project regression suite was run. Existing Starlette/SQLAlchemy dependency deprecation warnings are outside this feature.

**Local activation:** migration114 applied after verifying the existing local revision113. Retained trade, lifecycle-selection, subscription and access-audit counts matched before/after. Only the verified task-owned fintech API8000 was restarted; live OpenAPI exposes option inspection and OPTION_EXPIRY selection, and frontend3001 is healthy. No grants, positive strategy selections, operating trades, financial results or Toolhive changes were made.

## Research and applicability
Reviewed/opened 11 November 2026:
- [OCC/OIC exercise guidance](https://www.optionseducation.org/referencelibrary/faq/options-exercise) distinguishes exercise styles, broker instructions and exercise-by-exception from confirmed outcomes. No OCC threshold or broker deadline is hardcoded.
- [Cboe SPX specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications) illustrates series-specific differences between last trading and expiry. Its dated product snapshot is not used as a current calendar or universal expiry formula.
- [WAI modal-dialog guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) informs contained focus, Escape and focus restoration through the reused native modal.

The independent notifications-only selection and day-level treatment of date-only sources are explicit project choices, not regulatory mandates.

## Next discussion: structured observations and potential autocalls
Existing `secm.schedule`/`schedule_event` and structured condition/group/action records already store observation dates, payment dates and first-autocall eligibility. The structured-product writer separates parent/autocall observations from coupon observations for relevant templates. The next proposed slice is read-only scheduled observation/potential-autocall notices, with sourced barriers/conditions visible in inspection. A scheduled test is not a confirmed autocall or redemption. Products referenced by swaps need dependency-aware relevance and must not imply automatic swap termination. No structured-product detector or outcome engine is implemented by this option delivery.
