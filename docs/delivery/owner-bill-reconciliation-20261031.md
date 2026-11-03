# Owner-supplied closed Treasury-bill position — 31 October 2026

## Supplied facts and normalization

The supplied FCPGF export omitted Treasury bill `GB00BSGQQ650`, its executions
and prices because it was no longer held at the closing date. The owner supplied
both executions and the opening EoD clean mark as separate reconciliation
addenda. Original bundle CSVs, hashes and earlier valuation evidence are unchanged.

- Buy: 8 May 2026 at 11:00 UTC, settlement 11 May, 1,000,000 nominal,
  source counterparty **22**, clean consideration 979,917.86 GBP.
- Sale: 20 October 2026 at 11:00 UTC, settlement 21 October, 1,000,000 nominal,
  source counterparty **17**, clean consideration 997,991.60 GBP.
- The displayed prices were rounded. The buy's fraction-of-par quote
  **0.97991786** is derived from supplied consideration divided by nominal,
  rather than asserted as an independently supplied unrounded execution quote.
  The sale uses the owner's earlier explicit **0.9979916** quote.
- Native percentage-of-par execution prices are therefore **97.991786** and
  **99.79916**, with unchanged nominal and quote divisor 100.
- The owner supplied **0.99787468** for 19 October EoD, stored exactly as
  **99.787468 CLEAN / RAW**. It is not backsolved from expected P&L.

The latest explicit rows take precedence over the earlier suggestion to use the
same counterparty. Both source company IDs retain their existing **unverified
operational-reference** identities; no legal name or LEI is invented. Source
investment-bucket and yield-lock fields remain retained annotations, without
claiming new product support for those external taxonomy IDs.

## Reference and booking evidence

The missing canonical GBP zero-coupon bill and its nominal/CLEAN convention were
created through native proposal/approval APIs. Public secondary reference data
provides the 9 November 2026 maturity and penny denomination:
[Cbonds instrument reference](https://cbonds.com/bonds/2138817/). The original
issue date was not confirmed and is not invented from the trade or settlement.

The original reference covered the first supplied sale date. Once the buy was
provided, unchanged definition/terms versions were appended to cover its actual
8 May execution, with authority checks, retained source payload and an explicit
audit event. The convention extension follows native proposal approval. Prior
versions and the already-booked sale's lifecycle evidence remain retained.
This is a scoped research-data completion, not a new general reference-amendment
API or a relaxation of historical booking checks.

Both executions were booked through the native bond command. Source sale accrued
interest is explicitly zero; the blank buy accrual becomes zero because this is
a zero-coupon instrument, with that derivation disclosed. Exact retries return
the same native identities and lifecycle events. Trade history confirms two
executions and **zero closing nominal**, with different counterparties as supplied.
No cash payment or balance was generated.

The opening mark uses the existing private reconciliation dataset with current
ACQUIRE/STORE/DISPLAY/NON_DISPLAY checks, exact normalization, retained raw JSON,
vintage, ingestion report and audit. No rights or tenant permissions were added.
The observation has source-date-only EoD bucket semantics, no claimed official
exchange designation and no invented publication timestamp. It is owner-supplied
source data, not an independent reviewed-price override or a vendor observation.

## Daily P&L convention

Closing the position on T does not remove its contribution on T. The opening
nominal is valued using the 19 October mark and the sale uses its execution price:

`1,000,000 × (0.9979916 − 0.99787468) = 116.92 GBP`

The May purchase price is retained in the ledger but does not replace the
19 October opening mark for daily P&L. The full buy-to-sale gain is a different
period calculation. No T closing market mark is manufactured for a position
that is flat after the sale.

Private source addenda, normalized requests, source hashes, API responses and
verification scripts remain ignored beside the retained research bundle. They
are not application dependencies, startup seeds or supported tenant CSV formats.

## Native valuation acceptance

A new 20 October FCPGF calculation completed into **STAGED / CURRENT**, using the
same pricing policy as the preceding run. Frozen position evidence shows
1,000,000 opening nominal, zero closing nominal, the owner-supplied 19 October
mark and the 20 October sale as its closing execution. Its price component is
exactly **116.92 GBP**, matching the supplied production report; FX is zero.
The engine requests only the opening market mark for this closed position.

All 123 previously calculated position contributions and cash FX are unchanged.
The market subtotal is now **13,840.199892142711 GBP**, and net calculated subtotal
**56,849.478719743611 GBP**. Four unrelated forward/SGD FX observations remain
missing, and opening accrued-stock evidence and two additional nonzero
production forward positions remain separate reconciliation gaps. These are
partial subtotals, not a fully reconciled fund total. No result was published.

Native booking retries, retained sale-event equality, exact consideration,
zero-net trade history and frozen calculation inputs were checked. No product
code or migration changed, and no full regression suite was needed for this data
completion. Temporary API sessions were ended.
