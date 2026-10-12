# P&L attribution subjects and cost ownership

**Status:** Current POSITION ownership implemented; broader typed ownership remains design direction
**Content type:** Architecture decision  
**Owner:** Trading, valuation, and operations architecture  
**Last reviewed:** 2026-10-12

## Current implementation — 2026-10-12

Current economic P&L is owned by a compatible **POSITION** bucket, with original trades/events retained as lineage. Historical first-alpha records remain TRADE-owned and readable. A trade is therefore not the sole attribution owner. The broader design direction below describes additional economic subjects; it is not an implemented generic polymorphic ownership API.

## Original direction and rationale

The October 7 direction treated trade-level attribution as the primary/common case but explicitly rejected `trade_id` as the only possible owner. Revision 70 superseded the first-alpha ownership choice with compatible positions while preserving original execution lineage. The broader **attribution subject** concept remains the economic object to which P&L or a cost belongs.

This prevents fake cash or fee trades from being created merely to satisfy a trade-only attribution schema. It also preserves the distinction between an execution, a holding, a cash state, and a vehicle-level operating cost.

## Subject types and practical rules

The table is the broader target model. Today the database enforces mutually exclusive trade/position ownership, an actual valued reference subject and immutable trade/event lineage. CASH_BALANCE, direct STRATEGY/FUND/FUND_SHARE_CLASS cost ownership and allocation workflows remain undelivered. Strategy scope on a position result is not the same as strategy-owned attribution.

| Subject type | Use when | Examples |
| --- | --- | --- |
| `TRADE` | P&L or a cost is caused by one booked economic event. | Equity MTM, OTC option model mark, brokerage commission, execution tax, swap reset. |
| `POSITION` | The amount arises from a holding but cannot fairly be assigned to one execution. | Position-level corporate-action adjustment, holding-level allocation. |
| `CASH_BALANCE` | The effect belongs to a frozen cash balance. | FX translation P&L on USD cash, cash-account interest. |
| `STRATEGY` | The effect belongs to the portfolio/account as a whole. | Custody fee, audit/legal/platform charge, unallocated operational cost. |
| `FUND` | The effect is legally/economically fund-vehicle specific. | Fund management-fee accrual, fund-level expense. |
| `FUND_SHARE_CLASS` | The effect is share-class specific. | Performance fee, share-class hedging cost, class-specific administrator fee. |

The governing rule is:

1. Use `TRADE` when a particular booked execution causes the economics.
2. Use `POSITION` or `CASH_BALANCE` when the economics arise from an end-of-day state.
3. Use `STRATEGY`, `FUND`, or `FUND_SHARE_CLASS` for vehicle/account costs and accruals.
4. Do not create a synthetic trade merely to record a non-trade cost.

## Components, not separate P&L universes

Costs are components of an attribution owned by their subject. The initial component catalogue should distinguish at least:

- market: `PRICE`, `FX`, `PRICE_FX_CROSS`, `MODEL_MARK_CHANGE`, later sensitivity components;
- income/cashflow: `ACCRUAL`, `CARRY`, `COUPON`, `DIVIDEND`, `RESET`, `CASHFLOW`;
- costs: `BROKER_FEE`, `CUSTODY_FEE`, `MANAGEMENT_FEE`, `PERFORMANCE_FEE`, `TAX`, `OTHER_COST`;
- controlled non-economic reporting changes: `ADJUSTMENT`, with four-eyes approval.

An approved adjustment must remain separate from a correction of price, FX, trade, cash, or valuation inputs. Input corrections require an upstream recalculation and create a new immutable attribution version; they must not be concealed as an adjustment component.

## Data-model direction

The future attribution header should declare `attribution_subject_type` and use typed nullable links rather than an unvalidated polymorphic `subject_id`. Candidate links are:

- `trade_id`;
- `position_snapshot_line_id`;
- `cash_balance_id`;
- `strategy_id`;
- `fund_reference_node_id`;
- `share_class_instrument_node_id`.

PostgreSQL checks and, where needed, triggers must enforce that the correct link is populated for the declared subject type. A generic `subject_id` without a foreign key is explicitly rejected because it would allow orphaned or misclassified P&L.

Every attribution additionally carries tenant ownership, value date, frozen market-data/valuation inputs, calculation methodology/version, immutable version number, supersession link, and staged/reviewed/published lifecycle evidence.

## Relationship to the current Fortem-core attribution workflow

The existing Fortem-core P&L attribution package is the source of operating principles: clean price/FX/cross decomposition, immutable versions, staged review, publication, and approved adjustment workflow. The new platform will adapt those principles to UUID identities, tenant/strategy scope, frozen `md` and `nav` inputs, and the subject types above. It must not mechanically copy the legacy integer-ID tables or reflect them as its new platform contract.

## Deferred implementation

The [first delivery](../../delivery/valuation-market-pnl-alpha.md) implemented TRADE ownership; [revision 70/position reconstruction](../../delivery/position-reconstruction-foundation.md) subsequently introduced position-owned financial results and immutable ledger lineage. [Economic v3](../../delivery/economic-pnl-implementation-2026-10-09.md) adds price/FX, assessed accrual/flows and reviewed component amendments. All use the existing `nav` schema. General cash/vehicle-level allocation remains future work, not a second implemented subject engine.

- broader attribution subject links and their type-specific FK checks;
- calculation-method catalogue, including price/FX, model-mark, sensitivity, and cashflow methods;
- persisted selection of measurement semantics and valuation methodology per run;
- allocation policies for costs which arrive strategy-level but need downstream fund/share-class allocation;
- broader cost allocation and cash/vehicle-owned workflows; bounded position income/cost components and staged approved amendments are already implemented.
