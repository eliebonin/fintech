# Plain bond maturity redemption

## Approved design and implementation plan

Implement the agreed Ops-triggered lifecycle closing workflow, beginning with
full maturity of plain unadjusted-nominal fixed/zero-coupon bonds. Final principal
price comes from approved effective bond terms `redemption_amount_per_par` in
PCT_OF_PAR; missing/unsupported terms block rather than default to par or zero.
Partial calls, amortising/indexed/defaulted bonds and derivative maturity are
outside this increment. The notification dashboard and payment/accounting remain
deferred. Existing trades stay immutable.

Each strategy has an append-only BOND_MATURITY processing-mode policy, default
REVIEW. CONFIGURE changes require explicit scoped permission, revision, reason and
confirmation. DIRECT is an Ops click, not unattended scheduling. REVIEW prepares
immutable proposed inputs, then independent approval revalidates them before
posting. MANUAL requires the operator to confirm sourced terms, never arbitrary
price authority. Financial input changes invalidate prepared fingerprints.

Closing entries are `MATURITY_REDEMPTION` trades recognized on the maturity date:
past maturities use EoD UTC, while today's maturity uses the Ops action instant
(never a future execution timestamp),
with negative remaining long / positive remaining short nominal, one entry for
each compatible listing/canonical bucket. Booked convention and source-term
references are retained with actor/operator ancestry. The transaction locks the
strategy, rechecks exposure, prevents duplicate retries, and verifies zero after
posting. Correction uses TRADE_CORRECT and retained cancellation/rebooking, not
mutation of original purchase or publication. Payment date/cash receipts are not
asserted by this entry. Final interest still needs assessed daily-accrual inputs.

Execution: sequential in the approved current feature checkout, focused tests,
preserving unrelated changes. No live permission grants or synthetic financial
postings to operating data. Operating migration/restart requires activation
confirmation when the additive schema is ready.

1. [x] Pure closing-economics tests, subject-filtered position projection and
   candidate fingerprint; unknown price/units/terms reject.
2. [x] Immutable policy/proposal schema, permission-enforced prepare/book/approve
   and cancellation, idempotency, stale-source and duplicate guards.
3. [x] Ledger adapter and valuation acceptance: T closure reaches zero; correct
   signed redemption proceeds enter T bridge; no closing mark for zero exposure;
   final daily interest remains separately assessed.
4. [x] Strategy/instrument lifecycle workspace for preview, processing mode,
   prepared approval and Book now; frozen candidate fields are not browser-priced.
5. [x] Focused API/isolation/financial/frontend tests, generated contracts,
   capability updates and live activation without creating operating trades.

## Verification / remaining work

### Mock-booking acceptance — 14 October follow-up

Executed [the retained HTTP journey](../../tests/test_bond_redemption_journey.py)
against a newly owned disposable database with a synthetic 100,000-nominal bond
holding and distinct Ops/reviewer users. The fixture installs retained mock booking
evidence; lifecycle commands then use the real authenticated API routes, not direct
service calls. Verified strategy/bond selection, contractual price 100, default
REVIEW, preparation, self-approval denial, independent approval, idempotent retry,
BOOKED status and no remaining exposure. Cancellation retains evidence and reopens
the original holding; explicit DIRECT configuration and a refreshed preview allow
one new closing entry. Original purchase remains BOOKED; no settlement is asserted.

The HTTP journey and existing service/API/financial tests passed together: seven
focused tests. Financial checks confirm principal P&L 1,000 and staged gross P&L
1,010 including separately assessed daily interest 10. One initial test-fixture
cleanup failure was corrected: its committed synthetic pricing rule collided with
later rollback fixtures; cleanup now removes only that owned rule and restores the
shared synthetic instrument date. No application behavior was changed.

This is API/financial mock acceptance, not a full browser interaction walkthrough.
No operating trades, permissions or service configuration changed. The runner
removed its disposable database after the checks. FX-forward maturity remains a
separate next product slice; bond pricing assumptions must not be reused for it.

### Original delivery verification

Final focused verification: 43 backend tests passed in an owned disposable
PostgreSQL database, with one existing Starlette/httpx deprecation warning.
Four frontend tests across three files passed; TypeScript, OpenAPI consistency
and diff whitespace checks passed. Operating database reports migration 90 and
API health reports `ok`. No full-suite or operating financial browser acceptance
was performed. Next acceptance step is an Ops/reviewer walkthrough with explicitly
assigned strategy permissions and disposable sample holdings, not live grant
expansion or financial posting by this delivery task.

Delivered bounded alpha at `/trades/lifecycle`, linked from trade history for
users with LIFECYCLE_READ. Default REVIEW; DIRECT and MANUAL require explicit
configuration. MANUAL is source confirmation, not a general editable-price ticket.
Prepared fingerprints include remaining ledger exposure, source terms and policy
revision. Instrument/strategy locks, idempotency and current authority checks apply
to posting. Cancellation appends audit events and reopens exposure; refreshed
preparation/rebooking is required. Existing published financial evidence is retained.

Migration `20261014_90` was applied with explicit user approval on 14 October;
the local API was restarted. No operating grants, synthetic bookings, cancellations,
cash uploads or valuation publications were performed. Restart logs are
`logs/api-bond-redemption-20261014.*.log`.

Focused disposable-database checks cover signs/price units, permission/isolation,
independent review, stale inputs, duplicate replay, cancellation, immutable evidence
and actual maturity-date valuation. The full calculation/staging example closes
100,000 nominal at contractual 100 against an opening mark of 99: principal P&L
1,000 plus separately supplied final-day interest of 10 gives staged gross P&L
1,010 and zero closing nominal. It needs no closing bond mark. This is not a test
of coupon payment, accounting or final valuation publication.

Notifications/due-event discovery, partial redemption, amortization, indexed or
defaulted bonds, coupon generation, cash/payment settlement and other product
lifecycles remain deferred. Missing final-interest coverage still blocks valuation;
passing the principal workflow does not establish complete bond/fund NAV support.
