# Listed cash trade booking design

**Status:** Approved for implementation planning  
**Date:** 2026-09-30  
**Scope:** A tenant-scoped manual booking path for an already-executed, listed
cash trade.  
**Depends on:** active tenant session, active `TRADING` entitlement, an active
strategy, and an active instrument listing.  
**Supersedes:** Nothing. This narrows and operationalises section 5 of
`2026-09-29-tenant-cash-trading-alpha-design.md` against the delivered tenant,
strategy, instrument, listing, trade-ledger, and P&L foundations.

## 1. Purpose and success criteria

An authorised user must be able to record an already-executed buy or sell of an
active **listing** for an active strategy, then see that immutable booked
execution in the tenant trade blotter and detail page. The existing P&L read
model must be able to consume the persisted record without a parallel trade
representation.

This is a manual operations/trader booking workflow, not order management,
execution routing, broker-confirmation ingestion, or an attempt to implement
transaction reporting. Regulatory sources inform the minimum economic and
attribution facts, but this alpha does not claim to be a regulatory reporting
system.

Success is demonstrated when a permitted tenant user can:

1. open an active listing and choose **Book trade**;
2. provide valid execution facts and submit once;
3. receive one persistent `BOOKED` trade and initial immutable lifecycle event;
4. revisit it from the detail page and tenant trade blotter; and
5. see the booked trade reflected by the existing P&L read model when the
   necessary market-data inputs exist.

The system must reject cross-tenant, inactive, invalid, duplicate-conflicting,
or incomplete requests without creating a partial trade.

## 2. Product boundary

### Included

- Listed, cash-style buys and sells of a canonical instrument through a selected
  active listing. ETPs are explicitly included; the initial form is also usable
  for listed equities and other listing-backed instruments whose default units
  and price basis are supported.
- A user who manually records an execution that has already happened.
- One strategy and one economic execution per booking.
- Optional operational note, client/external reference, and a single
  counterparty selected from governed organisation data.
- Read-only ledger/detail output after booking.

### Excluded

- Orders, routing, executions/fills, allocation across strategies, block trades,
  booking approvals, settlement workflow, accounting postings, confirmation
  ingestion/matching, or regulatory-report generation.
- Funds subscriptions/redemptions, OTC trades, FX forwards, swaps, options,
  structured products, lifecycle corrections/cancellations, and fees. These
  reuse the future ledger and audit pattern but require product-specific terms
  and flows.
- Editing a booked execution in place.

## 3. Decisions

| Concern | Decision |
| --- | --- |
| Tradable subject | A listing is required. The server derives its parent instrument; the client cannot submit a different parent. |
| Entry points | Primary: active listing row on `/instruments/[instrumentId]`. Global fallback: `/trades/new` with listing search. |
| Direction and sign | The form asks for `BUY` or `SELL`; the server persists signed quantity (`BUY` positive, `SELL` negative). The UI never asks users to enter a signed number. |
| Trade type | Persist `INVESTMENT` for this alpha. Purpose is an optional controlled value, initially `INVESTMENT`, `REBALANCING`, `HEDGING`, or `OTHER` with a mandatory note. |
| Listing versus execution venue | The listing venue is reference data and is persisted as the execution venue in this first listed-cash slice. Off-venue execution is deferred until the governed venue/classification model and required counterparty controls are designed. |
| Price/currency | The form pre-fills listing trading currency. Changing it is not allowed in this listed-cash slice; a price needs a positive decimal amount and `UNIT_PRICE` basis. |
| Quantity/unit | Positive decimal quantity, persisted as `SHARES` or `UNITS` according to the selected instrument type's displayed default. Fractional quantities are allowed. |
| Time | Execution date/time is entered in the user's browser local time with its offset and converted to UTC before persistence. Settlement date is required and cannot precede trade date. |
| Audit | The server assigns booking actor/time and creates the initial `BOOKED` lifecycle event in the same transaction. |
| Retry | The BFF generates a UUID idempotency key when the ticket is opened, sends it with `POST`, and reuses it only for a retry of the unchanged payload. Same key with changed facts returns a deterministic conflict. |

## 4. User experience

### 4.1 Listing-first route

The listing table on an active instrument detail page gains `Book trade` for
each active listing. It navigates to:

```text
/trades/new?listingId={listingId}
```

The ticket resolves the listing from the active tenant session and renders a
locked **Trading subject** card with canonical instrument name/type, listing
symbol, listing venue MIC/name, and trading currency. It is not a free-text
field. The parent instrument is shown for clarity only.

`/trades/new` without a `listingId` begins with a server-backed listing search.
Selecting a listing transitions to the same locked-subject ticket. The global
route is a fallback for work initiated from an external instruction, not a
second creation model.

### 4.2 Ticket fields

The ticket is intentionally one page, grouped by the decisions an operator
makes, with a booking summary immediately above Submit.

| Group | Required fields | Optional fields |
| --- | --- | --- |
| Subject | Selected active listing | None |
| Allocation | Active strategy | Controlled purpose |
| Execution | Buy/sell, quantity, price, execution date/time | External/client reference; counterparty |
| Settlement | Settlement date | Operational note |

The page displays the listing price currency and execution venue, and the server
sets channel `MANUAL_UI` and purpose `INVESTMENT`. It shows the calculated unsigned gross consideration
(`quantity × price`) as a user aid, but this is not an independently editable
economic field.

Inline validation occurs before submit and the server returns field-level
problems where possible. Submit disables while in flight. A successful response
routes to `/trades/{tradeId}` with a clear `BOOKED` confirmation.

### 4.3 Read views

The existing `/trades` ledger remains the cross-strategy read view and the
existing trade detail remains the authoritative record. Both must use the
active tenant session, not `resolveLocalTenantContext`, as part of this slice.
The detail view must display direction, the selected listing, execution venue,
booking actor, and initial lifecycle event in addition to the existing facts.

## 5. Command and data design

### 5.1 API contract

Add the tenant-scoped command:

```text
POST /v1/trades
Idempotency-Key: {uuid}
```

The command body deliberately contains human-entered execution facts and stable
references, not tenant ID or derived instrument ID:

```json
{
  "listingId": "uuid",
  "strategyId": "uuid",
  "side": "BUY",
  "quantity": "1250",
  "executionPrice": "101.25",
  "tradeDatetime": "2026-09-30T14:32:00+01:00",
  "settlementDate": "2026-10-02",
  "counterpartyOrganisationId": "uuid",
  "externalReference": "BROKER-REF-123",
  "comment": "Manual booking from confirmed fill"
}
```

`counterpartyOrganisationId`, `externalReference`, and `comment` are optional.
The response is the existing `TradeDetailResponse`
shape so the ticket can navigate and render without a second read.

The Ops Console exposes a narrow `POST /api/trades` BFF route. It gets actor and
tenant exclusively from the signed active-tenant session and forwards the
idempotency and correlation headers; browser-supplied tenant/user headers are
not accepted.

### 5.2 Persistence transaction

The repository uses the existing `trd.trade` table, not a new parallel cash
trade table. In one database transaction it will:

1. resolve and lock the selected listing and confirm it is `ACTIVE`;
2. resolve its canonical parent instrument;
3. resolve and validate the active strategy in the active tenant;
4. resolve governed currency, listing venue, and organisation references;
5. insert the `trd.trade` row with `trade_subject_reference_node_id` equal to
   the listing and `reference_instrument_node_id` equal to its parent;
6. set `trade_type=INVESTMENT`, `price_basis=UNIT_PRICE`, signed quantity,
   listing-derived price currency and execution venue, `lifecycle_status=BOOKED`,
   booking actor, and `execution_channel=MANUAL_UI`;
7. optionally insert one counterparty party-role and one external reference; and
8. append sequence `1`, event type `BOOKED`, to `trd.trade_lifecycle_event`.

The existing lifecycle table is already append-only at the database level. The
trade row must be treated as original-entry evidence: no mutation endpoint is
introduced. A later correction design will append an event and create a linked
replacement/cancellation according to explicit rules.

### 5.3 Idempotency

Use the repository's established idempotency convention for creation commands.
Its durable record is keyed at least by tenant, command type, client key, and
payload fingerprint. A same-key/same-payload retry returns the original detail
response; same-key/different-payload produces HTTP 409; a new key creates one
trade. The trade/lifecycle inserts and idempotency result commit atomically.

## 6. Validation and authorization

- Require a valid active tenant membership and `TRADING` module entitlement.
- Permit creation only for the tenant role/action policy selected for trading
  writes; alpha defaults to `TENANT_ADMIN` until an explicit trader/dealer role
  model is delivered.
- Listing must exist, be active, and resolve to an active canonical instrument.
- Strategy must belong to the active tenant and be `ACTIVE`.
- Quantity and price must be finite positive decimals. Side controls the stored
  sign. Settlement date cannot precede the execution's local calendar date.
- Price currency and execution venue derive from the listing and are not
  editable in this first slice. A later off-venue design must introduce the
  required governed classification and counterparty controls before relaxing
  that rule.
- User-entered time must include an offset. The API normalises to UTC and
  rejects impossible/non-parseable timestamps.
- Every rejected request is atomic: no trade, party, reference, lifecycle event,
  or idempotency success record is created.

The fixed listing, strategy, user, time, quantity, price, venue, and execution
method give the alpha a defensible original-entry record. They correspond to the
core transaction facts described by [MiFIR Article 26](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mifir/article-26-obligation-report-transactions)
and the [FCA transaction-data specification](https://handbook.fca.org.uk/technical-standards/provision/s113c992sn0p1459), while remaining a non-regulatory alpha.

## 7. Error handling

| Condition | Result |
| --- | --- |
| No active tenant/session | Redirect to tenant selection in the BFF; API returns safe unauthorised/forbidden response. |
| Missing trading entitlement or write authority | 403 with no cross-tenant detail. |
| Missing/inactive listing or strategy | 404/422 safe problem, field-associated where possible. |
| Price/currency/quantity/date inconsistency | 422 field validation problem. |
| Idempotency replay, same payload | Original `TradeDetailResponse`, with no duplicate row. |
| Idempotency key conflict | 409 problem showing that the key was already used for different facts. |
| Tenant changes while ticket is open | BFF rejects submission with a safe context-changed error; UI returns to tenant selection or restarts the ticket. |

## 8. Test and evidence plan

Tests precede implementation and cover:

1. repository creation of a listing-backed buy and sell, deriving parent
   instrument, sign, defaults, and initial lifecycle event;
2. atomic rejection for cross-tenant/inactive strategy and listing, invalid
   values, and disallowed currency/venue;
3. same-key replay and conflicting-key protection;
4. API entitlement/tenant isolation and RFC 9457 error contracts;
5. BFF session authority and idempotency-header forwarding;
6. ticket defaults, field validation, locked subject, and success navigation;
7. ledger/detail visibility under the active tenant; and
8. a focused end-to-end path from approved listing to booking to trade detail.

Full Python and frontend suites, typecheck, production build, and a local
authenticated browser/API smoke test are required before claiming completion.

## 9. Delivery sequence

1. Define the command/response contracts and durable idempotency seam.
2. Add repository transaction and API authorization/validation tests, then the
   implementation.
3. Add BFF command and move trade reads to active tenant session.
4. Add listing-first and global ticket routes, then ledger/detail enhancements.
5. Add integration evidence and update user-facing delivery documentation.

## 10. Later decisions

- Trader-person selection, a full controlled purpose catalogue, tags, and
  off-venue execution classification.
- Formal maker/checker and booking approval policy.
- Trade cancellation/correction semantics and linked replacement identifier.
- Fees, multiple counterparties, allocations, block trades, and cash-account
  settlement instructions.
- Broker/file/API ingestion, confirmation matching, order and fill models.
- Product-specific booking for funds, FX, OTC derivatives, options, swaps, and
  structured products.
