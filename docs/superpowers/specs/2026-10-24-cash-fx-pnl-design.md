# Cash-balance FX P&L — agreed daily convention

**Status:** Approved convention; implementation details below are engineering rulings  
**Date:** 2026-10-24

**Supersession:** the user's 25 October instruction removes the original opt-in
choice below. Current cash assessment is standard, without an exclusion flag;
missing snapshots are visible/non-blocking. See the [current implementation plan](../plans/2026-10-25-standard-cash-pnl.md)
and [maintained delivery](../../delivery/cash-fx-pnl-20261025.md). The opening-balance
formula and source/review safeguards remain unchanged.

The user approved opening-balance cash FX attribution, separate from trading,
income recognition, settlement and accounting. For each daily boundary, signed
opening cash × (closing FX − opening FX), where FX is reporting-currency units
per unit of cash currency. Example: USD 100,000 × (0.76 − 0.75) = GBP 1,000.
Deposits/withdrawals/settlements are not income. Movements are treated at closing
FX for this attribution; no intraday timing or conversion-spread P&L is claimed.

## Alternatives and chosen scope

Opening-balance attribution fits existing exact-date EoD snapshots and the user's
choice. Closing-balance weighting attributes the whole day's FX to newly arrived
cash and was not selected. Full movement-time attribution requires movement/rate
inputs we do not have and is deferred. Never calculate profit as the difference
between translated closing/opening cash values without removing cash movements.

Reuse TENANT_EOD account/company/currency snapshots, append-only revisions,
governed FX selection, exact arithmetic, staging/amendment/publication and current
tenant/strategy/DISPLAY checks. No fabricated instruments, positions or trades.
Cash-owned attribution links account and cash currency through typed foreign
keys; frozen evidence retains each exact-date balance revision and FX input.
Multiple accounts at the same company remain separate.

## Explicit implementation choices

- `includeCashBalances` defaults false for API/backward retry compatibility and
  is an explicit checkbox on new daily requests; recalculations retain the flag.
  Historical stored results and hashes are not backfilled.
- Cash inclusion uses daily date mode, not arbitrary intraday timestamp cuts.
  Multi-day requests sum daily opening-balance contributions, not the first
  balance over the entire period. No silent carry-forward across missing dates.
- Discover known account/currency scopes from uploaded history visible at the
  information cutoff. Every included day needs exact opening and closing
  snapshots, including explicit zeros. Missing scope/date inputs are omitted
  with frozen partial coverage, not treated as zero. Never-uploaded accounts
  remain explicitly unassessed; no completeness claim beyond known scopes.
- Missing/ineligible policy FX for a nonzero foreign opening balance blocks
  calculation. Same reporting currency uses 1; zero opening exposure requires
  no market observations and earns confirmed zero under this convention.
- `CASH_FX` is a separate component family contributing to gross/net, not added
  to the investment price/FX subtotal or interest. The existing securities
  opening/closing/execution bridge remains unchanged.
- Cash records are inspectable in their own account report. Coverage separates
  excluded/not requested, included, partial and unassessed. Interest/flows are
  not recognized again from balance changes.
- Corrected/new relevant cash data invalidates staged publication and amendment
  approval. Published numbers remain immutable and display reassessment state.
  Current-access checks still apply at read/review/publication.
- Cash writers/review share strategy serialization. Source-health detection may
  conservatively flag newly received historical snapshots up to the closing
  date, even if their eventual financial impact is nil; no automatic recalculation.

## Acceptance

Test long/negative/zero/same-currency balances, daily changing balances, account
separation, missing versus zero, information cutoffs/revisions, provider rights,
cash-only results, no-market-input proof, immutable staging, amendments,
independent/self publication, stale cash rejection and old request identities.
Do not run tests against operating databases, seed cash, publish operating runs,
grant rights or apply a local migration without explicit approval.

## Sources and applicability

Checked 24 October 2026: [IBKR cash report](https://www.interactivebrokers.co.uk/en/?f=38845)
distinguishes cash activity, translation effects and balances. Its legacy settlement
examples do not prescribe our timing convention. [IAS 21 overview](https://www.ifrs.org/issued-standards/list-of-standards/ias-21-the-effects-of-changes-in-foreign-exchange-rates/)
establishes the foreign-currency translation topic, not this internal daily P&L
method or statutory compliance. The opening/EoD attribution convention is the
user's explicit product choice, not a claim of exact intraday or accounting P&L.
