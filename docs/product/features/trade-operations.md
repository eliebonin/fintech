# Trade operations — capability records

11 November: [Business-day proximity display](../../delivery/lifecycle-business-day-colours-20261111.md) adds labelled date badges and a Timing guide. Missing holiday-calendar configuration is an explicit weekday estimate, not inferred contractual evidence.

11 November: [Remaining lifecycle source batching](../../delivery/lifecycle-reader-batching-20261111.md) improves FX/future/option reads and preserves complete source/economic checks; bond/coupon discovery was already batched. No new financial product coverage. [Instrument/Event column separation](../../delivery/lifecycle-worklist-20261105.md#event-column-readability--11-november-2026) is delivered. Further permission-context/evidence consolidation is investigated but not implemented; the measured local repetition is about 20 ms, not a demonstrated seconds-long bottleneck.

26 October F19: [shared instrument labels](../../delivery/shared-instrument-display-20261026.md)
cover trade history/detail headings and four booking searches, without changing
booking context DTOs, submitted payloads or frozen economics. Existing SQL search
semantics and readiness gates remain; current names do not replace booking evidence.

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Trading operations/engineering  
**Last reviewed:** 2026-11-11 (F24/F51 maturity, coupon, futures/option and structured information boundaries)

[Feature register](../feature-register.md). [Product restrictions](product-booking.md) remain authoritative alongside common controls.

## F19 Booking console and readiness

- **Desired:** A menu-accessible booking page searches eligible references and exposes required economics/metadata; it is not launched only from a listing.
- **Status / backend / frontend:** ALPHA. Shared authority, strategy, replay/savepoint and annotation controls plus product validators; `/trades/new`, ready-first search, unavailable reasons and review/submit state.
- **Cuts/trade-offs:** Readiness is advisory; the authoritative writer revalidates actual execution inputs. Product tickets remain separate instead of forcing every instrument into share-price economics.
- **Weaknesses:** Search/date/pagination support varies by product; long property sections can be dense. Local synthetic browser evidence is not latest whole-system visual sign-off.
- **Remaining:** Realistic ticket UX/accessibility acceptance and consistent supported-scope messages as products expand.
- **Evidence:** [Readiness](../../delivery/booking-readiness-alpha.md), [controls](../../delivery/booking-controls.md), [properties UX](../../delivery/trade-booking-properties-ui-alpha.md).

## F20 Governed trade properties

- **Desired:** Common nullable party/trader fields plus tenant property definitions with types or curated lists.
- **Status / backend / frontend:** ALPHA. Shared tenant reference data, immutable field definitions, canonical standard roles and versioned trade profiles pinned per strategy. Separate source maintenance, Fields/Lifecycle rules, publish review, explicit singular/batch adoption, scoped usage/history and profile-aware booking/import/lifecycle consumers.
- **Cuts/trade-offs:** There is no fixed field1…field30 slot schema, but a per-tenant safety quota limits active property definitions to 1,000; tags have a separate 1,000-active-item quota. Meanings are immutable/versioned; retire an old field rather than reusing it for a different concept. Legacy embedded CHOICE lists are read history, not new definitions.
- **Weaknesses:** Manual curation, no external party-master sync or universal cascading/reference queries. UI density still needs realistic acceptance.
- **Remaining:** [Reference data and profile delivery](../../delivery/tenant-reference-data-trade-profiles-20261104.md) implements required/optional/not-used and lifecycle rules per assigned profile. Publishing never upgrades assignments. Profile-specific source subsets and saved server drafts remain deferred. Data-source synchronization/import/export and advanced dependent fields remain separate; preserve historical labels/definitions and inactive-value controls.
- **Evidence:** [Configuration/cleanup](../../delivery/governed-trade-configuration-alpha.md), [management UX](../../delivery/trade-configuration-ui-alpha.md), [booking UX](../../delivery/trade-booking-properties-ui-alpha.md).

## F21 History and detail

- **Desired:** View actual tenant trades, recent history, saved economics, parties/properties and original evidence.
- **Status / backend / frontend:** ALPHA. Live scoped paginated reads and immutable product snapshots; `/trades` default two-week window, filters/pages/detail and return navigation.
- **Cuts/trade-offs:** Recent default is a query preference, not deletion of older history. Details display frozen values, not recalculated current instrument terms.
- **Weaknesses:** No complete bulk-export/blotter analytics, settlement status or accounting reconciliation journey.
- **Remaining:** Broader operational search/export and realistic long-history acceptance; latest permission/layout walkthrough.
- **Evidence:** [History delivery](../../delivery/trade-history-alpha.md), [correction delivery](../../delivery/historical-booking-and-record-corrections-alpha.md), [detail route](../../../apps/ops-console/src/app/trades/[tradeId]/page.tsx).

## F22 Record corrections

29 October [cash extraction](../../delivery/cash-booking-service-extraction-20261029.md)
moves shared linked-replacement helpers to `trading.corrections`; cancellation
orchestration/HTTP remain in the existing adapter. Correction rules and support
status are unchanged.

- **Desired:** Cancel an erroneous booking or atomically replace it, with reason, concurrency controls and original facts retained.
- **Status / backend / frontend:** ALPHA. Append-only CANCELLED/SUPERSEDED/replacement evidence, sequence/replay guards and scoped authority; supported trade detail actions and correction-prefilled ticket. Unproved legacy bookings have cancel-only recovery.
- **Cuts/trade-offs:** Cancel/replace corrects records; an opposite market execution is a new trade, not settlement. Not every lifecycle history is supported by P&L.
- **Weaknesses:** Cancellation/supersession effective after the opening boundary inside the requested period blocks valuation. A removal known at the information cutoff and effective by the opening boundary can exclude the erroneous booking while preserving audit lineage. There is no universal historical ledger replay/lot accounting.
- **Remaining:** Reconcile correction-period position/financial semantics before broadening valuation; retain cancel-only safeguards for legacy evidence.
- **Evidence:** [Corrections](../../delivery/historical-booking-and-record-corrections-alpha.md), [legacy cancellation](../../delivery/legacy-booking-cancellation-2026-10-08.md), [position limits](../../delivery/position-reconstruction-foundation.md).

## F23 Historical and recognition dates

- **Desired:** Book historical executions against historically applicable definitions, with optional built-in starting valuation date.
- **Status / backend / frontend:** ALPHA. UTC execution-date/reference checks, current write authority and effective valuation date evidence; ticket date inputs and date-based valuation requests.
- **Cuts/trade-offs:** Recognition defaults to execution's UTC date; it can be deferred to a later date with a reason, but cannot precede execution. It is a standard field, not tenant custom data. Historical cash booking selects the applicable approved version but requires its identity, currency, venue, symbol and factors to agree with the current projection; materially changed historical economics remain unsupported. Settlement, economic recognition and information availability stay distinct.
- **Weaknesses:** Provider-derived inception estimates do not prove historical ISIN/ticker/venue continuity; backdated corrections invalidate naïve checkpoints.
- **Remaining:** Historical reference stewardship and checkpoint invalidation; maintain explicit economic date, observation date and information cutoff in evidence.
- **Evidence:** [Daily recognition](../../delivery/daily-valuation-recognition-progress.md), [historical reference dates](../../delivery/index-trading-history-and-yahoo-2026-10-08.md), [recognition tests](../../../tests/test_position_recognition.py).

4 November: [Profile-aware allocation rules](../../delivery/tenant-reference-data-trade-profiles-20261104.md) preserve stable source identities and current native requirements in booking, corrections and supported maturity. Existing global rule rows remain history; no new lifecycle handler or financial formula is introduced.

5 November: [Lifecycle operations worklist](../../delivery/lifecycle-worklist-20261105.md) now discovers bond maturities for explicitly enabled strategies. Scoped current ledger/source reads, actionable/information filters, retained processing status and contextual native handoff do not create financial effects. At that checkpoint FX discovery was deferred; the [11 November mixed worklist](../../delivery/fx-maturity-worklist-20261111.md) and [coupon notices](../../delivery/coupon-notifications-20261111.md) supersede that discovery limit. Other detectors remain deferred.

## F24 Contractual lifecycle

11 November: [Batched structured-source reads](../../delivery/structured-lifecycle-batch-reads-20261111.md) preserve complete event/source proofs and permission boundaries while eliminating per-contract SQL amplification. The SQL-free renderer serves single and bulk inspection.

11 November: [Structured informational notifications](../../delivery/structured-informational-notifications-20261111.md) shows current source-linked coupon/autocall observations, final valuation and maturity, for direct notes or structured performance references of held swaps. All notices remain INFORMATION. A passed date is not a confirmed outcome, payable amount or closing instruction. Existing financial handlers remain limited to bonds and deliverable forwards.

- **Desired:** Linked delivery, option exercise/expiry, bond redemption and swap reset/termination events without fabricated opposite executions.
- **Status / backend / frontend:** PARTIAL. Ops-triggered full plain-bond redemption and deliverable FX-forward maturity closure verify zero remaining compatible exposure. `/lifecycle` supplies mixed bond/FX maturity discovery, read-only sourced coupon/futures/option deadline notices and information-only structured schedules and a contextual native side panel; `/trades/lifecycle` retains the full Bonds / FX forwards workspace with preview, preparation, approval, posting and cancellation. FX uses a maturity-day spot suggestion or sourced entered rate, feeds rate-based P&L, and does not create cash/delivery. Discounted model MTM remains unsupported. The separate FX-delivery prototype remains parked/not signed off.
- **Cuts/trade-offs:** Maturity is a term, not evidence of performed settlement. Settling a cash purchase/premium does not extinguish its holding.
- **Weaknesses:** No signed-off general exposure-extinction/obligation/cash-security movement framework across instruments.
- **Remaining:** Partial/amortising/indexed/defaulted redemptions, derivative lifecycle and other notification discovery; settlement/accounting remain separate. Do not auto-close exposure just because the calendar date passed. Final bond interest/coupon handling remains separate.
- **Evidence:** [Plain-bond delivery](../../delivery/plain-bond-redemption-20261014.md), [FX maturity delivery](../../delivery/fx-forward-maturity-20261014.md), [earlier scope ruling](../../delivery/booking-signoff-and-lifecycle-execution.md), [FX prototype](../../delivery/fx-delivery-lifecycle-alpha.md), [agreed lifecycle boundary](../../delivery/booking-and-lifecycle-scope.md).

The [tenant lifecycle handling modes](#f51-tenant-lifecycle-handling-modes) apply to bounded plain-bond and deliverable FX-forward workflows; this does not sign off the FX prototype or enable other product lifecycles.

14 October follow-up: [deliverable FX maturity](../../delivery/fx-forward-maturity-20261014.md)
also consumes these modes for exposure closure, not actual delivery or general
forward valuation. Other derivative lifecycles remain deferred.

FX prefilled booking may now use a sourced Ops-entered closing rate, retaining the
spot suggestion, source/reference, reason and actor separately. Missing spot
blocks one-click booking, not sourced manual entry. REVIEW still independently
approves the retained proposal; approval cannot replace its rate. Bond redemption
prices remain contractual and non-editable.

## F51 Tenant lifecycle handling modes

5 November: [Subscription ceilings and strategy/event assistance are implemented](../../delivery/lifecycle-assistance-entitlements-20261105.md), with reviewed downgrade choices and enforcement in both bounded maturity handlers. Commercial ceilings0–3 remain distinct from native DIRECT/REVIEW/MANUAL. Tenant transitions and platform subscription changes keep separate authority. Bond-maturity discovery is now delivered by the [shared worklist](../../delivery/lifecycle-worklist-20261105.md); FX discovery and coupon/futures/option/structured notices are now delivered in the 11 November extensions; retained tasks and billing remain deferred.

- **Desired:** Each tenant can choose how lifecycle events are handled per instrument type, including events such as dividends, coupons and maturity.
- **Origin:** Requested on 12 October; clarified and permission implementation approved on 14 October. Earlier unattended automatic/four-mode wording is superseded by Ops-triggered processing below.
- **Status / backend / frontend:** ALPHA for plain bonds and deliverable FX-forward maturity. Explicit scoped permissions protect separate per-product/per-strategy processing modes, immutable proposals, independent approval, posting and linked cancellation; `/trades/lifecycle` exposes these controls. Unconfigured assistance is0; native review defaults to REVIEW. FX additionally requires an explicit pricing policy/cut and MARKET_DATA_READ. The worklist discovers bond and deliverable FX maturities plus sourced coupon dates, futures/option deadlines and information-only structured observations/final valuation/maturity. Futures, options and structured schedules have independent selections0/1 and no financial handler. Coupon inspection is read-only at every tier and shares the bond notification selection; other detectors remain deferred.

These are native execution/review modes, separate from the subscribed ceiling and selected assistance tiers0–3.

| Mode | Desired booking behavior | Desired notification behavior |
| --- | --- | --- |
| 1. Book now (DIRECT) | With selected3/ceiling3, Ops clicks to execute a validated closing entry. At selected2, retained preparation/confirmation is required instead. No unattended scheduler. | Bond/FX maturity worklist delivered; coupon notices remain read-only. Other detectors deferred. |
| 2. Prepare for approval (REVIEW) | Prepare an entry; an independent selected user and real operator approve before booking. | Prepared-entry table and bond/FX maturity worklist delivered; coupon notices remain read-only. |
| 3. Manual (MANUAL) | Ops reviews a retained proposal and explicitly confirms it under selected assistance2/3; no no-proposal one-click path. | Bond/FX maturity worklist delivered; coupon notices remain read-only. Other detectors deferred. |

- **Cuts/trade-offs:** Explicit lifecycle grants require TRADING and action-bound strategy scope. Book/approve additionally require TRADE_WRITE on the same strategy. Corrections reuse TRADE_CORRECT. Administrator role and existing seed/bootstrap never grant future lifecycle actions. No live grants were added. Future mode/ancestry must come from server records, not browser-supplied authority.
- **Weaknesses:** Bond/FX maturity discovery and read-only coupon/futures/option and structured notices are delivered, but there is no persisted acknowledgement/assignment queue, structured outcome assessment or generic manual lifecycle ticket. Coupon visibility currently shares the bond setting; position context is not settled entitlement, and recorded confirmation is not payment reconciliation. Plain-bond principal and deliverable FX maturity closure only; no NDF/early termination/other derivatives. Final bond interest is separate. FX maturity posting and supported rate-based P&L do not establish discounted model MTM.
- **Remaining:** Broader lifecycle economics, futures notice/broker deadlines, option broker/fixing/outcome evidence, structured outcome confirmation and other product notifications, independent coupon visibility and receipt reconciliation. Full termination zeroes exposure per distinct canonical instrument/strategy, never through risk likeness; recognition on T includes closure P&L on T. Payment remains separate. Backdated corrections require recalculating affected valuations; published evidence is not silently rewritten.
- **Evidence / related capabilities:** [Futures notice scope and verification](../../delivery/future-lifecycle-notifications-20261111.md), [mixed maturity worklist](../../delivery/fx-maturity-worklist-20261111.md), [coupon notice scope and verification](../../delivery/coupon-notifications-20261111.md), [plain-bond delivery](../../delivery/plain-bond-redemption-20261014.md), [approved authority foundation](../../delivery/lifecycle-authority-foundation-20261014.md), [authority guards](../../../security_master_schema/lifecycle_authority.py), [scope tests](../../../tests/test_lifecycle_authority.py), [contractual lifecycle](#f24-contractual-lifecycle), [economic flows](valuation-and-pnl.md#f38-accruals-and-economic-flows), and [deferred settlement/accounting](future-modules.md#f47-settlement-and-accounting).


## Allocation preservation across maturity — F20/F24/F51 follow-up

The [4 November delivery](../../delivery/lifecycle-allocation-preservation-20261104.md)
adds explicit tenant-selected field dimensions and immutable policy revisions, typed
per-entry inputs, and allocation-preserving bond/FX maturity closure. An event may
create multiple entries, each with ordinary governed property assignments and exact
movement proof. Zero aggregate quantity does not erase opposing allocations. Posting
and cancellation are atomic; inherited classifications are read-only, required fresh
values need validation, and changed sources invalidate preparation. No historical
property values or financial results are rewritten. Ordinary position reports remain
economically aggregated; broader lifecycle discovery, reclassification and retired-source
remediation remain disclosed in the delivery note. F20/F51 remain ALPHA; F24 remains PARTIAL.

### Lifecycle search and booking presentation — 5 November 2026

The [UI follow-up](../../delivery/lifecycle-booking-ui-20261105.md) adds instrument name/identifier search across the scoped worklist before counts/page selection. The existing maturity workspace presents context, controls, sourced inputs, approval and audit history in separate cards, retaining native posting authority and allocation validation. Processing-mode changes reload current assistance decisions; no booking occurs on navigation.

11 November: [Lifecycle closing-entry drawer](../../delivery/lifecycle-action-panel-20261110.md) embeds the existing governed maturity workflow in the worklist, preserving filters and guarded financial retries; full-workspace access remains available. Direct and independently approved booking passed real isolated BFF/API/PostgreSQL acceptance; current ledger checks use database recording time. The normal app was subsequently [recovered on port15432](../../delivery/local-postgres-port-recovery-20261111.md) with existing data; operating financial acceptance remains separate.

### Mixed FX-forward maturity discovery — 11 November 2026

The [delivery](../../delivery/fx-maturity-worklist-20261111.md) extends Lifecycle to deliverable forward maturities with All/Bond/FX filters before counts/page selection. The drawer uses existing native FX preview, rate override, preparation and booking controls. Tier ceilings, strategy scope, required annotations and independent approval remain authoritative. Standard and custom prepared fields are retained on reassessment/confirmation. No cash delivery/payment is generated; no migration or automatic strategy enablement occurs. Other event types remain outside this delivery.

### Coupon notices and inspection — 11 November 2026

[Delivered scope and limits](../../delivery/coupon-notifications-20261111.md): sourced bond coupons share the Lifecycle report with a read-only inspection drawer. Explicit dates, reference-position context, schedule revisions and current/reversed/earlier-schedule confirmations are visible. No booking/payment confirmation, cash inference, accrual change or additional coupon income is generated. Discovery currently inherits bond notification visibility and stays inside the selected date window.

## Futures lifecycle awareness — 11 November 2026

[Delivery and limits](../../delivery/future-lifecycle-notifications-20261111.md): independent manual0/notifications1 selection; sourced last trading, optional expiry, final settlement and physical delivery milestones. Read-only inspection never mounts a booking console. First-notice/broker deadlines, futures preparation/closure/roll and actual delivery remain deferred.

## Option lifecycle awareness — 11 November 2026

[Delivery and limits](../../delivery/option-lifecycle-notifications-20261111.md): independent0/1 selection, sourced last-trading/expiry/settlement notices, read-only contract/position inspection and original-source conflict checks. Exercise/assignment, AM/PM fixing, broker cutoffs and financial closure remain separate/unimplemented. Structured observation/potential-autocall notices are next discussion, not delivered here.
