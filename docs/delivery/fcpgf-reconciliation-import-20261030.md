# FCPGF private reconciliation import — 30 October 2026

**Status:** Source rows posted: all 383 position entries and 1,002 RESET records. Pricing policy activated on 31 October; full financial acceptance is blocked on two missing opening forward marks.

This is an owner-authorised local reconciliation exercise under tenant one, for
the GBP strategy FCPGF at **20 October 2026**. It is not a supported upload format
or a new application subsystem. Source adapters and synthetic tests remain in
[optional tooling](../../tooling/reconciliation_csv/README.md). Original files,
row-level financial evidence and generated reports remain in ignored private
storage, with immutable database receipt and posting evidence. No valuation was
run or published during the 30 October import. The subsequent owner-requested
[31 October valuation attempt](fcpgf-valuation-attempt-20261031.md) is retained as
failed on missing source marks, with no staged or published financial result.

## Imported state

The strategy is displayed as **FCPGF — imported reconciliation**; its native code
is `RECON_FCPGF`. The partial-import label was removed only after every source
position row had a unique native posting. Posting completeness does not establish
full valuation or contractual-term acceptance.

| Input | Retained / posted result |
| --- | --- |
| Source files | All 20 CSVs plus a content-addressed manifest; includes the newly supplied bond schedule |
| Position entries | All 383 posted through native booking commands, including the owner-corrected fund price, typed unit movements and four rate exchanges |
| Position breakdown | 200 fund entries (172 dealings, 12 transfers, 16 reinvestments), 53 bond trades, 96 EQUITYOTC trades, 11 delta-one swap trades, 14 asset-swap trades, 8 FX forwards, 1 option |
| Dated RESET income | All 1,002 entries posted, date-only rather than cumulative exposure |
| Market prices | All 2,839 observations across 139 series, 21 September–20 October 2026 |
| FX | All 264 non-identity observations across 12 GBP/USD/EUR/JPY pairs; 88 identity rows validated without creating redundant series |
| Cash | All 174 exact-date snapshots across 9 separate account buckets |
| Daily interest | All 1,128 source trade/day rows aggregated into 462 bond/date/currency inputs |
| Bond schedules | All 180 source rows represented by 191 coupon/principal cashflows across 18 versioned schedules |
| Native posting check | 1,385 position/RESET records: 355 INVESTMENT, 12 TRANSFER, 16 REINVESTMENT and 1,002 RESET. All 383 source position identities map one-to-one to native trades; all 200 fund rows across 10 funds match exact native-normalized signed quantities |

There were no futures in this export. SGD cash is retained; no missing SGD FX
rate or other financial mark was invented. NT, IB/Misc and source wash/account
buckets remain separate. Coupon schedules are informative contractual evidence,
**not confirmation that payments occurred**.

## Terms and transformations

- All **65 current autocall swaps** are native SWAP instruments assigned the
  **EQUITYOTC** value in the governed source-product taxonomy. The funded reference
  is a separate structured-product instrument. The source omitted the payoff
  graph, so these underlyings explicitly carry **synthetic** single-SPX annual
  autocall terms, initial level 100, call barrier 100, with no KIP/coupon. Missing
  underlying maturity falls back to the associated swap maturity. These are
  disclosed placeholders, not verified confirmations or a payoff valuation.
  Supplied whole-swap marks and original trade economics remain distinct.
- Native asset swaps retain the sourced bond performance reference and the
  SONIA/SOFR funding reference/spread, with PAY direction for the source short
  bond leg. Original two-leg rows are retained. Signed quantities, including
  negative quantities, are preserved. Whole-contract marks are not multiplied
  again by the component signs or leverage.
- The four floating-versus-floating components use the native
  [rate-exchange variant](rate-exchange-swaps-20261030.md), retaining independent
  identities and whole-component bank marks. Their separate USD companion
  quantities establish the inferred USD-leg amounts; their own GBP quantities
  establish the booking basis. Day count, overnight compounding and quarterly
  reset details are disclosed completion assumptions; principal-exchange and
  exact observation conventions remain unassessed. The owner's bond-income
  clarification does not verify the earlier bond component's inferred
  gross-total-return profile. Existing marks and BOOKED evidence are retained;
  generated cashflows and underlying-risk interpretation require further terms.
- Bond quotes are owner-confirmed **CLEAN fractions of par**, converted ×100 to
  native percentage-of-par prices, with nominal unchanged. Existing matching
  tenant-private bonds are reused after currency, coupon and maturity checks.
  ACT/ACT variants and dealing-unit metadata are explicitly inferred local
  completion where the source is incomplete. Stale bond rows attached to
  source-classified funds are ignored for bond creation.
- **14 historical bond settlement-accrual amounts are estimates**, clearly
  labelled in booking comments/evidence and normalisation audit. They use sourced
  regular coupon terms at settlement and do not confirm actual cash, ex-dividend
  entitlement or inflation indexation. Other missing accrual fields on sourced
  zero coupon-rate trades are zero by the supplied rate, not by a missing-data
  default. These estimates need reconciliation before relying on settlement or
  accrued-stock history. Supplied daily interest remains separate.
- One Treasury-bill when-issued execution required an appended unchanged
  historical definition/terms/convention version. The actual issue date and
  settlement date were preserved; earlier definitions and booked evidence remain.
- Decimal normalisation truncates towards zero at native precision and retains
  original text and exact deltas. Two bond prices needed slightly fewer quote
  decimals for exact 12-decimal consideration, preserving nominal. There were
  47 initial investment quantity/price normalisations with nonzero truncation
  deltas; later correction/movement transformations remain separately retained.
- The SPX put reuses the existing same-tenant, previously reviewed standard
  contract/listing. Source quantity **45,000 units becomes 450 contracts ×100**;
  price remains 23.7, preserving gross premium 1,066,500 USD. The unused
  multiplier-one source placeholder was retired without deleting its evidence.
- FX-forward source quantity currency becomes native base currency; rates are
  GBP per unit of that currency, with no inversion. Original legacy currency
  labels remain in source evidence.
- Historical flow references without complete terms are non-tradable references,
  not newly bookable contracts. Missing numeric links on 71 RESET entries were
  resolved from their explicit source-comment contract codes; no amounts or
  payment confirmations were generated.
- Source-date-only price/FX timestamps are explicitly EoD buckets, not asserted
  fixing, exchange-close, NAV-publication or receipt times. The separate native
  fund NAV-date policy adapter is tested, but a full-portfolio valuation policy
  was subsequently activated for the 31 October attempt linked above; complete
  financial acceptance remains pending. File datasets retain the
  existing personal-use declaration model, without commercial/vendor clearance.

## Resolved rate-swap source exceptions

**ASWAP13, ASWAP15, ASWAP22 and ASWAP24** pay SOFR and receive SONIA/spread.
All four are now approved and booked through the native rate-exchange workflow,
not relabelled as equity performance references. Guarded completion appended a
sourced second definition on each original instrument. All four existing series
and **88 observations** have identical retained fingerprints before/after;
all **1,002 RESET records** are unchanged. Repeating the import returned the
same four booking identities without duplicates. The two priced components of
each arrangement remain separate; no aggregate package price or netting is added.

## Owner-resolved fund exceptions

The owner authorized the best-guess interpretation of the **28 zero-price fund
entries**. All are now booked through the separate
[native fund-unit movement command](fund-unit-movements-20261030.md):

- **12 TRANSFER** entries: initial allocations, the seven distinct 30 June 2021
  offsets/rebookings, and later reductions. Offset rows remain separate, including
  the two distinct same-sized source reductions; no deduplication by likeness.
- **16 REINVESTMENT** credits: the recurring positive unit additions on six dates
  between December 2021 and May 2023.
- Original dates, zero source prices, signed units and precision deltas remain
  retained. Each booking discloses owner-authorized inference, not broker-confirmed
  classification. Ordinary purchases still require positive prices.
- The movement changes units without generating cash, a purchase gain, a
  distribution payment or inferred income. Daily recognition uses policy NAV;
  unassessed reinvestment income is explicit when valuing its occurrence day.
  Historical movements contribute to later opening holdings normally.

All **10 source fund positions**, including the six affected by these movements,
now reconcile to all **200 source fund rows**, at exact retained native precision.
The other strategies still contain 162 trades; no unrelated trades were changed.

The original **one negative-price fund entry** was resolved on
30 October by explicit owner instruction to book it with a positive price.
The source price remains unchanged in the retained CSV. Native booking retains
the negative quantity and original execution/settlement dates, with the sign
correction, precision normalisation and owner instruction recorded in audit.
That earlier correction added one fund execution. The subsequent 28 native
movements originally left four rate-leg swaps unposted; the native rate-exchange
follow-up resolved those final entries. No operating valuation was run or
published by these follow-ups.

All source position rows are now represented; inferred terms and precision
transformations remain disclosed rather than asserted as confirmed contracts.
No total FCPGF P&L, cash/accrued reconciliation or full-NAV accuracy claim follows
from the native posting check. A coupon schedule alone also does not establish
paid coupons or a complete opening accrued balance; full daily history or
assessed opening anchors may still be needed for accrued-balance FX.

## Verification and operator evidence

Focused tests cover identifier-based FX files, optional detail receipts, original
bundle identity preservation, native private-fund buy/sell/replay, nonpositive
fund-price exceptions, synthetic autocall validation, whole-swap mark units,
EUR/GBP forward orientation, signed settlement-accrual estimates, NAV-date policy
construction, and same-tenant standard-option reuse. The final owned-disposable
run passed **76 tests**: the 70 optional-tooling tests plus boundary/neutrality
checks. The redacted source-secret scan and whitespace checks also passed. No
full Python/frontend suite was run for this isolated tooling change.

Private reports are retained beside the manifest as `instruments-report.json`,
`derivative-bookings-report.json`, `product-bookings-report.json`,
`fund-bookings-report.json`, `datasets-report.json`, `acceptance-report.json` and
`finalize-report.json`. Source IDs, raw financial rows, quantities, precision
deltas and exact missing entries are available there and in scoped audit events.
The initial acceptance/finalisation reports retain their original 33-exception
snapshot. `owner-positive-price-correction-20261030.json` and a subsequent
import-status audit record retain the correction and then-current count of 32.

The subsequent `unit-movements-report.json` retains all 28 native identities and
the 12/16 classification. `unit-movements-acceptance-20261030.json` records exact
quantity/row reconciliation for all ten funds, validated frozen movement proofs,
1,381 native records and four remaining source exceptions. A new append-only
import-status audit records that state; earlier reports retain their original
dated snapshots.

The native extension separately passed 76 focused Python regressions, then 22
final targeted checks (including exact maximum-precision transfer, distinct
daily NAVs, tooling isolation and repository neutrality), five UI eligibility
tests and frontend type-checking. Counts overlap rather than representing 98
distinct tests; see its linked delivery.
The rate-exchange follow-up passed **173 focused Python regressions** and **7 final
integration checks** (overlapping coverage), including real HTTP propose/approve/
book/cancel, independent component staging and changed currency-role refusal.
Frontend checks, type-checking and browser evidence are recorded in its
[delivery](rate-exchange-swaps-20261030.md). The private
`rate-swaps-acceptance-20261030.json` records 383 unique source postings,
1,385 total records, unchanged prices/RESETs and the other strategies' unchanged
162 trades. `rate-bookings-report.json` retains the four native identities;
append-only status is `SOURCE_ROWS_POSTED`. Earlier reports remain dated history.

The local API was restarted and API health/portal entry returned HTTP 200.
No migration, new movement endpoint/ticket, permission grant or source-value
rewrite was needed. The application does not import or start these operators.
