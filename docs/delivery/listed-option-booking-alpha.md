# Listed option booking alpha

**Date:** 2026-10-01  
**Status:** Implemented; activated in the local operator database with a recoverable backup  
**Scope:** Listed fixed-strike vanilla CALL/PUT, American/European, upfront premium

## Current assessment

The core process is accepted for the agreed listed vanilla booking alpha: governed creation and approval, separate listing approval, product-specific execution capture, exact premium conversion, review/retry and immutable history. It is not a complete options platform or a production-deployment sign-off. The subsequent booking/UX cleanup was approved and implemented on 2026-10-01.

Completed checks include 431 passing Python tests, 277 passing frontend tests, typecheck, production build and API contract export validation. The isolated browser cycle covered creation, both approvals and BUY/OPEN and SELL/CLOSE bookings. Exact evidence, final focused rerun and verification caveats are retained in the [quality review](quality-reviews/2026-10-01-option-booking-alpha.md).

## Delivered workflow

1. Instruments → Create instrument → Option: propose governed underlying, strike/currency, effective and expiry dates, offset-aware last-trading instant, exercise style, exercise settlement, deliverable units and premium multiplier/currency.
2. Instrument Requests: an authorised tenant administrator reviews and approves CREATE_OPTION. The economic instrument remains separate from its listing.
3. Instrument detail → Add listing: retain the parent context; propose venue, symbol, quotation currency/factor and unit convention. Approve the listing in Operations.
4. Book trade → Listed option: search eligible approved listings, select an active tenant strategy, BUY/SELL, OPEN/CLOSE, positive integer contracts, executed premium, execution timestamp and explicit premium settlement date. Shared parties, properties, tags, references and notes remain available.
5. Review, return to edit or confirm. Trade history/detail presents immutable booking economics and audit evidence.

OPEN/CLOSE is shared first-class execution metadata, optional outside this option ticket. Existing cash/FX tickets and historical records are not silently reclassified. CLOSE records intent; this alpha neither verifies holdings nor allocates lots, terminates a contract or posts settlement.

## Economic conventions

Gross premium = contracts × executed quoted premium × governed premium multiplier ÷ listing quote factor. Calculation is exact decimal arithmetic; unsupported precision/range fails rather than rounding silently. BUY means PAY and SELL means RECEIVE, before fees. Zero premium is supported; negative premiums and fractional contracts are not.

Ten contracts at 2.50, multiplier 100 and quote factor 1 produce 2,500 currency units. A minor-unit quotation of 250 with factor 100 produces the same result. History labels quoted premium explicitly; the quoted number is not itself the currency amount. Premium multiplier and exercise deliverable are separate facts. Strike is not premium; premium settlement is not exercise settlement or expiry.

Premium settlement has no guessed T+2 default. The ticket requires a real ISO calendar date on or after the UTC execution date. Execution requires an offset, an effective contract and an instant no later than the explicit trading cutoff.

## API, storage and safeguards

Migration `20261001_55_option_booking_conventions` follows revision 54. It adds nullable `trd.trade.position_effect`, option premium multiplier/style and last-trading timestamp. Unknown legacy terms remain unknown, not backfilled with guessed conventions.

Product-specific API routes provide option listing search/detail, option proposal and option booking. The frontend proxies use the selected server-side tenant context. Related underlying search, listing proposal and proposal review proxies were corrected to use that same context rather than the default demo tenant.

The option writer rechecks permissions, active strategy, tenant reference visibility, effective approved definitions, underlying, venue, currencies, quotation/unit conventions and term fingerprint under locks. Unsupported or ambiguous facts block booking. The cash writer explicitly rejects derivatives requiring product-specific booking. Option quantities use CONTRACTS and prices use OPTION_PREMIUM; the ledger retains signed quantities and history presents side separately from positive contract count.

Tenant/endpoint-scoped idempotency supports duplicate and concurrent retries. The UI freezes payload, tenant and key for uncertain submissions. Committed replay returns the original booking before evaluating changed reference terms. Conflicts and stale terms do not create a partial trade; annotations are transactional.

A versioned append-only BOOKED event freezes option terms, quotation conversion, gross premium, direction, fingerprint and position effect. History reads that snapshot instead of reconstructing old economics from mutable current references. The existing cash-oriented P&L path rejects strategies containing booked options; this is a compatibility guard, not option valuation.

## Restrictions and deferred work

Supported underlyings are governed active equity/ETP instruments and indices; index options require cash exercise settlement. One fixed deliverable and explicit supported conventions are required. No artificial OTC listing or broad derivatives engine was added.

Deferred: OTC/exotic/dynamic-strike options, adjusted baskets, futures-style premium, packages, lot allocation, positions, exercise/assignment, expiry processing, confirmed settlement, cash postings, netting, valuation, Greeks and margin/credit checks. Booking records an already-executed transaction; it routes no order.

The former mock-sidebar and option-term inspection gaps were addressed in the approved cleanup below. This does not expand product eligibility or add a lifecycle engine.

## Completed booking and UX cleanup

- Trade detail now uses “Option · booking snapshot”. Individual premium fields retain their precise labels.
- Option instrument detail exposes current underlying, strike/basis/currency, expiry/cutoff, exercise/settlement conventions, deliverable, premium currency/multiplier/style and listing quote factors. Exact decimals are preserved. Missing/ambiguous facts are explicit, hidden underlyings are not disclosed, and current reference facts are distinguished from immutable booking snapshots.
- Instrument detail requests use the selected tenant, not the demo default. Legacy pages without explicit server workspace props inherit verified context through the existing session endpoint. While unavailable, the sidebar displays no invented tenant identity or module grants; obsolete responses are discarded on navigation.
- An instrument without a listing is labelled “No listing attached”, not automatically OTC.
- Cash search and preselected cash routes exclude OPTION, FX_FORWARD, FUTURE and SWAP, matching the authoritative cash-writer boundary. Product-specific tickets remain separate.

Automated cleanup verification: 290 frontend tests across 80 files; typecheck, production build and contract export validation passed. Option/instrument API checks passed 34 tests, including hidden-underlying privacy and missing conventions. Migration reconciliation and upgrade/downgrade checks passed seven tests. The earlier 431-test full Python result remains historical; the complete Python suite was not rerun for this cleanup.

## Remaining booking and UX work

These remain follow-ups after the implemented cleanup.

- **Position intent clarity:** The ticket, review and history already warn that OPEN/CLOSE is intent, not position verification. Validate the wording and prominence with realistic user walkthroughs. Do not imply that CLOSE proves a holding exists or prevents over-closing. Mixed close/open executions currently require separate bookings; automated splitting and allocation are not implemented.
- **Ticket density:** Walk through realistic tickets with parties, governed choices, numeric properties, tags and references before deciding further layout changes. End-to-end correctness does not settle the density/usability balance.
- **Browser regression follow-up:** A full synthetic cash booking now passed search, selection, review/back-to-edit, confirmation and persisted history, including a numeric property of zero. The cross-product FX discard check remains blocked by the embedded browser's native dialog handling: input times out and its dialog API reports no dismissible dialog. Do not label this browser check passed. Additional automated tests cover the actual guard's cancel/confirm branches; a manual operator check is still required.

The remaining usability assessment requires realistic walkthroughs. Positions, settlement and valuation are not prerequisites for this bounded booking alpha.

## Later modules requiring separate approval

- **Positions and allocation:** Determine actual open exposure, allocate closing executions and handle mixed effects. Recording OPEN/CLOSE alone does not implement this.
- **Lifecycle and settlement:** Record exercise, assignment, expiry, termination and confirmed premium/security/cash movements with correction lineage. Passing maturity/expiry is not proof of settlement, and delivery must not be manufactured as an opposite execution.
- **Additional product conventions:** Design OTC options, adjusted/multi-component deliverables, futures-style premiums and packages separately, without forcing them into the current listed ticket.
- **Valuation and risk:** Design option market-data semantics, valuation, P&L, Greeks and margin/credit checks later. The present P&L rejection is protective, not a pricing implementation.

These modules are deliberately outside current booking acceptance. The next user-facing step is an operator walkthrough of the activated local app, not silently expanding into valuation or settlement.

## Verification and rollout

See [dated quality review](quality-reviews/2026-10-01-option-booking-alpha.md) for tests, synthetic browser evidence and limitations. Implementation is uncommitted on the current feature branch alongside preserved earlier work; no merge or push occurred.

The local operator database `fortem_secm` was backed up before activation to `C:/Users/forte/Documents/ChatGPT/Tech V2/local-db-backups/fortem_secm_pre_option_cleanup_20261001.dump`. It was at revision 53 but already contained the two revision-54 bond fields. Revision 54 now reconciles only exact compatible types, nullability and defaults, updates comments without changing values, and refuses incompatible definitions; no blind revision stamp or column deletion was used.

The additive upgrade reached revision 55. Record counts stayed at nine trades and 271 instruments. API/frontend are served locally on ports 8000/3000; browser submission regressions use the separate synthetic database on 8001/3001. No synthetic acceptance bookings were copied into the operator database. A fresh process-only tenant-cookie secret requires selecting the tenant again; no credentials were committed.

Local API health and frontend tenant-selection requests returned successfully. After the user closed the blocked synthetic tab, the operator browser selected the tenant, loaded Strategies and opened the creation picker with the correct verified tenant/module context. The synthetic native discard-dialog check remains separately limited; it is not a passed user walkthrough of that guard.

Research and accepted design rationale remain in [Booking and lifecycle scope](booking-and-lifecycle-scope.md#research-and-applicability). Those sources inform the distinctions; alpha restrictions and storage choices are project decisions, not universal market rules.
