# Maintained accrued-interest balances

**Date:** 31 October 2026  
**Status:** Implemented; final activation recorded below  
**Scope:** F38/F39; existing PARTIAL/ALPHA classifications remain.

## Delivered behavior

Ops has an interest workbench at `/valuation/interest`, linked from P&L valuation,
with three explicit steps: validate daily earnings, update local accrued balances,
calculate accrued-stock FX P&L. Daily interest, supplied closing stocks, derived
history and per-valuation evidence have separate ownership.

The balance bridge is opening + earned + bought accrued − sold accrued − actual
coupon receipts. Opening USD 1,000, earned USD 20 and receipt USD 1,000 leaves
USD 20. At FX 0.75 to 0.76 GBP/USD, daily earnings contribute GBP 15.20 and opening
stock FX contributes GBP 10. Receipt is not new income. Partial receipts reduce
only the paid amount; reversed confirmations restore stock. A scheduled coupon
date never proves payment or zeroes new-period accrual.

Supplied stocks require a source/reason, exact decimal string and canonical bond
currency. Correction/withdrawal appends an immutable revision. Explicit updates
retain source signatures and provenance. Verified closing checkpoints support
next-day maintenance; changed original sources force reconstruction. Repeating
unchanged work retains a receipt without creating new financial rows or making
staged evidence stale.

Valuation reads exact-date maintained history, checks freshness and freezes stock
and FX proof. A missing closing row can use the exact preceding day's verified
closing as opening; no indefinite carry-forward occurs. Missing/stale optional
stock or FX is a disclosed omission and does not independently stop calculation
or publication. Published results remain immutable; changed staged sources require
recalculation under existing review controls.

## Implementation and controls

- Migration 108 adds `nav.accrued_balance_input`, `nav.accrued_balance_build` and
  `nav.accrued_balance_history`. Migration 101's per-attempt output remains.
- [Domain commands](../../valuation/balance_history.py),
  [contracts](../../valuation/balance_history_contracts.py),
  [schema](../../valuation/balance_history_tables.py),
  [local/FX adapter](../../valuation/accrued_balance_inputs.py),
  [source health](../../valuation/accrued_balance_health.py).
- [API](../../apps/reference_api/balance_history_routes.py): supplied input
  GET/POST, explicit refresh POST, history GET with server pagination, full build
  evidence GET and scoped bond/currency choices.
- [Workbench](../../apps/ops-console/src/features/valuation/interest-register.tsx):
  strategy/date filters, readable amounts, correction/withdrawal, update action,
  paginated history and collapsed proof. Existing verified BFF transport, retained
  request identity and uncertain-outcome retry controls apply.
- Scope is enforced before writes and replay. Database guards reject mutation,
  cross-strategy supersession and inconsistent known derived bridges. Read access
  does not imply run/review authority.

## Deliberate limits

This maintains supplied interest; it does not generate coupon accruals, certify
correctness, create cash or perform accounting. A contractual schedule alone
cannot establish missing historical amounts. Ops needs sufficient daily history
or assessed stock anchors. The four missing USD bond stocks in the reconciliation
dataset have not been fabricated.

Refresh is synchronous, explicit and at most 366 output days; earlier contributing
sources are still read. Invalidation is conservative at strategy level. No
background scheduler or bulk Excel stock upload is included. Local maintenance
cannot translate trade-accrual movements from another currency without an assessed
native basis; reporting FX is applied later. CLEAN-note anchors retain their
separate existing path.

## Research and rationale

The [Microsoft materialized-view pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/materialized-view)
(updated September 2026) supports persistent derived read models with explicit
refresh and source/access consistency. Immutable builds and verified checkpoints
are our implementation choice; supplied facts remain authoritative inputs.

[IMF BPM6 Compilation Guide](https://data.imf.org/-/media/iData/External-Storage/Documents/FB1F86C7158646DDB554D0882F1F2A3B/en/3-BPM6-com-guide.pdf),
paragraph 13.65, distinguishes accrued interest from subsequent payment. This
supports the economic distinction, not an IFRS/regulatory certification.
[GOV.UK table guidance](https://design-system.service.gov.uk/components/table/)
informs captions, headers and right-aligned comparisons. Technical proof is
progressively disclosed beside operational amounts.

## Verification and local activation

Focused contracts/financial/API checks: 58 passed in a disposable PostgreSQL
database (46.37 seconds). Frontend component/transport checks: 44 passed.
TypeScript `tsc --noEmit` passed. One pre-existing Starlette/httpx deprecation
warning remains. No full suite or operating valuation publication was performed.

Adjacent note, DIRTY-bond and daily-interest checks added 33 distinct cases:
32 passed initially; one DIRTY-bond test still assumed implicit reconstruction.
It now performs the explicit history-update stage, preserving its exact daily
interest and stock-FX assertions, and its targeted rerun passed. In total,
91 distinct focused backend cases and 44 frontend cases passed across these runs.
The new assessed-stock revision test also confirms stale staged publication is
rejected until recalculation.

Migration `20261031_108` applied to the local app database; all three tables verified
using the maintenance connection. API 8000 restarted and its new endpoints verified;
portal 3001 serves the workbench. The runtime role remains unable to read migration
administration metadata. Browser read-through verified daily source rows, strategy
choices, balance view, empty-history guidance and scoped update/assessment controls.
The final page had no console errors; its development reload warning came from
editing the component during inspection. Long source identities were moved into
closed disclosures after the live layout check. Existing operating stock inputs,
history builds, trades and valuations were not generated or changed by acceptance.
