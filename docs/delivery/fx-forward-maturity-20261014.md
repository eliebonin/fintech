# Deliverable FX-forward maturity

**Subsequent delivery:** [FX-forward rate-based P&L](fx-forward-rate-pnl-20261014.md)
now consumes these closing entries. Earlier valuation-blocked statements below
record the maturity-only checkpoint; discounted model MTM is still absent.

## Agreed scope

Ops-triggered maturity closure, following the bond workflow: DIRECT, REVIEW
(default, independent selected user and real operator), or source-confirmed MANUAL.
Close the actual remaining signed base-currency amount for each distinct contract.
One-click booking uses the maturity-date policy-selected quote-per-base spot rate;
late booking does not select today's rate. Prefilled/manual booking may use an
Ops-entered positive rate with a required source/confirmation reference and reason.
Suggested and entered rates remain separately retained. No silent rate fallback,
implicit stale-price allowance, NDF, early termination, currency delivery or cash mutation.

Retain source observation, date, policy/rule, source rights, selection cutoff,
contract terms, remaining exposure, preparer/reviewer and real-operator ancestry.
Revalidate before posting; unknown/changed inputs block. Idempotency prevents
duplicate closure. Linked cancellation preserves original bookings and audit.
Original physical obligations stay at the agreed contractual rate. Actual currency
movements live separately in cash snapshots or an explicitly supported cash flow.

## Implementation checkpoints

- [x] Test rate direction, signs, precision, exact maturity-date selection and
  rejection of missing/stale observations.
- [x] Retained processing policy with explicit pricing-policy/cut references;
  prepared inputs, independent approval, posting and cancellation.
- [x] Permission-aware Ops workspace and allowlisted BFF; explicit source evidence.
- [x] Disposable mock-booking API acceptance, focused regression checks and
  truthful capability documentation; operating activation separately authorized.

The existing valuation reader rejects FX-forward bookings. This maturity increment
must not remove that guard or claim full forward MTM/P&L support without explicit
forward-rate boundary inputs and correct two-currency/net-contract economics.
The agreed rate-difference intent is retained, not proof of delivered valuation.

## Implementation and boundaries

### Approved prefilled/manual-rate extension

Spot is a suggestion, not a counterparty-confirmed contractual closing rate.
DIRECT retains one-click Book now for an eligible maturity-day observation.
Ops may instead check an entered rate in the prefilled editor, with source/reference
and reason. The same path remains available when no eligible spot observation
exists; missing suggestions remain null with a warning, never zero or today's rate.
Rates must be positive, finite decimal strings within 18 integer / 12 decimal
digits. Direction, quantity, currency and economic date remain server-owned.

The retained inputs store `suggestedPrice`, `rateOverride`, `rateSource` and any
`rateSelectionError`, alongside source evidence and posting authority. Editing
disables preparation/booking until checked, so unchecked text cannot accidentally
book the old suggestion. The preview does not create a trade. REVIEW proposals
retain the chosen rate/source/reason; approval rejects any fresh rate override and
revalidates the retained proposal. Changing source selection or exposure invalidates
it even when the entered rate itself is unchanged. Existing prepared records from
before this input-shape change may need fresh preparation; none are rewritten.

This extension uses existing JSON evidence tables; no new migration or grants.
General FX-forward valuation and cash handling remain outside the scope.

Extension verification: 27 focused backend checks and seven frontend checks passed,
including the real API booking at entered 1.125 while retaining spot suggestion
1.12, manual closure with missing spot, retained independent-review rates, invalid
decimal/provenance rejection and bond regression checks. TypeScript and OpenAPI
consistency passed. One existing Starlette/httpx deprecation warning remains.
The local API was restarted to activate this schema-free extension; logs:
`logs/api-fx-manual-rate-20261014.*.log`. No operating grants, trades, cash balances
or pricing-policy settings were changed. Full-suite and financial browser
acceptance were not run; mock financial tests used a disposable database.

`lifecycle/fx_service.py` owns the canonical-contract exposure reader and maturity
workflow; `valuation.fx.resolve_fx` supplies existing licensed, policy-selected,
orientation-checked rate evidence. No new provider acquisition or FX interpolation.
The reader checks frozen original obligations/term fingerprints and retained
corrections. Existing delivery histories or changed contract terms require
reconciliation rather than double closure. It does not replace the valuation ledger
adapter or enable portfolio FX-forward valuation.

`MATURITY_CLOSE` is a dedicated rate-based closing trade with no settlement date.
Its quote equivalent is informational, not an automatically booked payment. The
original agreed rate/physical obligations remain unchanged. Closing quantity is
server reconstructed, never supplied by the browser. Cancellations are retained
corrections, not a market execution. Rebooking requires a new preview.

Each strategy configures mode and an active tenant/strategy-compatible pricing
policy version and its cut. Missing configuration blocks preview. FX source
evidence additionally requires MARKET_DATA_READ on the same strategy. Policies
can permit inversions, but there is no silent inversion, triangulation or prior-day
maturity fallback. Pricing targets later than the current economic cutoff block.
Independent approval rechecks current grants, input selection and remaining exposure.

The prepared fingerprint excludes only advancing `informationCutoffUtc` fields:
selected observations/rules/source priorities/calendar/rights facts still determine
staleness. Each preparation/post retains its actual information-cutoff evidence.
An initial test failure identified this distinction; it was corrected without
weakening rate/exposure revalidation.

UI: `/trades/lifecycle?product=fx-forward`; shared navigation links Bonds / FX
forwards. API: `/v1/lifecycle/fx-forward/options`, `/policy`, `/closures` and its
preview/prepare/book/approve/cancel/postings paths. The shared route/UI shell is
parameterized; product posting/ledger semantics remain separate. Table construction
is shared, but bond/FX policy/proposal/posting tables are separate, additive records.
No new implicit administrator grants or unattended scheduler.

Migration 91 adds FX policy/proposal/posting tables with append-only guards.
Migration 91 was applied with explicit user approval; the local API was restarted
with logs `logs/api-fx-maturity-20261014.*.log`. No operating grants, strategy
configuration changes or financial postings. Synthetic acceptance uses only the
owned disposable PostgreSQL runner.

Final verification: 33 focused backend tests and six frontend tests passed.
TypeScript, OpenAPI consistency and whitespace checks passed. Repeat TypeScript
contract generation is byte-identical; the repository's generate:check command
returns nonzero because it compares the intentionally uncommitted generated file
with Git HEAD, including unrelated pre-existing feature changes. No full suite ran.
Mock acceptance includes real initial FX booking, direct long/short closure,
independent review, changed-rate refusal, missing-rate refusal, cancellation,
idempotent retry and API strategy isolation. Bond maturity regressions also passed.
General FX-forward valuation remains explicitly blocked. Publication/financial
reconciliation and a full browser financial journey are not claimed by these tests.

Live browser smoke check confirmed the FX-forward maturity heading and Bonds / FX
forwards navigation render. The selected operating MEMBER correctly sees the
explicit LIFECYCLE_READ restriction and Groups link; no permissions were expanded
to bypass this check. The temporary smoke-check tab was closed afterward.
