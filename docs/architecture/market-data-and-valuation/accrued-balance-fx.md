# Accrued-interest balances and FX P&L

3 November follow-up: [independent exploration](../../delivery/accrued-balance-explorer-20261103.md)
reads the latest maintained history by strategy/instrument/date range and shows
chart plus paginated exact evidence. It does not gate on Ops review, reconstruct
unknown balances, change sources or rebuild stale history.

3 November: [daily Ops review layer](../../delivery/interest-daily-review-20261103.md)
retains immutable daily/balance review revisions above the existing native source
and history services. Drafts do not change financial inputs. VALIDATED receipts
apply assessed inputs atomically; explicit gaps remain unknown. Balance review
requires the current daily receipt, with no automatic coupon-payment assertion
or zero reset. These decisions are distinct from P&L publication.

**Status:** Accepted  
**Content type:** Reference  
**Owner:** Valuation and operations  
**Last reviewed:** 2026-11-01 (scoped history-display addition; economic rules reviewed 31 October)

This extends the three-dataset model: assessed daily earned interest, the
[contractual coupon/principal schedule](../trading-and-operations/bond-cashflow-schedules.md),
and retained accumulated interest balances. It is economic attribution, not a
complete accounting ledger or IFRS/GIPS certification.

## Local stock and daily attribution

28 October extension: [fully funded CLEAN notes](../../delivery/structured-note-pnl-20261028.md)
can use explicitly assessed daily balance anchors in the same retained output
table, after migration 102. They use the formula below but do **not** enter bond
trade/coupon-receipt replay. Supplied note aggregate movements can include bought,
sold or paid accrued; their coupon portion remains unclassified rather than zero.
DIRTY/NONE notes do not add separate interest-stock FX. Missing CLEAN anchors are
partial and nonblocking; detached note coupon receivables are not generated.

For each tenant/strategy/canonical bond and supported monetary currency:

```
closing stock = opening stock + daily earned
                + purchased accrued − sold accrued − confirmed coupon receipts

daily interest P&L = daily earned × closing reporting-per-local FX
accrued-stock FX P&L = opening stock × (closing FX − opening FX)
```

Amounts are already position-level money. They are not multiplied by quantity a
second time. Trade accrual uses the frozen total per execution and its direction;
negative ex-coupon amounts retain their sign. Actual cash is separate. Coupon
receipts, purchased/sold accrued and assessed stock changes are not new interest
income. Principal-only redemption does not sell or erase coupon receivables.

Example: opening 1,000 USD, earned 20 USD, coupon received 1,000 USD → closing
20 USD. With GBP/USD 0.75 → 0.76, daily earnings are 15.20 GBP and accrued-stock FX
is 10 GBP. Receipt is not an extra 1,000 USD of P&L. A late/partial receipt reduces
only its amount; new-period interest and unpaid prior coupons can coexist.

## Three-stage maintained workflow

1. Ops validates and records daily earned interest in `/valuation/interest`.
2. Ops explicitly updates local accrued-balance history for a strategy/date window.
   Independently supplied, sourced closing balances can establish or reconcile
   history. Corrections and withdrawals append revisions.
3. Valuation reads maintained stocks and applies reporting FX. It never rebuilds
   a missing stock implicitly or treats a missing amount as zero.

The workbench separates Daily interest and Accrued balances. History shows the
local stock bridge, completeness/freshness and expandable source evidence.
The [read-only evolution viewer](../../delivery/accrued-balance-chart-20261101.md)
opens from each balance row with its bond preselected: choose a date range, inspect its full stored
closing-balance line and the exact table beneath it with 25/50/100/All pagination.
Chart gaps remain unknown; the viewer never maintains or recomputes stocks.
Readable strategies remain available without calculation authority; writes
require scoped valuation-run or review authority. Backend validation of accepted
source revisions is not an independent financial sign-off.

## Sources and explicit maintenance

`valuation/accrued_balance.py` is the pure Decimal rollforward.
`balance_history.py` owns supplied stock revisions, explicit updates and exact-date
reads. `accrued_balance_inputs.reconstruct_local_balances` batch-loads original
daily-input revisions and actual coupon-confirmation revisions only during an
explicit update, as of its source information cutoff. Booked
economics come from the existing complete ledger projection, including
cancellations and effective valuation dates. No current security-master terms
reprice historical execution evidence.

The latest supplied reconciled closing balance before the period is a useful
anchor. A maintained closing stock can be a checkpoint only after verifying its
original source revision signature. A backdated change invalidates it and forces
source reconstruction. Checkpoints remain derived history, never supplied facts.
Detailed daily inputs can also restore opening/closing stocks after a
gap. With no supplied anchor, a first recorded ledger acquisition starts from
zero under the same complete-ledger assumption as position reconstruction;
its purchased accrued is added explicitly. A history containing earlier interest
without an established stock does not acquire an invented zero anchor.

Active coupon bonds require assessed daily history to reconstruct a stock. A
missing day breaks the derived closing stock until an assessed anchor restores
it. Supplied anchors remain authoritative and bridge differences are disclosed.
Zero-coupon absence and verified flat investment days do not invent coupon
earnings. No weekend interpolation or source-specific accrual generation occurs;
business-day aggregated feeds need explicit coverage or assessed anchors.

The schedule supplies the coupon identity and expected date linked to actual
receipts. A scheduled date alone never zeroes the stock or proves full receipt.
Different payment currencies without an assessed native conversion leave the
subsequent derived stock unassessed. Conflicting daily source currencies require
an explicit consistent basis; they are never summed. Local maintenance currently
has no pricing-policy context to translate bought/sold accrued from a different
trade currency. Such a movement remains unassessed until native source history
or an assessed stock establishes it. Reporting FX is selected later by valuation.
This limits stock completeness without restricting trade booking.

## Missing data, storage and review

Missing accrued stocks or optional interest FX do not abort other valid
components. Unknown values remain null with dated reasons, not zero. A known
opening stock can earn FX on T even when T's earnings/closing stock are unknown.
Zero opening stock needs no FX lookup. Same-currency nonzero stock uses identity
FX. Invalid supplied semantics, access and infrastructure errors still raise.
The pre-existing explicitly requested strict daily-interest mode remains separate;
the new stock-FX component has no blocking mode.

Migration 108 adds separate maintained input/history tables:

- `nav.accrued_balance_input`: independent local closing-stock facts, scoped to
  tenant/strategy/canonical bond/currency/date, exact NUMERIC(30,12), source,
  reason, actor and revision chain. ACTIVE and WITHDRAWN are retained.
- `nav.accrued_balance_build`: immutable update request, source information cutoff,
  original source catalogue and revision signature.
- `nav.accrued_balance_history`: exact typed local opening, daily earned,
  bought/sold accrued, coupon receipts and closing amounts linked to the build.

Database guards enforce immutability, tenant/strategy/reference/revision scope,
build date bounds and the bridge for fully known derived rows. API writes share
the valuation-input serialization lock and audited transaction. Unchanged updates
retain a receipt while reusing day rows; they do not invalidate staged financial
evidence. Source changes make affected history stale. Build selection uses its
source information cutoff, allowing a computation today to reproduce historical
knowledge without admitting later supplied facts.

Migration 101's `nav.accrued_interest_balance` remains immutable per-calculation-
attempt/bond/currency/date records with typed opening/closing stock, daily earnings,
non-income movements, coupon amount, reporting currency, FX and stock-FX P&L.
Unbounded PostgreSQL NUMERIC retains exact derived decimals; existing financial
attributions still apply explicit 12-place half-even rounding with exact evidence.
Source IDs/revisions, convention, anchors and missing reasons are retained beside
the typed amounts. These per-attempt records remain output evidence, never future
inputs. Recalculation reads maintained history and verifies source freshness;
it does not trust a previous calculation as an authoritative balance.

`CARRY` is added once to an actual security line when available. After full
disposal, an identified accrued-interest receivable can remain, using a separate
owner key and `ACCRUED_RECEIVABLE_V1` evidence. It has no fabricated security
quantity, market price or trade. A dedicated database scope branch ties it to
retained balance records, reporting currency and exact CARRY amount, preserving
all prior position/cash/component/review guards. Source display checks cover every
dependent FX selection, including historical trade-accrual conversions.

Source coverage and position inspection show available components, missing
bond/dates, the local stock bridge and actual FX inputs. Partial interest totals
are labelled partial. Missing optional stock/FX alone does not block publication.
Staging/amendment/independent publication remain separate. CARRY itself must be
corrected at its source and recalculated, not manually amended.

Immutable revision counts capture daily inputs, supplied stocks, actual history
builds, relevant ledger changes and coupon receipts, including
corrections moving a date and reversals. Payment writers share the valuation input
serialization lock. Changes since staging require recalculation; source health
and reassessment queues use the same checks before paging. Published values are
never silently rewritten. The guard is conservative: a new historical source
revision for the strategy may require reassessment even if a newer anchor would
leave today's calculated amount unchanged. An outstanding receivable remains
disclosed after disposal; missing later exact-date history does not erase it or
justify carrying an old amount forward.

Maintenance is synchronous, explicit and limited to 366 output days per update;
earlier contributing ledger/source history is still read without a trade cap.
There is no automatic interest model, scheduler, bulk workbook or independent
source certification. CLEAN-note assessed stocks retain their separate adapter.

The [1 November Ops workspace](../../delivery/interest-ops-workspace-20261101.md)
separates daily source inputs, assessed closing stocks and derived history into
three tabs. Its read-only refresh, source writes and confirmed rebuild are distinct
actions. Source correction preserves detailed reconciliation metadata; retained
request keys and current strategy authority remain mandatory. The balance overview
requests an exact To-date snapshot and can narrow one instrument before count/paging;
the independent chart reads its full From-to-To series. Missing To-date values are
not replaced with older stocks. These presentation/query changes do not alter
balance reconstruction.

Research basis: [the accrued-interest review](../../research/accrued-interest-fx-20261026.md)
and [initial delivery](../../delivery/accrued-balance-fx-20261027.md). The
[31 October maintained-balance delivery](../../delivery/maintained-accrued-balances-20261031.md)
supersedes the initial implicit bond-reconstruction behavior.
