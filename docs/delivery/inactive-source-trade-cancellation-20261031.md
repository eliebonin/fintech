# Inactive source trade cancellation — 31 October 2026

## Scope and root cause

Three fund sales in the FCPGF research export were explicitly `active=False`.
The optional CSV preparer did not inspect that column and had included them in
native booking. The owner requested deactivation using the cancellation feature,
retaining the database rows rather than deleting them.

## Applied correction

- All three native trades were cancelled through authenticated
  `POST /v1/trades/{tradeId}/cancel-booking`, with a reason, expected event
  sequence and distinct idempotency key. No direct status update or deletion.
- Original quantities, execution prices, dates, references and BOOKED events
  remain unchanged. Each trade now has exactly one additional CANCELLED event.
  Exact retries append no duplicate event; fresh authenticated reads confirm it.
- The previous staged valuation correctly requires reassessment after these
  ledger changes. Its frozen financial evidence is retained. A new FCPGF
  candidate uses the corrected ledger and the previously established
  [prior-day fund NAV policy](fund-nav-lag-20261031.md).
- The optional preparer now excludes explicit inactive positions, RESET flows
  and related daily-interest contributions. It retains the original CSV bytes
  and raw rows, records excluded identities in new manifests, rejects ambiguous
  activity flags, and still rejects accrual links to unknown trades. This does
  not alter the product upload workflow or relax native booking validation.
- Earlier export variants without an activity column retain their existing
  behavior. Existing receipts remain immutable; no reimport of operating data
  was performed to activate this correction.

## Verification and limits

The fresh 20 October FCPGF run is **STAGED**, with current source health. The three
cancelled trades are absent from its contributing position buckets. All ten
fund market-P&L contributions match the supplied production report within one
penny; the maximum exact residual is **0.0000000008 GBP**. The other 113 priced
position contributions and cash FX are unchanged. Removing the erroneous sales
increases the calculated subtotal by **485 GBP**.

The new market subtotal is **13,723.279892142711 GBP** and net calculated subtotal
**56,732.558719743611 GBP**. These are incomplete subtotals: four required
forward/SGD FX observations still lack marks, and accrued-stock opening evidence
and additional production positions remain separate reconciliation gaps.
Nothing was published. This is fund-component reconciliation, not acceptance of
the entire production total.

All 18 focused synthetic checks pass, covering inactive investment/RESET filtering, source-byte
retention, ambiguous flags, known inactive versus unknown accrual links, existing
NAV selection setup and interest aggregation. The actual regenerated export was
also read without writes to verify that exactly these three rows are excluded.
Native authenticated cancellation and retry checks provide live feature evidence;
no product cancellation implementation or schema migration was needed. Private
requests, responses and acceptance evidence remain ignored beside the original
retained bundle. Temporary API sessions were ended.

## Implementation references

- [Optional source preparation](../../tooling/reconciliation_csv/reconciliation.py)
  and [interest aggregation](../../tooling/reconciliation_csv/reconciliation_accruals.py).
- [Focused preparation tests](../../tooling/reconciliation_csv/tests/test_reconciliation_bundle.py).
- [Native cancellation adapter](../../apps/reference_api/trade_corrections.py)
  and [retained correction chain](../../trading/corrections.py).
