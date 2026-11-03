# Bond DIRTY-to-CLEAN quotation normalization

**Status:** Implemented; focused verification passed; local activation recorded below  
**Content type:** Delivery and bounded design reference  
**Owner:** Market-data and valuation engineering  
**Last reviewed:** 2026-10-28

## Agreed economics

Daily plain-bond P&L uses **CLEAN = source DIRTY − matching quoted accrued per
100 nominal**. The ordinary price/FX/execution bridge then uses that CLEAN price.
Supplied strategy daily earnings contribute `ACCRUAL`; assessed opening accrued
stock times the daily FX change contributes `CARRY`. Neither is generated from
the quoted price component. This implements the user's second approach rather
than an all-in DIRTY return with additional accrued income.

Example: nominal 100,000, DIRTY 101 → 101.02, quoted accrued 1 → 1.02. CLEAN is
100 on both days, so price P&L is zero. Independently supplied daily earnings of
20 contribute 20 once. A coupon quote reset to DIRTY 100 / accrued 0 still gives
CLEAN 100; a payment confirmation is not new earnings.

The quote component and a strategy accrued stock need not agree. The native
foreign-currency regression retains bought accrued of 1,250; FX 1.5 → 2 gives
stock FX 625. It does not replace that holding-specific stock with the source
quote's per-100 component. Actual market date, quote settlement date, valuation
date and information cutoff remain distinct. RAW/share adjustment basis remains
separate from CLEAN/DIRTY quotation.

## Source evidence and ingestion

[Migration 103](../../alembic/versions/20261028_103_bond_quote_accrual.py) adds
`md.bond_quote_accrual`, an immutable typed sidecar keyed by the **exact price
observation**:

| Column | Meaning |
| --- | --- |
| `observation_id` | Owning DIRTY source observation and correction identity |
| `accrued_interest_per_100` | Signed `NUMERIC(30,12)` quoted component, not daily position interest |
| `quote_settlement_date` | Explicit provider quotation settlement date |
| `source_reference` | Required source evidence reference |
| `recorded_at_utc` | When the component became known |
| `component_hash` | Canonical amount/date/reference hash |

Instrument/listing, currency, market date, dataset/licence, raw payload and source
vintage inherit from the observation; they cannot be independently overridden.
The controlled writer requires an ACCEPTED native RAW BOND PRICE observation,
DIRTY dimension and explicit divisor 100. Zero or signed negative ex-coupon
accrued is allowed. Invalid/nonfinite amounts, excess precision, inconsistent
dates and nonpositive derived plain-bond CLEAN prices are rejected without
rounding. Mutation/deletion is rejected; corrections append a new observation.

[DailyPoint](../../market_data/contracts.py) has optional typed bond quotation
and quote-accrual fields. [Ingestion](../../market_data/ingestion.py) validates
the package; [storage](../../market_data/storage.py) retains both atomically and
includes the component hash in duplicate detection. A component-only correction
therefore creates a new price revision even if DIRTY is unchanged. Ordinary
non-bond/Yahoo bulk insertion and source-rights checks remain intact.

This is an internal provider-neutral capability, not a new bond provider fetch
or tenant file-upload screen. The existing daily ingestion boundary accepts one
source field per series kind in a delivery; this change does not add simultaneous
same-kind CLEAN and DIRTY field routing. The trusted paired writer also supports
existing retained canonical bond observations; it is not a public write endpoint.

## Calculation, review and display

[Bond selection normalization](../../valuation/bond_prices.py) requires the
component known by the information cutoff, verifies its hash and source basis,
and freezes original DIRTY, quoted accrued, derived CLEAN and their dates/source
proof. The common calculator consumes the derived value. Original observations,
trades and previously published results are not rewritten. Full monetary-value
previews continue to use the original eligible DIRTY quote.

Missing quoted accrued is a **mandatory price-input gap**: CLEAN cannot be
determined. Missing optional strategy daily earnings or accrued stocks still
leave warnings/partial components; they are not confirmed zero and do not alone
block publication. A daily earnings amount or a trade accrued amount cannot
substitute for matching quote evidence.

The inspector shows source DIRTY, accrued per 100, CLEAN used, actual market date
and quotation settlement date. Applied rule `BOND_DIRTY_TO_CLEAN` explains the
conversion. Presentation reads frozen exact amounts; it never recalculates.
Technical evidence remains available under the existing disclosure.

[Publication guard](../../valuation/bond_quote_review.py) reselects normalized
bond inputs at the saved economic cutoff under current eligible source access,
and rejects changed observations, paired components or lost valuation rights.
Query-time-only proof differences do not invalidate an unchanged pair. Ordinary
independence/self-publication policy, amendments and source checks remain.
The request calculation contract is `economic-pnl-bond-clean-v1`, preventing
reuse of a differently interpreted request identity.

## Verification and activation

Focused checks on 28 October, using native synthetic bookings and owned
disposable databases:

- 46 offline normalization, booking, request-contract, architecture and repository
  neutrality cases passed.
- 25 paired-ingestion, normalization/publication and existing accrued-stock
  integration cases passed; component-only corrections, revoked rights, signed
  components, cutoff knowledge, optional gaps and unchanged monetary previews
  are covered.
- 54 adjacent market-data ingestion, economic-P&L, bond-redemption and
  structured-note integration cases passed.
- The final 10 native bond cases passed again after keeping RAW/share adjustment
  basis independent of the CLEAN quotation transformation.
- 20 focused frontend cases, TypeScript and OpenAPI export parity passed. One
  isolated Edge browser case passed with console-error checks, desktop/390px
  overflow checks and a visually inspected screenshot.
- No full Python regression suite was run. One initial broader invocation used
  a nonexistent test filename and collected nothing; the corrected 54-case batch
  above passed. This is bounded feature verification, not full portfolio sign-off.

After user approval, migration **103** was applied from verified operating schema
102. The new table and revision were confirmed, API **8001** was restarted and
`/health` returned `status: ok`; startup completed without an error. No operating
prices, trades, interest, rights or valuations were created/changed. The frontend
was not started by this activation; browser verification used an isolated fixture.

## Limits and research basis

No automatic quoted-accrual/interest engine, schedule/DCF pricer, bond subtype
expansion, inferred provider evidence or general market-data source-impact
fanout is added. Broader independent reconciliation, operational scaling and
warning/stock-display findings in [FIX.md](../../FIX.md) remain open. Structured
notes retain their separately agreed quotation methodology.

Rechecked 28 October: [MSCI fixed-income calculation methodology, April 2022](https://www.msci.com/eqb/methodology/meth_docs/MSCI_FI_Index_Calculation_Methodology_April2022.pdf)
defines dirty value from clean plus accrued; [S&P fixed-income mathematics,
March 2025](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-fixed-income-index-math.pdf?force_download=true)
distinguishes price/interest return and coupon effects. The economic distinction
supports the chosen normalization; source pairing/storage and scoped publication
checks are this project's implementation decisions, not mandated index rules.

[Plan](../superpowers/plans/2026-10-28-bond-dirty-to-clean.md) ·
[Numerical/ingestion tests](../../tests/test_bond_price_normalization.py) ·
[Native financial integration](../../tests/test_bond_dirty_market_integration.py) ·
[Source ingestion regression](../../tests/test_bond_quote_ingestion.py) ·
[Browser check](../../apps/ops-console/browser-tests/bond-dirty-price.spec.ts)
