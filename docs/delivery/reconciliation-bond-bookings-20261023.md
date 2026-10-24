# Private reconciliation bond bookings — 23 October 2026

**Classification:** One-off external CSV reconciliation exercise, not product
functionality. Scripts and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md). Retained data and
audit evidence are unchanged; this record does not establish a supported upload
format or processor.

**Status:** Implemented and locally activated; full portfolio valuation not signed off  
**Content type:** Delivery record  
**Owner:** Trading and security-master engineering  
**Last reviewed:** 2026-10-23

## Authorized scope

Import the 13 FCAGF bond executions into the existing tenant-one reconciliation
strategy. The owner explicitly confirms all execution prices are **CLEAN** and
that source fractional quotes convert to native percentage-of-par prices ×100.
Nominal quantities are not contract counts and must not be multiplied by par.
The original exports remain unchanged; normalized values and exact precision
deltas accompany each native booking's retained evidence.

## Mapping and boundaries

- [Bond adapter](../../tooling/reconciliation_csv/reconciliation_bond_postings.py) completes only
  source-bound approved private GBP/GB bonds; the local operator adds `--book-bonds`.
  No generic public amendment/upload interface is implied.
- DMO guidance confirms conventional gilts and Treasury bills transfer in penny
  nominal units. This disambiguates source `par_amt=0.01`; it is used for the
  explicit nominal unit and dealing increment, never as a quantity multiplier.
  Source `bq_face_amt=1000` is not silently substituted for actual booked nominal.
- Existing bond terms are versioned, not silently overwritten. Earlier proposals
  and terms remain retained. Metadata completion refuses already-booked subjects;
  repeat preparation checks exact retained terms/definition/convention snapshots
  and refuses governance drift rather than repairing it.
- Source execution can precede issue date. The canonical definition and terms
  become applicable from the first evidenced execution, while actual issue date
  is unchanged. Settlement cannot precede actual issuance. This is historical
  reference validity, not an invented issue date or a global booking-date bypass.
- Native booking conventions are submitted/approved through existing services:
  NOMINAL, PCT_OF_PAR, divisor 100, MANUAL_CONFIRMATION, OTC, penny increments.
  All usual tenant, strategy, source, fingerprint and economic validators remain.
- Source settlement accrual is a signed cash-flow amount. For a BUY the native
  consideration adjustment is its negative; for a SELL it has the same sign.
  This preserves ex-dividend negative accrued instead of applying `abs()`.
  Missing fixed-coupon accrual blocks; missing zero-coupon accrual is explicitly
  zero by contractual coupon type. These are settlement amounts, not new daily
  earnings or cash balance entries.
- Decimal conversion uses the owner's later truncation-toward-zero policy at
  12 decimal places. The earlier `percentage_price` half-even preparation helper
  remains historical mapping evidence, not the financial posting path.
- The normal product writer creates frozen BOOKED economics and valuation
  conventions. Source IDs, hashes and replay checks prevent duplicate postings.
  Prices, coupons, cash balances and daily-interest inputs are not changed here.

## Definition transition safeguard

Disposable testing exposed an existing conflict: the database prohibited updating
any definition-version field, including retiring `is_current`, while requiring one
current approved version. Migration 98 permits only true-to-false retirement with
status APPROVED → SUPERSEDED, without changing old economic contents, and requires
a newer sourced approved current replacement by transaction completion. Existing
approved-period exclusion and unique-current constraints are unchanged. No trigger disabling, deleted
definitions or fabricated duplicate canonical instruments is acceptable.

## Research evidence

Reviewed 23 October 2026, primary sources:

- [DMO — About Gilts](https://www.dmo.gov.uk/responsibilities/gilt-market/about-gilts/):
  percentage-of-£100 nominal quoting and penny transferable units.
- [DMO — About Treasury Bills](https://dmo.gov.uk/responsibilities/money-markets/about-treasury-bills/):
  zero-coupon government obligations, penny transfer units, tender/settlement timing.
- [DMO glossary](https://dmo.gov.uk/help/glossary/): when-issued trading distinguishes
  execution from later issue/settlement.

These support conventions, not independent certification of every supplied trade
or an assertion that auction minimum sizes apply to all secondary-market trades.

## Verification and activation

Migration **20261023_98** was applied to the local app database. No API restart
was required: the changed booking adapter runs in the local operator, and database
guards take effect immediately. The API health check returned OK.

**13 source bond executions across 10 instruments are BOOKED**, with net signed
nominal **GBP 11,000,000**. FCAGF now has **77 investment trades** (64 previous plus
13 bonds); the 38 dated RESET flows are separate, not investment positions.
The repeat operator returned **0 booked / 13 replayed / 0 failed**. Independent
database readback checked every source quantity, converted CLEAN execution price,
settlement date, separate accrued amount, clean/dirty consideration and frozen
bond valuation conventions. Every original source trade row matches its retained
audit evidence. Nothing was imported as a dirty execution price.

**27 focused tests passed in 10.97 seconds**, covering the new adapter, source
bond mapping, existing investment mapping, bond arithmetic, repository neutrality
and guarded definition retirement. The final adapter-only rerun passed **5 tests
in 5.11 seconds**, recorded in `logs/reconciliation-bond-final-adapter-tests.log`. Native bond HTTP checks also
passed within an earlier broader focused run which exposed the subsequently
fixed definition-period transition failure; that earlier run was not wholly green.
No full suite was run. Evidence:
`logs/reconciliation-bond-final-tests.log`, `logs/reconciliation-bond-migration.log`,
`logs/reconciliation-bond-apply.log`, `logs/reconciliation-bond-replay.log`.

The operator's `sourceResetFlowsExcludedFromThisBatch=193` counts original RESET
rows outside this bond batch, not outstanding flows: 38 were already posted and
155 remain unresolved. One option execution and 884 price observations remain
outside this import. No cash balances, daily-interest inputs, coupon confirmations
or financial valuations were generated or published. No full strategy valuation,
browser acceptance or external reconciliation sign-off is implied by booking.
