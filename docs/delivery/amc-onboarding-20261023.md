# Native AMC onboarding, quotation and monetary measures

**Reviewed:** 23 October 2026. **Status:** Implemented; activation/evidence below.

## Intent

Keep `ACTIVELY_MANAGED_CERTIFICATE` distinct from FUND, FUND_SHARE_CLASS, ETI and
autocalls. Share security identity, units, dated prices and reporting FX; do not
force a fund-vehicle/share-class hierarchy. Issuer and adviser are separate roles.
Reference portfolio/index and venue listings are optional.

[Approved plan and research](../superpowers/plans/2026-10-23-amc-onboarding.md):
SSPA recommendations amended April 2025, BNP certificate prospectus May 2026,
SEC fund NAV guidance. Swiss guidance informs engineering, not universal legal
requirements or a claim of regulatory compliance.

## Workflow

1. Instruments → Create → AMC (`/instruments/amcs/new`). Search canonical issuer,
   choose currency/start, optionally adviser/reference portfolio/index.
2. Confirm quantity/price basis, divisor, minimum/increment, OTC permission,
   redemption/distribution and source. Unknown optional facts stay UNKNOWN/null.
3. Submit `CREATE_AMC`; Operations approves/rejects via existing reference review.
   Approval rechecks active dependencies and tenant-visible references.
4. Inspect the canonical certificate and AMC terms; add a listing separately if
   needed. Use Trade booking → Book AMC for listed or approved OTC execution.
5. Booking reuses governed annotations, consideration and frozen conventions.
   Retry keys/intent remain fixed on uncertainty. No cash-account entry is generated.

## Economics / limits

- Fully funded UNITS/UNIT_PRICE and percentage-of-par booking reuse exact existing
  arithmetic. Unit-counted percentage quotes require an explicit denomination.
- Listed AMC booking currently requires one certificate per listing unit; no
  unsupported listing-unit conversion is silently applied.
- Daily valuation and monetary preview support unit and percentage quotations:
  quantity × frozen multiplier × price ÷ divisor, with existing reporting FX and
  execution treatment. Unit-price multiplier is one. Percentage divisor is 100;
  certificate counts multiply denomination, nominal quantities do not. Identity
  stays AMC; daily applied rule `AMC_QUOTED_PRICE` explains the calculation.
- AMC observations require series dimension `AMC_PRICE_BASIS=UNIT_PRICE` or
  `PCT_OF_PAR`, matching every contributing trade's frozen quotation factors.
  Missing/conflicting semantics block; numerical price level never implies basis.
- All three monetary measures use the existing funded-security market-value proxy
  convention, not underlying look-through, risk exposure or contractual face.
  Local values survive missing reporting FX as LOCAL_ONLY, not false base zeros.
- Pricing frequency/publication lag do not default to fund NAV conventions and
  never override policy rules, actual price dates or information cutoffs.
- No generated fees, issuer-credit/collateral model, look-through, cash postings,
  redemption schedule or maturity closure. Known matured instruments reject new
  investment bookings; existing trades do not silently disappear.
- Convention amendments use the existing API. A dedicated AMC amendment UI and
  economic-terms revision workflow remain deferred; full AMC management F41 is
  not delivered by this onboarding slice. Missing prices/rights/calendars still block.
- Historical percentage bookings with incompatible/missing denomination factors
  remain blocked and need normal correction; old financial evidence is not repaired.

## Implementation

[Proposal](../../apps/reference_api/amc_contracts.py),
[creation/revalidation/inspection](../../apps/reference_api/amc_creation.py),
[booking](../../apps/reference_api/product_booking.py),
[audited routes](../../apps/reference_api/product_booking_routes.py),
[UI](../../apps/ops-console/src/components/amc-creation-form.tsx),
[tests](../../tests/test_amc.py),
[migration 97](../../alembic/versions/20261023_97_amc_terms.py).

`secm.amc_terms` contains typed effective-dated metadata. Issuer/currency stay on
the instrument; maturity on instrument dates; execution dimensions on approved
conventions. No historical financial evidence is rewritten. Routes retain current
reference/trading and strategy checks; private organisation labels/notes are not
copied. Creation grants neither counterparty eligibility nor provider rights.

## Reconciliation fixture

[Operator](../../tooling/reconciliation_csv/reconciliation_products.py) creates FCGMS source1857,
ISIN DE000A4AHQW5 through native AMC proposal/approval. The old ETI request remains
rejected with original payload. Issuer SUPER GLOBAL SEC SA is source-derived
operational identity, not an invented verified legal name or LEI. USD/unit quote
is sourced; start is first observed execution, not a confirmed issue date.
Minimum/increment 10^-12 and OTC permission are disclosed reconciliation settings,
not confirmed dealing terms. Unsourced adviser, security, distributions, redemption
and publication details remain unknown. Source trades/prices are unchanged.

## Verification / activation

Earlier scoped runs: 45 booking/readiness, 32 AMC/import and 30 frontend tests
passed; frontend typecheck clean. Final evidence is appended after completion.
No full suite, portfolio reconciliation or browser acceptance is implied.

Activation: migration `20261023_97` applied locally. Native FCGMS ID
`01a16852-f45d-738d-9995-6d0d5a1a523d` verified through canonical inspection:
AMC type, expected ISIN, unknown redemption. Operating trade count remains 46;
reconciliation strategy has zero trades. The existing app runs on API **8001**
and frontend **3001**; separate applications occupy 8000/3000 and were not stopped.

Final scoped verification: **48 backend tests passed** in 46.56 seconds in an
owned disposable PostgreSQL database; **32 frontend tests passed**, and frontend
typecheck passed. The final backend run covers native identity/ISIN replay and
duplicate refusal, other-tenant reads, stale issuer approval refusal, unit booking,
partial sale, retained valuation conventions, the hand-calculated 40-unit daily
P&L example, shared rule/product tests and reconciliation replay. The earlier
empty-read test failure used the host clock against database receipt timestamps;
the fixture now freezes its information cutoff from the database clock, without
changing production selection semantics. Logs: `logs/amc-final-focused.log`,
`logs/amc-frontend-final.log`, `logs/amc-typecheck.log`.

Live read-only smoke checks confirm new routes, canonical FCGMS detail and
`READY` booking status on API 8001; frontend creation URL returns HTTP 200 on
3001. API was restarted; no operating trade, price, balance or valuation posted.
Source/adviser/fee terms are not independently contractually signed off by these
checks. Final review was a separate self-review, not an independent code audit.

### Quotation/measure extension

[Plan and issuer research](../superpowers/plans/2026-10-23-amc-measures-percentage.md).
The Julius Baer AMC example establishes currency-per-certificate quotations;
the separately identified UBS non-AMC certificate illustrates percentage/denomination
dimensions only. Neither establishes the private FCGMS contract's missing facts.
Shared factors live in [amc_quotation.py](../../security_master_schema/amc_quotation.py).
**40 focused tests passed** in 82.36 seconds in a disposable database, covering
unit, percentage/certificate, percentage/nominal, local/reporting values, missing
FX, wrong quote basis and hand-calculated daily P&L. No migration, additional
browser acceptance or full portfolio reconciliation is implied. Evidence:
`logs/amc-measures-focused.log`. API activation is recorded separately.

Reconciliation follow-up now posts all 16 FCGMS executions via the native AMC
writer, retaining original prices and explicitly authorized truncation evidence;
see [current financial import counts and limits](fcagf-reconciliation-import-20261023.md#latest-committed-readback).
The earlier zero-trade activation count is historical, not current strategy state.

Activation follow-up: API8001 restarted with the quotation/measure and exact
swap-reference fixes; `/health` returned OK and frontend3001 `/select-context`
returned HTTP200. Other applications on 8000/3000 were not stopped. No new
migration, operating valuation or publication was required.
