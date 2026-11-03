# Fund unit transfers and reinvestment credits

**Status:** Bounded native implementation; local import acceptance recorded separately below  
**Content type:** Delivery record  
**Owner:** Trading and valuation engineering  
**Last reviewed:** 2026-10-30

## Purpose and boundary

Fund allocations, transfers and reinvested distributions can change units without
being an ordinary purchase at a zero execution price. The native
[`trading.position_movements`](../../trading/position_movements.py) command records
these as **TRANSFER** or **REINVESTMENT**, reusing approved fund listing/definition
validation, current tenant/action/strategy authority, governed annotations,
idempotency and caller-owned transactions/audit. No migration is required.

Ordinary cash purchases/sales still require a positive execution price, including
when called directly rather than through HTTP. Transfer quantities can be signed;
reinvestment credits must add units. Native quantity precision remains exact.
The stored source zero is accompanied by immutable `quantityMovement` evidence:
type, signed quantity, reason, policy-day-end recognition and income assessment.
It is not a price of zero used to create an investment gain. Position readers
validate the typed proof against the original trade and fund product.

This first command is internal to the domain. There is no new movement endpoint,
booking ticket or Excel template. Existing trade detail can display the records;
the ordinary erroneous-record cancellation path supports validated movements.
Purchase-ticket replacement is disabled: cancel an incorrect movement and submit
a new typed movement. No cash balance, payment or distribution is generated.

## Daily financial treatment

- The movement changes holdings from its effective valuation date.
- On that day, policy-selected closing NAV values the transferred/reinvested
  principal in the position bridge. Subtracting that principal excludes it from
  price gains. For example, receiving 10 units at a selected NAV of 12 introduces
  value 120 and principal 120, with market P&L zero.
- A transfer out still requires that day's NAV even if it leaves zero units.
  Offsetting source movements retain separate records.
- Reinvestment distribution income is **UNASSESSED** until separately evidenced.
  Its occurrence-day review carries an Attention item and partial completeness;
  it is not silently counted as zero or invented from the unit credit. This
  disclosure does not by itself block staging/publication. No automatic dividend
  record is created.
- Later valuations include historical movement units in opening holdings without
  repeatedly warning about an old credit. Each day in a multi-day calculation
  uses that day's NAV and FX for movement recognition.
- Intraday recognition is not defined by this first day-end convention. A
  calculation containing an in-period movement requires daily valuation. Missing
  policy NAV/FX still blocks the financial calculation; a source zero cannot
  substitute for a market input.

Applied rules and economic inputs retain the classification, recognition NAV,
signed quantity and bridge value for inspection. Existing authorization,
immutable staging, reassessment and publication controls remain in force.

## Source-specific exercise

The [FCPGF reconciliation](fcpgf-reconciliation-import-20261030.md) uses an optional
adapter under `tooling/reconciliation_csv`. Its owner-authorized best guesses are
not product classification rules or broker-confirmed events. CSV parsing,
recurring-date inference and customer data stay outside application packages.
Original source rows, precision deltas and classification reasons are retained
in scoped private evidence. The adapter calls the native command; it does not
insert positions directly or alter ordinary purchase validators.

## Verification and limits

Focused tests cover transfers in/out, historical opening holdings, net-flat
movement days, FX, product/quantity proof mismatches, authority before replay,
ordinary positive-price booking, native NAV selection, staging, cancellation and
the source adapter's classification. Verification passed **76** broader focused
Python regressions, then **22** final targeted movement/isolation/neutrality
checks (overlapping coverage), **5** UI eligibility tests and frontend
type-checking. The final targeted run includes exact maximum native quantity,
missing NAV/daily convention and a two-day same-currency example with different
NAVs: two units received at 100, one removed at 110, principal bridge 90,
closing value 110 and market P&L 20. Known dependency deprecation warnings remain.

Live acceptance booked all 28 authorized FCPGF rows as 12 transfers and 16
reinvestment credits. All 200 source fund rows across ten funds reconcile at
exact normalized native quantity precision; the other strategies' 162 trades
remain unchanged. At that acceptance, four unsupported rate-leg swap entries kept
the overall import partial; the subsequent [native rate-exchange delivery](rate-exchange-swaps-20261030.md)
resolved those four postings. Original source/assumption evidence and private
acceptance reports are retained; see the linked reconciliation delivery.
The API was restarted and API health/portal entry returned HTTP 200. A live
browser walkthrough of movement cancellation was not performed; its native and
UI eligibility paths are covered by focused tests. This is not full NAV,
tax-lot accounting, a general corporate-action engine or a historical distribution
income reconciliation. No operating valuation is published by this change.

## Guidance checked on 30 October 2026

The [GIPS firms handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/)
distinguishes external assets/flows from investment return. The
[SEC mutual-fund explanation](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-funds-etfs/mutual-funds)
explains reinvestment as acquiring additional shares from a distribution.
Using the selected day-end NAV and leaving unconfirmed income unassessed are
explicit project choices for this bounded implementation, not a GIPS compliance
claim or a verified interpretation of an external source's event codes.
