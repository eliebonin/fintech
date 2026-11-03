# Fund NAV boundary correction — 31 October 2026

## Agreed convention

For the imported FCPGF daily P&L, valuation date **T** uses the fund NAV for
**T−1**, and its opening value uses the NAV for **T−2**, counting the fund's
valuation sessions. Trade-price-currency → strategy-currency FX stays on **T**
and **T−1**. A dated NAV remains attributable to its original date; neither the
observation nor its publication/receipt evidence is relabelled.

For 20 October 2026, the closing/opening NAV dates are 19/16 October, with FX
20/19 October. This is explicit fixed-lag selection, not tolerance for an
unexpected missing price or a fallback to whichever observation happens to exist.

## Root cause and correction

The engine already supports `NAV_DATE` with `FIXED_LAG` and an explicit calendar.
The optional CSV setup incorrectly created a `SAME_DAY` NAV rule and an all-open
date-bucket calendar. Applying a lag to that calendar would count weekends.

- Fresh optional setup now uses `FIXED_LAG`, `lagBusinessDays=1` and zero permitted
  staleness for fund NAV rules. All other price/FX rules remain same-day.
- Its dedicated published tenant VALUATION calendar uses a declared Monday–Friday
  reconciliation baseline. Actual fund holidays are not invented from absent
  observations; they still require governed fund-calendar dates/configuration.
- Local FCPGF calendar v2 and pricing policy v3 were created through normal
  authenticated/audited APIs. The policy is labelled **Imported EoD — prior-day
  fund NAVs (personal reconciliation)**. Prior versions remain retained.
- No universal lag is hard-coded into the calculator. Calendar/lag policy remains
  configurable for other actual fund valuation conventions; equity/ETF and FX
  semantics are not changed. No source date, trade, permission or financial result
  is rewritten.
- Existing optional setup replay continues to return its original retained
  receipt. The correction is a separately identified native policy/calendar
  version, not a rewrite of that earlier setup evidence.

The separate inactive-sales import finding was not corrected by this NAV change;
it is resolved in the later [audited cancellation check](inactive-source-trade-cancellation-20261031.md).
Missing opening accrued stocks, additional production positions and required
forward/SGD FX observations also remain separate reconciliation items.

## Verification and local activation

Nine lightweight checks pass, including explicit NAV lag, unchanged other rules,
weekend and declared closure handling, timezone/DST and bounded session semantics.
No full regression suite or migration is required: the product selection behavior
already existed. A fresh native FCPGF calculation completed into staging with policy v3.
All ten fund positions retain 19/16 October NAV dates and, where needed, 20/19
October FX dates. Requested/used NAV dates agree exactly (zero staleness).
All 113 non-fund position components and cash FX are unchanged; frozen trade
facts are identical. The new market subtotal is **13,238.279892142711 GBP** and
net calculated subtotal **56,247.558719743611 GBP**. Four required forward/SGD FX
observations remain missing, so the candidate is incomplete and unpublished.
At this checkpoint the three inactive imported sales remained unresolved; see
the later cancellation check above. This is not a claim of full production
reconciliation. Private frozen response/verification evidence
remains ignored beside the retained bundle, and the temporary API session ended.

## Implementation references

- [Optional setup](../../tooling/reconciliation_csv/reconciliation_eligibility.py)
  and [focused tests](../../tooling/reconciliation_csv/tests/test_fund_nav_convention.py).
- [Existing selection](../../market_data/policy_selection.py) and
  [session targeting](../../market_data/pricing_conventions.py).
- [Methodology](../architecture/market-data-and-valuation/valuation-methodology.md)
  and [partial-price review](incomplete-price-review-20261031.md).
