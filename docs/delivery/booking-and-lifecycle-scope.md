# Booking and lifecycle scope

**Date:** 2026-10-01  
**Status:** Agreed direction; listed option booking alpha delivered  
**Audience:** Product and engineering  
**Delivered slice:** [Listed vanilla option booking alpha](listed-option-booking-alpha.md)

## Decision

Continue extending product booking, starting with listed vanilla calls and puts with fixed strikes and upfront premiums. Preserve accurate economic semantics and the existing lifecycle extension points, but do not build settlement, position calculation or valuation as prerequisites. This is the project alpha boundary, not a universal market convention.

The user accepted this bounded approach after discussing option opening/closing, FX delivery, bond maturity and the risk of overbuilding. This record supersedes suggestions that opening/closing is an options-only feature or that comprehensive lifecycle processing must precede option booking. It does not supersede the delivered cash or FX booking contracts.

## Three separate concepts

| Concept | Meaning | Example |
| --- | --- | --- |
| Execution | The agreed transaction recorded in the ledger | BUY ten option contracts at an executed premium |
| Position effect | The intended effect on a position | Open a long, close a short |
| Lifecycle and settlement | Subsequent contractual events and fulfilment of obligations | Exercise, expiry, redemption, termination, currency delivery |

BUY does not necessarily mean open, and SELL does not necessarily mean close. A closing purchase reduces a short; a closing sale reduces a long. Opening/closing information is shared execution metadata, with requirements determined by product and market convention. It is not a substitute for settlement evidence, contractual termination or lot allocation.

An execution may cross zero and both close and open exposure. A later implementation must preserve source facts and represent mixed effects or split them explicitly; it must not infer a single label incorrectly. Existing historical trades remain unspecified rather than being silently classified. Capturing an OPEN/CLOSE designation does not prove that the position exists or that a contractual obligation was extinguished.

## Lifecycle examples and corrections

- **FX forward:** Keep the original execution. Delivery fulfils its currency obligations and changes cash holdings; it is not a fictitious opposite execution. An offsetting forward can neutralise market exposure while leaving both contracts' obligations outstanding. Actual termination is a distinct event.
- **Bond:** Settling a purchase leaves a bond holding. Selling is a new execution. Redemption affects the eligible holding and creates or fulfils a principal repayment entitlement; the final coupon is separately identifiable. Maturity does not prove payment, and default/delay must remain visible.
- **Option:** Paying the premium does not remove the option position. A closing execution, exercise and expiry are distinct events. Opening/closing applies to execution intent, not to whether premium payment succeeded.

Trade history must retain original bookings. Future position views must distinguish live instruments, amounts due/overdue and settled cash/security movements. A matured contract cannot disappear merely because its date has passed; nor should an unpaid obligation necessarily continue to be treated as an unchanged pre-maturity instrument. The precise position/accounting transition belongs to later lifecycle design.

## Foundations inspected before option implementation

The following inspection describes the starting point, not the final delivered state. The shared position-effect field, option proposal and product-specific booking path have since been implemented; see the linked delivery record and acceptance evidence.

Inspected source: `security_master_schema/models.py`, `apps/reference_api/fx_forward_booking.py`, `apps/reference_api/repository.py` and migration `20260901_09_trade_lifecycle_events.py`.

- `trd.trade` records signed quantities, strategy, subject, execution facts and attribution. Its vocabulary also anticipates REDEMPTION, COUPON and CASH_FLOW, but those labels do not establish working lifecycle workflows.
- `trd.trade_lifecycle_event` is linked through `trade_id` and has sequence, effective/recorded timestamps, source identifiers, actor, payload hash/payload and correction linkage. A database trigger prevents updates/deletes.
- The FX BOOKED event carries a versioned immutable economics snapshot, including expected receive/pay obligations. It is not payment confirmation.
- `trd.cash_account` exists. `trd.cash_balance` stores balance snapshots, explicitly not movements or per-trade settlement evidence.
- The current P&L query filters BOOKED trades and execution dates; it does not replay settlement/position-changing lifecycle events. Strategies containing booked FX are deliberately rejected by that cash-oriented calculation.
- No shared position-effect field, structured settlement-movement/allocation workflow or lifecycle-aware position engine was found in the inspected booking code.
- Existing option terms, instrument dates, contract-unit terms and listing quotation terms provide reference-data foundations. There is no standalone option-proposal route in the current reference API. The cash booking writer currently uses SHARES/UNIT_PRICE and must not be mistaken for option booking support.

The previous cash/FX sign-off remains a booking-alpha acceptance, not certification of outstanding positions, settlement or portfolio valuation.

## Approved option booking slice

Use Book trade from the menu with a distinct option product choice. Search/select an eligible approved option listing; do not launch booking from instrument detail as the sole entry point. Reuse tenant access, active strategies, parties, governed properties, tags, references, review/back-to-edit, idempotency and immutable trade history.

### Reference facts inherited by the ticket

Underlying, CALL/PUT, fixed strike and basis/currency, expiry and applicable trading cutoff, exercise style, exercise settlement method, premium currency/quotation convention, premium multiplier and contract deliverable. These belong to governed instrument/listing configuration, not repeated manual trade inputs. Required conventions must be explicit and effective-dated; missing or ambiguous facts block booking instead of defaulting a multiplier to 100 or 1.

Premium multiplier and exercise deliverable are distinct. Existing generic multipliers/quotation terms must be assessed for exact semantic fit before reuse; adjusted or multi-component deliverables are deferred rather than squeezed into one multiplier.

### Execution facts entered by the user

Strategy, BUY/SELL, positive integer contract count, executed premium, offset-aware execution timestamp, explicit premium settlement date and opening/closing designation for this listed-option slice. Existing operational metadata remains available. Position effect must be a shared first-class field, not a tenant custom property or a lifecycle status. Its presence outside options can remain optional; no compulsory change to old cash/FX tickets is approved by this record.

Review derives gross premium from count and the governed quote-to-currency conversion, and clearly shows payment for BUY or receipt for SELL before fees. For a supported monetary-per-point convention: ten contracts at USD 2.50 with multiplier 100 produce USD 2,500. Strike is not execution premium. Expiry/exercise settlement is not premium settlement. Do not copy the cash ticket's universal T+2 weekday default; initially require an explicit premium settlement date until a supported convention/calendar is implemented.

Persist CONTRACTS quantity semantics and an immutable versioned snapshot of terms, quote conversion, gross premium, direction and execution position effect. Authoritative submission must revalidate permissions, listing/terms eligibility and fingerprints. A stale or unsupported contract cannot create a partial booking. Opening/closing is recorded intent, not position verification or automatic contractual close-out.

### Delivery sequence and acceptance

1. Establish authoritative option eligibility and the minimum governed proposal/approval capability needed for real tenant-created options. Reuse existing option reference tables; no broad fund/future/swap onboarding expansion.
2. Define premium convention and position-effect contracts, migrations where required, and pure decimal/domain rules. Start with lightweight unit tests.
3. Add product-specific option search/booking endpoints using shared annotation persistence and tenant-scoped idempotency. Keep options out of the generic cash writer.
4. Add the option ticket, review/edit/retry behaviour, generated API contracts and precise history/detail labels.
5. Add robust API/component regressions: both sides and opening/closing values, premium conversion, permissions, hidden/inactive/unsupported terms, expiry cutoff, stale snapshot, duplicate/concurrent retry and annotation rollback. Freeze terms used for history even if references change later.
6. Run the full Python/frontend suites, type/contract/build checks and an isolated synthetic browser walkthrough. Include cash/FX regressions and no live trade mutation.

Option valuation remains unsupported in this slice. Do not allow the new bookings to acquire misleading totals through the existing cash-only P&L path; a fail-closed guard is a booking compatibility safeguard, not an option pricing implementation.

### Deferred scope

OTC vanilla options follow separately; the design must not require artificial listings for that later path. Also defer adjusted/multi-component options, dynamic strikes, barriers/exotics, futures-style premium settlement, spreads/packages, exercise/assignment, settlement feeds, cash postings, netting, lot allocation, position calculation, valuation, Greeks and margin/credit checks. Booking records an already-executed transaction and does not route an order.

## Later lifecycle module

Update 2026-10-06: [historical booking and record corrections](historical-booking-and-record-corrections-alpha.md) now implements bounded cancel/replace of erroneous alpha booking records. This is not contractual termination, settlement, exercise or position replay. The later module described below remains unimplemented.

Reuse the event history. Add typed obligations, position changes and confirmed cash/security movements when that module is approved. Preserve partial/failing settlement, effective versus recorded dates, correction lineage, tenant isolation and idempotency. A later allocation model must accommodate one event affecting multiple holdings/trades and one netted payment fulfilling multiple obligations; the simple forward's one-trade event is not a universal model.

Choose one authoritative posting path. Do not count a movement and an independently created generic CASH_FLOW/REDEMPTION trade twice. These are design requirements for future work, not an approval to create a parallel ledger now.

## Research and applicability

Sources read during the discussion on 2026-10-01:

- [FIX 4.4 PositionEffect, field 77](https://fiximate.fixtrading.org/legacy/en/FIX.4.4/tag77.html): opening/closing is distinct position metadata, described especially for gross/omnibus accounting. Does not require that all platform products expose it.
- [FINOS CDM event model, version 7.0.0](https://cdm.finos.org/docs/event-model/): executions, quantity changes, closure reasons and asset transfers are distinct; history is retained, and business events can affect multiple trades. Architectural reference, not a mandated database schema.
- [BIS consolidated guidance on foreign exchange risks](https://www.bis.org/committees/bcbs/basel-consolidated-guidelines/module/rma/20): final settlement must be confirmed/reconciled; obligation netting depends on enforceable arrangements. Supervisory guidance aimed at banks, used here to motivate accurate operational distinctions rather than claim tenant compliance.
- [OCC equity option specifications](https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications): standard US equity contract size and premium points illustrate multiplication. US-product conventions are not universal defaults for other venues or OTC options.
- [OIC opening and closing definitions](https://www.optionseducation.org/referencelibrary/faq/general-information): opening/closing purchases and sales have different position intentions.
- [OIC contract adjustment examples](https://www.optionseducation.org/referencelibrary/faq/splits-mergers-spinoffs-bankruptcies): premium multiplier may remain 100 while the deliverable changes. Supports keeping those concepts separate.
- [CME primer on margining styles](https://www.cmegroup.com/education/articles-and-reports/a-primer-on-margining-styles-for-options): upfront-premium and futures-style settlement differ. Older explanatory material, used for this structural distinction, not current product-specific calendars or margin rates.

The initial product restrictions, storage choices and delivery sequence are project recommendations accepted as direction, not universal requirements imposed by these sources. FpML pages attempted during option research were not retrievable and are not used as verified evidence here.
