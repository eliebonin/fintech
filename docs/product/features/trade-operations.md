# Trade operations — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Trading operations/engineering  
**Last reviewed:** 2026-10-12

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
- **Status / backend / frontend:** ALPHA. Tenant/version-scoped definitions, typed values, governed catalogue records, lifecycle and historical values; trade configuration/list curation and booking property entry.
- **Cuts/trade-offs:** There is no fixed field1…field30 slot schema, but a per-tenant safety quota limits active property definitions to 1,000; tags have a separate 1,000-active-item quota. Meanings are immutable/versioned; retire an old field rather than reusing it for a different concept. Legacy embedded CHOICE lists are read history, not new definitions.
- **Weaknesses:** Manual curation, no external party-master sync or universal cascading/reference queries. UI density still needs realistic acceptance.
- **Remaining:** Data-source synchronization/import/export and advanced dependent fields only after explicit scoping; preserve historical labels/definitions and inactive-value controls.
- **Evidence:** [Configuration/cleanup](../../delivery/governed-trade-configuration-alpha.md), [management UX](../../delivery/trade-configuration-ui-alpha.md), [booking UX](../../delivery/trade-booking-properties-ui-alpha.md).

## F21 History and detail

- **Desired:** View actual tenant trades, recent history, saved economics, parties/properties and original evidence.
- **Status / backend / frontend:** ALPHA. Live scoped paginated reads and immutable product snapshots; `/trades` default two-week window, filters/pages/detail and return navigation.
- **Cuts/trade-offs:** Recent default is a query preference, not deletion of older history. Details display frozen values, not recalculated current instrument terms.
- **Weaknesses:** No complete bulk-export/blotter analytics, settlement status or accounting reconciliation journey.
- **Remaining:** Broader operational search/export and realistic long-history acceptance; latest permission/layout walkthrough.
- **Evidence:** [History delivery](../../delivery/trade-history-alpha.md), [correction delivery](../../delivery/historical-booking-and-record-corrections-alpha.md), [detail route](../../../apps/ops-console/src/app/trades/[tradeId]/page.tsx).

## F22 Record corrections

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

## F24 Contractual lifecycle

- **Desired:** Linked delivery, option exercise/expiry, bond redemption and swap reset/termination events without fabricated opposite executions.
- **Status / backend / frontend:** DEFERRED. A bounded FX-delivery event/workflow implementation exists; broader contractual lifecycle and this slice's final acceptance are parked.
- **Cuts/trade-offs:** Maturity is a term, not evidence of performed settlement. Settling a cash purchase/premium does not extinguish its holding.
- **Weaknesses:** No signed-off general exposure-extinction/obligation/cash-security movement framework across instruments.
- **Remaining:** Resume a separately scoped event/position transition, then settlement/accounting; choose one authoritative posting path and prevent double counting. Do not auto-close exposure just because the calendar date passed.
- **Evidence:** [Current scope ruling](../../delivery/booking-signoff-and-lifecycle-execution.md), [FX prototype](../../delivery/fx-delivery-lifecycle-alpha.md), [agreed lifecycle boundary](../../delivery/booking-and-lifecycle-scope.md).
