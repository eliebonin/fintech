# Directly held structured-note P&L — 28 October 2026

**Status:** Implemented; verification and activation recorded below.  
**Capabilities:** F15, F37, F38, F39.  
**Scope:** Vital supplied-mark valuation run. Lifecycle automation remains deferred.

## Delivered economics

Fully funded structured securities use their supplied **whole-note** marks. The
existing security bridge values opening/closing holdings and subtracts signed
period executions, then decomposes price, reporting FX and their interaction.
It supports longs/shorts, additions, partial/full ordinary sales, new holdings
and confirmed zero marks. Unknown prices remain missing inputs. Neither
underlying returns nor embedded leverage are multiplied again.

- Nominal / percentage price: `nominal × price / 100`.
- Units / percentage price: `units × frozen denomination × price / 100`.
- Units / monetary price: `units × price / frozen quote divisor`.

For example, 100,000 nominal at 98 then 99 earns 1,000 locally without trades.
Selling 50,000 at 98.5 on the second day leaves 750 local P&L. A complete sale
still earns P&L that day and needs no invented closing mark for zero exposure.

Original PRODUCT_BOOKING contexts are normalized only when their fingerprint
uniquely binds retained definition, convention, structured-terms and optional
listing/venue identities. Existing trade/evidence records are not rewritten and
today's multipliers do not replace booked factors.

## Quotation and income

The approved convention explicitly states `CLEAN`, `DIRTY` or existing `NONE`
(no separate accrued convention). Governed RAW whole-note series use:

| Dimension | Values |
| --- | --- |
| `STRUCTURED_PRICE_BASIS` | `PCT_OF_PAR` or `UNIT_PRICE`, matching execution |
| `STRUCTURED_ACCRUAL_BASIS` | `CLEAN`, `DIRTY` or `NONE`, matching execution |
| `QUOTE_FACTOR` | Exactly one numeric divisor equal to the frozen convention |

MARK or CLOSE families can be selected with the existing explicit/session
calendar, source, licensing and information-cutoff checks. Adjusted share-price
conversion is not a note-pricing method. A different CLEAN/DIRTY basis needs
assessed conversion evidence; this slice does not guess or relabel it.

CLEAN bookings can retain optional total signed accrued interest. A supplied
amount adds once to quoted consideration. If absent, the amount is explicitly
`QUOTED_AMOUNT_EXCLUDING_UNASSESSED_ACCRUAL`, and full consideration remains
unknown. DIRTY consideration already contains accrued and is not increased.
These amounts are evidence, not cash postings or an interest-pricing model.

The existing daily input register accepts canonical structured notes as well
as bonds. Only CLEAN notes add supplied daily earned interest. Optional missing
daily inputs or assessed accrued-stock anchors leave visible partial coverage;
they are not zero and do not alone block publication. The existing opt-in
complete-daily-interest requirement still applies.

CLEAN note stock FX uses an explicitly assessed opening/closing balance bridge,
not inferred conditional/memory-coupon accrual. It is opening stock × daily FX
change. Balances are already monetary amounts and are not multiplied by nominal
again. Aggregate bought/sold/coupon movements remain assessed movements; an
unclassified coupon portion stays null. DIRTY/NONE notes do not independently
add daily accrual or accrued-stock FX already embedded in their marks. Canonical
interest is not silently allocated between mixed CLEAN/DIRTY listings.

The existing `/v1/valuation/economic-flows` API can record note COUPON income on its economic recognition date, or a later
PAYMENT_ONLY confirmation with zero additional income. The frozen note type
binds this distinction; the existing bond COUPON payment-only guard remains.
An explicit same-date CLEAN daily-interest plus coupon-income overlap fails
with guidance to use PAYMENT_ONLY when already accrued. This is not automatic
entitlement or proof that all prior-period income was recorded correctly.

## Review and database boundary

Ordinary stage → amendment → independent publication controls are reused.
Changed interest inputs still require recalculation before an old candidate can
publish. The inspector shows the frozen quote basis and exact quantity, prices,
FX, factors and bridge before technical proof.

Additive migration **102 / `20261028_102`** extends the immutable retained-stock
guard to canonical notes with explicit assessed-CLEAN proof. It preserves
attempt/tenant/strategy ownership and the bond branch; it does not add trades,
source inputs, permissions or automatic valuations.

## Deliberately deferred

- Barrier/autocall observation evaluation, generated maturity/redemption,
  physical settlement, replacement exposures and payment/accounting automation.
- Coupon schedules or marks do not themselves generate income or payment facts.
- Detached unpaid note coupon receivables are not generated. Bond receivable
  reconstruction is not repurposed for notes. CLEAN note stocks require assessed
  anchors; no conditional coupon history is invented.
- Cross-basis CLEAN↔DIRTY normalization and mixed-listing interest allocation
  require further explicit evidence/workflow support.
- Existing ordinary booking maturity limits remain. A dated past-maturity
  holding is not silently zeroed or assigned arbitrary redemption proceeds.
- This does not add note monetary-measure previews, risk weights, a payoff model
  or complete fund NAV/accounting.

## Evidence and verification

- [Plan and reviewed constraints](../superpowers/plans/2026-10-28-structured-note-pnl.md).
- [Pure quotation/evidence/position cases](../../tests/test_structured_note_valuation.py).
- [Real booking, governed marks, income, stock FX and publication](../../tests/test_structured_note_pnl_integration.py).
- [Browser inspection](../../apps/ops-console/browser-tests/structured-note-pnl.spec.ts).

Verified on 28 October:

- 52 focused offline quotation, frozen-evidence, position and futures cases;
  18 API-contract/architecture/import-boundary checks; 10 separate AMC quotation
  and identity checks.
- Final 16 note disposable-database cases passed, followed by four focused
  later-convention/amendment/publication checks (one added amendment variant;
  17 distinct note cases overall). A broader batch passed 60 cases; its one
  blocked new fixture was cancelled and corrected to stage on the booking
  connection. The 47 adjacent booking, bond-interest, flow and futures cases
  passed. No application lock was removed to resolve that fixture.
- 60 focused frontend cases (40 calculation/coverage and 20 trade-view cases), TypeScript, OpenAPI export parity and reproducible
  generated TypeScript passed. One isolated Edge browser case passed with the
  console-error guard, desktop/narrow widths and a visually inspected screenshot.
- The standard `contract:generate:check` Git-diff gate returns nonzero against
  the intentionally uncommitted generated changes, including earlier work. Its
  generation is deterministic; no commit was made merely to satisfy that gate.
- Local links and `git diff --check` passed. No full Python suite was run.

Migration **102** was applied to the local operating schema after verifying it
was at 101. API **8001** was started and its health and live CLEAN/DIRTY/NONE
contract verified. No operating trades, interest inputs, source rights or
valuations were booked, calculated or published. The frontend was not restarted
as part of this activation.

## Research basis

Checked 28 October 2026: [UBS barrier reverse-convertible guidance](https://keyinvest-ch-en.ubs.com/api/v2/page-api/_clone/filedb/deliver/xuuid/l001ce9b935527174345b0f7ae800a622392/name/Barrier%20Reverse%20Convertible%20Knowledge.pdf)
distinguishes note quotation/accrued and repayment outcomes; [issuer conditional
and memory coupon terms](https://www.sec.gov/Archives/edgar/data/83246/000110465926037646/tm267724d475_424b2.htm)
demonstrate why accrued earnings and economic coupon events cannot be inferred
from a universal fixed-interest rule. Matching supplied marks and deferring
payoff/lifecycle models is this project's bounded implementation decision.
