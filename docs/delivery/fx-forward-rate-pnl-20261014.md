# Deliverable FX-forward rate-based P&L

Later correction follow-up: [historical cancel/rebook and explicit valuation reassessment](trade-corrections-valuation-reassessment-20261014.md) now verifies the corrected closure bridge without rewriting prior published values. Later-effective economic terminations remain unsupported. Operating migration 92/restart pending.

## Agreed calculation and implementation

Signed base notional × change in contract rate gives quote/trade-currency price
P&L. New executions start at their actual booked rate; retained maturity closure
uses the actual closing rate, including a sourced Ops override. Closure removes
exposure and does not create cash balances or currency payments.

Before maturity, selected observations must describe the specific canonical
contract, not a spot pair or monetary MTM. Series semantics: `FX_FORWARD`, `RATE`,
measure `FX_RATE`, RAW observation basis, BASE_CURRENCY / QUOTE_CURRENCY,
`RATE_BASIS=FORWARD_OUTRIGHT` and exact `MATURITY_DATE`. Policies select timed
contract rates with sealed calendars, governed source priority/rights, information
cutoffs and explicit freshness. Missing rates do not silently substitute spot.
The pricing-policy editor offers the contract-rate family separately from spot FX.

The reporting-currency bridge uses quote-to-strategy FX and retains price, FX and
cross components. It applies FX movement to net contract value, not gross currency
notional. Opening/closing value is the explicitly labelled **undiscounted
rate-difference value** `signed notional × (selected rate − frozen agreed rate)`.
This is not a discounted model MTM or complete NAV; no discount factor or curve
was invented. Period executions use the analogous rate difference. Thus a new
trade at agreed rate has zero starting contract value, while a maturity closing
entry realises the difference and leaves zero closing exposure/value.

For multi-day foreign-currency requests the existing daily bridges continue to
translate each day's execution economics at its own day-end FX. An unclosed
position beyond maturity blocks; date alone never extinguishes exposure. Cancelled
or superseded booking semantics and unsupported in-period corrections remain
governed by existing reconstruction rules.

## Boundaries and code

- `positions/fx_forward.py` validates frozen currency direction, agreed rate,
  obligations, approved definition and maturity-close evidence. New original
  bookings freeze valuation conventions. Legacy originals/closings without these
  conventions are accepted only with an exact unchanged current contractual
  fingerprint and compatible approved definition; changed legacy terms block.
- `valuation/forward_inputs.py` rejects spot/MTM observations, wrong currencies,
  maturity or basis. `valuation/position_calculation.py` applies rate-difference
  economics with Decimal precision; equity/fund/bond calculations remain unchanged.
- `valuation/service.py` selects and freezes rates and reporting FX. Closing spot
  provenance, when present, is retained as a suggestion separately from the booked
  execution rate and remains subject to evidence display permissions.
- `valuation/decisions.py` provides readable forward-rate, selection and maturity
  rules; staged lines retain the value-basis warning and source evidence.
- Existing staging, amendment, independent/self-publication policy controls,
  strategy scopes and current evidence permissions are reused without bypass.

Not supported: NDFs, FX swaps, automatic pre-maturity spot valuation, triangulation,
curve pricing, discounted MTM, cash movement accounting or payment recognition.
Real operating runs still need eligible contract-rate observations and matching
policy rules; Yahoo spot observations alone do not supply forward rates.

## Verification and activation

Focused tests cover signed long/short P&L, new trades, negative/zero net values,
manual maturity closes, inverse reporting FX, missing contract rates, wrong maturity
proof, actual frozen booking inputs, staging, reviewed amendments and publication.
All financial fixtures use owned disposable databases. No operating market data,
permissions, trades, cash balances or pricing policies are populated by this task.
No migration is required. Final verification/activation evidence is recorded below.

Final focused regression: 86 backend tests passed with nine existing dependency/
seed deprecation warnings; 14 frontend tests passed. TypeScript, OpenAPI consistency
and diff whitespace checks passed. Two older booking tests needed reconciliation
with current group/scoped authorization: unknown strategies raise PermissionError,
and changing a membership label does not remove an explicit TRADE_WRITE grant.
The denial fixture now uses a genuinely ungranted member; production authority
was not weakened. An earlier source-missing fixture attempted to delete a referenced
observation; it now retains published evidence and marks the test input ineligible.

The API was restarted to activate the implementation. Logs:
`logs/api-fx-rate-pnl-20261014.*.log`. No migration, grant expansion, operating
trade/cash mutation or live synthetic publication was performed. At initial
implementation handoff, no full-suite or browser financial acceptance had run.
The subsequent [end-to-end acceptance report](fx-forward-e2e-acceptance-20261014.md)
records successful disposable browser maturity/calculation and independent HTTP
publication, plus the remaining cancellation/rebooking valuation blocker.
Required operating contract-rate data and policy rules are not automatically
seeded by this implementation.
