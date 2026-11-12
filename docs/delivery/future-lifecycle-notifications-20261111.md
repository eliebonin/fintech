# Futures lifecycle notifications and inspection — 11 November 2026

## Delivered workflow
Open `/lifecycle`, choose **Futures milestones** or **All events** and apply strategy/instrument/date filters. Rows represent distinct sourced milestones, even when several share a date. **Inspect future** opens the existing focus-preserving drawer, with signed contracts, gross opposing allocations, quote currency, family/contract month, settlement method, multiplier, dates and collapsed source evidence.

Under **Strategy → Overview → Lifecycle assistance → Futures milestones**, explicitly select manual0 or notifications1. The existing subscription ceiling, LIFECYCLE_READ/CONFIGURE actions and strategy scope still apply. No positive setting or grant is provisioned. Tier2/3 processing is not implemented for futures and cannot be selected via API or database. Reviewed downgrade previews preserve lower valid choices; highest-available respects the per-event maximum, while explicit unsupported replacements are rejected rather than silently changed.

The read model never prepares, posts, rolls, delivers, pays, updates cash, calculates variation margin or runs valuation. An overdue milestone means current open ledger contracts need attention; it does not establish settlement failure or an unpaid amount. Flat positions disappear without a settlement claim. Separate nonzero allocations remain visible at aggregate zero. Missing evidence is unknown/blocked, never a fabricated zero.

## Dates and source boundaries
- Approved `FutureConvention.lastTradingAtUtc` uses the exact timezone-aware instant, normalized to UTC. Before it the cutoff is upcoming, at it due, and afterwards overdue.
- `instrument_dates.expiry_date` is separate and optional; it is never inferred from contract month or last trading.
- Approved final settlement and physical delivery start/end remain distinct date milestones. A date alone does not assert an intraday cutoff.
- **First-notice dates are not stored in the current convention model.** Inspection explicitly says Not recorded and advises checking exchange/broker deadlines. There is no fabricated first-notice event or claim of complete deliverable-contract alert coverage. Adding governed first/last notice and broker-specific deadlines remains follow-up work.
- Current versus original frozen last-trading, settlement, delivery and economic convention conflicts block the affected event for source review. The drawer rejects revised source fingerprints and asks to refresh Lifecycle. It does not rewrite original BOOKED evidence.
- Current-ledger discovery is not a historical entitlement, broker-position or settlement reconciliation. There is no persisted task acknowledgement/assignment queue, email scheduler or automatic deadline ingestion.

## Implementation and data
[Domain reader](../../lifecycle/worklist_futures.py) scopes canonical/listing candidates before rebuilding current immutable ledger and joint allocation evidence. Current approved conventions are read in batched queries. Shared worklist applies relevance/status filters, full-population counts and pagination after combining supported event types. Lazy [GET adapter](../../apps/reference_api/lifecycle_worklist_routes.py) rechecks strategy authority, subscription, selected notifications and reference/source context. The BFF requires the expected-tenant guard, forwards only allowlisted inputs and exposes no futures POST. Workload admission classifies inspection as a lifecycle read.

[Migration113](../../alembic/versions/20261111_113_future_lifecycle_notifications.py) extends the retained assistance CHECK constraint only; no new financial table, data backfill, permission, subscription or strategy default is created. Approval conventions/common dates are reused without mutation. Existing bond/FX native processing and coupon-only inspection retain their boundaries.

## Verification and activation
- **Backend:** 76 tests passed in the bounded futures/bond/FX/coupon/worklist, transition, API-scope and admission group. Further futures runs passed cancellation, selected-read scope, unsupported-tier database enforcement, case-insensitive UUID/literal search and full-population pagination. The last pagination fixture was corrected to use native bookings with each strategy's own retained profile evidence; the focused test passed with 27 synthetic strategies. The product FK/authority guards were not weakened. These runs overlap; their counts are not added as independent tests.
- **Frontend:** 37 focused frontend/BFF/help tests passed. TypeScript and OpenAPI export checks passed. Generated TypeScript reproduced byte-for-byte. The Git-based generation check reports the intended uncommitted schema difference; independent regeneration verified the actual generated content.
- **Browser:** 14 mounted Edge journeys passed across futures/coupon/FX inspection, assistance settings and the existing maturity drawer. They check read-only futures controls, changed source rejection, short-contract formatting, mobile containment, Escape/focus return, subscription versus supported-tier messaging and existing native closing/retry behavior. Desktop/mobile screenshots were inspected; the final two futures journeys passed again after screenshot capture. These use mounted components and mocked HTTP; no claim of a new full-stack financial futures posting is made.
- **Local activation:** additive migration113 applied to the existing local database; before/after retained trade, lifecycle-assistance, subscription and access-audit row counts matched. Only the verified task-owned fintech API8000 was restarted. Live OpenAPI exposes the GET inspection and futures selection; frontend3001 is healthy. No grants, positive strategy selections, financial postings or Toolhive changes were made.
- No full project regression suite was run. Existing SQLAlchemy/Starlette dependency deprecation warnings remain outside this feature. First-notice/broker data coverage and futures financial processing remain explicitly deferred.

## Research and applicability
Reviewed 11 November 2026; online pages were opened and read.

- [CME expiration and settlement](https://www.cmegroup.com/education/courses/introduction-to-futures/get-to-know-futures-expiration-and-settlement) distinguishes cash/physical contract outcomes. Applied by keeping notices separate from financial effects.
- [ICE WTI expiry calendar](https://www.ice.com/products/213/WTI-Crude-Futures/expiry) publishes last trading, notice, delivery and final settlement separately. This is a concrete product example, not a date formula for all futures.
- [CFTC glossary](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CFTCGlossary/index.htm) distinguishes first notice and notes commodity/exchange variation. Applied by disclosing the absent field rather than substituting delivery start.
- [WAI modal-dialog guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) supports contained focus, Escape and focus return. The existing native modal is reused.

The independent selection, notifications-only first release and date-only due-day behavior are explicit project decisions, not regulatory mandates. No financial method or settlement automation is signed off by these references.
