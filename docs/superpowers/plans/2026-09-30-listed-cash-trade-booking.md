# Listed Cash Trade Booking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an authorised tenant user manually book one immutable, listing-backed cash buy or sell and see it in the tenant trade ledger and detail view.

**Architecture:** Add one typed, tenant-scoped `POST /v1/trades` command backed by existing `trd.trade` and append-only `trd.trade_lifecycle_event` records, plus a dedicated durable idempotency table. The Ops Console sends the command only through a session-bound BFF, provides listing-first and global ticket entry points, and moves existing trade reads off the legacy local tenant context.

**Tech Stack:** PostgreSQL 18, Alembic, SQLAlchemy Core, FastAPI/Pydantic, pytest, Next.js App Router, React 19, TypeScript, MUI 9, Vitest, pnpm.

**Spec:** `docs/superpowers/specs/2026-09-30-listed-cash-trade-booking-design.md`

## Global Constraints

- Scope is manual booking of an already-executed, listing-backed cash trade only; orders, fills, allocations, confirmations, fees, OTC, and correction/cancellation flows remain out of scope.
- A trade subject is an active listing; the server derives its parent instrument, listing price currency, listing execution venue, `INVESTMENT`, `UNIT_PRICE`, and `MANUAL_UI` values.
- The browser must not supply tenant or actor authority; BFF routes obtain both from `getActiveTenantContext()`.
- `BUY` persists a positive quantity and `SELL` persists a negative quantity; users enter positive amounts only.
- A booked trade is immutable. Creation inserts its first `BOOKED` lifecycle event atomically.
- The command requires `Idempotency-Key`; same key/same request replays, while same key/different request returns the existing `idempotency.key_reused` 409 problem.
- A trade must use an active strategy belonging to the active tenant, and creation is restricted to `TENANT_ADMIN` with `TRADING` entitlement.
- Preserve the standard API metadata and RFC 9457 problem conventions; regenerate the committed OpenAPI contract and TypeScript consumer types.

## Review Focus

- A retry after a network loss must return the original trade without a second trade or lifecycle row; test in Tasks 1 and 2.
- A stale form after a tenant change must not book into the prior tenant; test in Task 3.
- A user must never be able to change listing-derived currency or venue through a crafted request; test in Task 2.
- A sell must create negative stored quantity, but zero and negative user-entered quantities must fail; test in Tasks 2 and 4.
- An inactive listing or cross-tenant strategy must create no partial evidence; test in Task 2.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `alembic/versions/20260930_49_trade_booking_idempotency.py` | Durable tenant/key/fingerprint/replay trade-ID storage. |
| `security_master_schema/models.py` | SQLAlchemy metadata for `trd.trade_booking_idempotency`. |
| `apps/reference_api/contracts.py` | Typed create command and response aliases. |
| `apps/reference_api/repository.py` | Listing/strategy validation, atomic persistence, and replay. |
| `apps/reference_api/main.py` | `POST /v1/trades` authority, errors, and response location. |
| `apps/ops-console/src/lib/reference-api-client.ts` | Session-scoped server API adapters. |
| `apps/ops-console/src/app/api/trades/route.ts` | Session-bound BFF command. |
| `apps/ops-console/src/lib/browser-api-client.ts` | Typed browser submission adapter. |
| `apps/ops-console/src/app/trades/new/*` | Server ticket route and client form. |
| `apps/ops-console/src/components/instrument-detail.tsx` | Listing-level entry action. |
| `apps/ops-console/src/app/trades/*` | Active-session blotter/detail reads and evidence. |
| `tests/test_trade_booking*.py`, Ops Console route/ticket tests | Repository/API/BFF/UI coverage. |
| `packages/api-contracts/*` | Regenerated command contract. |
| `docs/delivery/tenant-workspace-strategy-alpha.md` | Delivered behaviour and exclusions. |

### Task 1: Add durable trade-booking idempotency metadata

**Files:**
- Create: `alembic/versions/20260930_49_trade_booking_idempotency.py`
- Modify: `security_master_schema/models.py`
- Create: `tests/test_trade_booking.py`
- Modify: `tests/test_schema_metadata.py`

**Interfaces:**
- Produces `m.trade_booking_idempotency` with `tenant_id`, `endpoint`, `idempotency_key`, `request_fingerprint`, `trade_id`, and `created_at_utc`.
- Enforces unique `(tenant_id, endpoint, idempotency_key)` and a foreign key to `trd.trade.trade_id`.

- [ ] **Step 1: Write failing schema tests**

```python
def test_trade_booking_idempotency_is_unique_per_tenant_endpoint_and_key(connection):
    insert_key(connection, tenant_a, "/v1/trades", "retry-1", trade_id)
    insert_key(connection, tenant_b, "/v1/trades", "retry-1", other_trade_id)
    with pytest.raises(IntegrityError):
        insert_key(connection, tenant_a, "/v1/trades", "retry-1", third_trade_id)
```

- [ ] **Step 2: Run the new tests and confirm failure**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trade_booking.py tests/test_schema_metadata.py -v`

Expected: FAIL because `trade_booking_idempotency` is absent.

- [ ] **Step 3: Add revision `20260930_49` and matching metadata**

Create the narrow table, unique key, comments, foreign key, and lookup index. Do not reuse market-data snapshot idempotency metadata or add a generic JSON event table.

- [ ] **Step 4: Run migration/schema verification**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trade_booking.py tests/test_schema_metadata.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add security_master_schema/models.py alembic/versions/20260930_49_trade_booking_idempotency.py tests/test_trade_booking.py tests/test_schema_metadata.py
git commit -m "feat: add trade booking idempotency storage"
```

### Task 2: Implement the listing-backed trade command

**Files:**
- Modify: `apps/reference_api/contracts.py`
- Modify: `apps/reference_api/repository.py`
- Modify: `apps/reference_api/main.py`
- Modify: `tests/test_trade_booking.py`
- Create: `tests/test_trade_booking_api.py`
- Modify: `packages/api-contracts/openapi/reference-data-api.v1.json`
- Modify: `packages/api-contracts/src/generated.ts`

**Interfaces:**
- Produces `TradeBookingRequest` with `listingId`, `strategyId`, `side`, `quantity`, `executionPrice`, `tradeDatetime`, `settlementDate`, optional `counterpartyOrganisationId`, `externalReference`, and `comment`.
- Produces `book_listed_cash_trade(connection, tenant_id, actor_id, request, idempotency_key, request_id) -> TradeDetailResponse`.
- Produces `POST /v1/trades` returning `TradeDetailResponse`, HTTP 201 for a new booking, and `Location: /v1/trades/{tradeId}`.

- [ ] **Step 1: Write failing repository tests**

```python
def test_books_listing_buy_with_derived_parent_currency_venue_and_lifecycle(connection):
    detail = book_listed_cash_trade(connection, tenant_id, actor_id, buy_request(listing_id), "key-1", "request-1")
    assert detail.data.trade.listing_id == listing_id
    assert detail.data.trade.instrument_id == instrument_id
    assert detail.data.trade.quantity == "1250"
    assert detail.data.trade.price_currency == "USD"
    assert detail.data.lifecycle_events[0].event_type == "BOOKED"

def test_books_sell_as_negative_quantity_and_replays_the_same_key(connection):
    first = book_listed_cash_trade(connection, tenant_id, actor_id, sell_request(listing_id), "key-2", "request-2")
    replay = book_listed_cash_trade(connection, tenant_id, actor_id, sell_request(listing_id), "key-2", "request-3")
    assert first.data.trade.quantity == "-10"
    assert replay.data.trade.trade_id == first.data.trade.trade_id
```

- [ ] **Step 2: Run repository tests and confirm failure**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trade_booking.py -v`

Expected: FAIL because the request contract and booking repository function do not exist.

- [ ] **Step 3: Define the request contract and repository transaction**

Validate fields before inserts. Lock and require the active listing; derive parent instrument, currency, and venue. Require an active tenant strategy. Insert signed `trd.trade`, optional counterparty/external-reference rows, and lifecycle sequence 1 in one transaction. Use SHA-256 canonical JSON fingerprint and an advisory lock patterned after market-data snapshot idempotency. Rebuild the existing `TradeDetailResponse` for both new and replay outcomes.

- [ ] **Step 4: Add error and atomicity tests**

Cover inactive listing, foreign-tenant/inactive strategy, zero/negative client quantity, non-positive price, settlement before trade date, changed payload with reused key, and crafted price-currency/venue fields. Assert no trade/lifecycle/idempotency success row after each rejection.

- [ ] **Step 5: Add the API route and API tests**

Require membership, `TENANT_ADMIN`, and `TRADING`; map validation to safe 422 and replay conflict to `idempotency.key_reused` 409. Test 201 shape/location, cross-tenant safety, entitlement rejection, metadata, and required header behaviour.

- [ ] **Step 6: Regenerate contract artifacts and verify**

Run: `.venv\Scripts\python.exe scripts\export_openapi_contract.py; pnpm --filter api-contracts build; .venv\Scripts\python.exe -m pytest tests/test_trade_booking.py tests/test_trade_booking_api.py -v`

Expected: generated artifacts change only for the new command and focused tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/reference_api/contracts.py apps/reference_api/repository.py apps/reference_api/main.py tests/test_trade_booking.py tests/test_trade_booking_api.py packages/api-contracts
git commit -m "feat: book listing-backed cash trades"
```

### Task 3: Add the session-safe BFF and retire local trade reads

**Files:**
- Modify: `apps/ops-console/src/lib/reference-api-client.ts`
- Create: `apps/ops-console/src/app/api/trades/route.ts`
- Create: `apps/ops-console/src/app/api/trades/route.test.ts`
- Modify: `apps/ops-console/src/lib/browser-api-client.ts`
- Modify: `apps/ops-console/src/lib/browser-api-client.test.ts`
- Modify: `apps/ops-console/src/app/trades/page.tsx`
- Modify: `apps/ops-console/src/app/trades/[tradeId]/page.tsx`
- Create: `apps/ops-console/src/app/trades/trades-session.test.ts`

**Interfaces:**
- Produces `submitBookedTradeFromBff(payload: TradeBookingRequest, idempotencyKey: string) -> Promise<TradeDetailPayload>`.
- Produces `POST /api/trades`, forwarding active session context and `Idempotency-Key` to `/v1/trades`.
- Changes Trades list/detail reads to `getActiveTenantContext()`; no-session users redirect to `/select-tenant`.

- [ ] **Step 1: Write failing BFF and session-read tests**

```ts
it("forwards only active session context and the retry key", async () => {
  await POST(requestWith({ listingId: "listing-1" }, { "Idempotency-Key": "retry-1", "X-Tenant-Id": "forged" }));
  expect(upstreamPost).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({
    headers: expect.objectContaining({ "X-Tenant-Id": activeTenantId, "Idempotency-Key": "retry-1" }),
  }));
});

it("does not retain resolveLocalTenantContext in trade pages", () => {
  expect(tradesPage).toContain("getActiveTenantContext");
  expect(tradesPage).not.toContain("resolveLocalTenantContext");
});
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `pnpm --filter ops-console test -- src/app/api/trades/route.test.ts src/app/trades/trades-session.test.ts src/lib/browser-api-client.test.ts`

Expected: FAIL because the BFF and active-session read path do not exist.

- [ ] **Step 3: Implement typed server/BFF adapters**

Use `getActiveTenantContext()`, reject a missing idempotency header before upstream work, use `bffErrorResponse`, and do not spread browser authority headers. Add typed server and browser helpers rather than raw ticket fetch calls.

- [ ] **Step 4: Move existing read pages to active tenant context**

Preserve filters/detail/error panels while replacing `resolveLocalTenantContext`. Thread active workspace data into `WorkspaceShell` as other tenant-aware pages do.

- [ ] **Step 5: Run focused verification and commit**

Run: `pnpm --filter ops-console test -- src/app/api/trades/route.test.ts src/app/trades/trades-session.test.ts src/lib/browser-api-client.test.ts`

Expected: PASS.

```bash
git add apps/ops-console/src/lib/reference-api-client.ts apps/ops-console/src/app/api/trades apps/ops-console/src/lib/browser-api-client.ts apps/ops-console/src/lib/browser-api-client.test.ts apps/ops-console/src/app/trades/page.tsx apps/ops-console/src/app/trades/[tradeId]/page.tsx apps/ops-console/src/app/trades/trades-session.test.ts
git commit -m "feat: add tenant-safe trade booking BFF"
```

### Task 4: Deliver the listing-first trade ticket and booking evidence

**Files:**
- Modify: `apps/ops-console/src/components/instrument-detail.tsx`
- Create: `apps/ops-console/src/app/trades/new/page.tsx`
- Create: `apps/ops-console/src/app/trades/new/trade-ticket.tsx`
- Create: `apps/ops-console/src/app/trades/new/trade-ticket.test.tsx`
- Modify: `apps/ops-console/src/app/trades/[tradeId]/page.tsx`
- Modify: `apps/ops-console/src/lib/trades.ts`

**Interfaces:**
- Produces `/trades/new?listingId={listingId}` with locked listing, strategy selector, and form values matching `TradeBookingRequest`.
- Produces a listing-row `Book trade` link only for active listings.
- Uses `submitBookedTradeFromBff` with one `createIdempotencyKey()` held for unchanged retries.

- [ ] **Step 1: Write failing ticket tests**

```tsx
it("keeps an active listing locked and defaults the ticket from reference data", () => {
  render(<TradeTicket listing={activeListing} strategies={[activeStrategy]} />);
  expect(screen.getByText("ETP-TEST · XNAS")).toBeVisible();
  expect(screen.getByLabelText("Price currency")).toHaveValue("USD");
  expect(screen.getByLabelText("Execution venue")).toBeDisabled();
});

it("rejects zero quantity locally and submits a sell with a stable idempotency key", async () => {
  // Assert validation, then assert two unchanged submits use side="SELL", quantity="10", and one key.
});
```

- [ ] **Step 2: Run ticket tests and confirm failure**

Run: `pnpm --filter ops-console test -- src/app/trades/new/trade-ticket.test.tsx`

Expected: FAIL because the route and ticket do not exist.

- [ ] **Step 3: Implement server route and focused client ticket**

Resolve signed active tenant, workspace, listing (or search fallback), and active strategies on the server. Render reference facts as locked fields. The client accepts positive decimal quantity/price, requires strategy and settlement date, captures offset-bearing execution time, displays gross, disables duplicate submits, and routes to returned `tradeId`.

- [ ] **Step 4: Add detail/blotter presentation evidence**

Render buy/sell direction from quantity. Ensure detail shows booking actor, execution venue, and initial `BOOKED` event. Add `Book trade` only to active listing rows and preserve existing instrument links.

- [ ] **Step 5: Run ticket regression tests and commit**

Run: `pnpm --filter ops-console test -- src/app/trades/new/trade-ticket.test.tsx src/lib/navigation.test.ts src/lib/browser-api-client.test.ts`

Expected: PASS.

```bash
git add apps/ops-console/src/components/instrument-detail.tsx apps/ops-console/src/app/trades/new apps/ops-console/src/app/trades/[tradeId]/page.tsx apps/ops-console/src/lib/trades.ts
git commit -m "feat: add listing-first trade ticket"
```

### Task 5: Integrate, document, and verify the vertical slice

**Files:**
- Modify: `tests/test_trade_booking_api.py`
- Modify: `apps/ops-console/src/app/trades/new/trade-ticket.test.tsx`
- Modify: `docs/delivery/tenant-workspace-strategy-alpha.md`

**Interfaces:**
- Produces evidence for approved listing → active strategy → ticket → booked trade detail → P&L-readable record.

- [ ] **Step 1: Write the failing cross-boundary scenario**

```python
def test_active_listing_can_be_booked_once_and_read_back_in_its_tenant(client):
    response = client.post("/v1/trades", json=booking_payload, headers=tenant_headers("trade-e2e-key"))
    assert response.status_code == 201
    trade_id = response.json()["data"]["trade"]["tradeId"]
    assert client.get(f"/v1/trades/{trade_id}", headers=tenant_headers()).status_code == 200
```

- [ ] **Step 2: Run it and repair any missing integration seam**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trade_booking_api.py::test_active_listing_can_be_booked_once_and_read_back_in_its_tenant -v`

Expected: PASS after Tasks 1–4; do not weaken the scenario assertion.

- [ ] **Step 3: Document delivered behaviour and explicit exclusions**

Update delivery documentation with entry point, tenant authority, immutable/idempotent booking, and deferrals. Retain the specification's regulatory-source links.

- [ ] **Step 4: Run full verification**

Run: `.venv\Scripts\python.exe -m pytest; pnpm --filter ops-console typecheck; pnpm --filter ops-console test; pnpm --filter ops-console build`

Expected: all commands exit 0. Run one authenticated local smoke path using the approved listing and active strategy; record only non-sensitive identifiers/results.

- [ ] **Step 5: Commit**

```bash
git add tests/test_trade_booking_api.py apps/ops-console/src/app/trades/new/trade-ticket.test.tsx docs/delivery/tenant-workspace-strategy-alpha.md
git commit -m "docs: verify listed cash trade booking"
```

## Plan self-review

- **Spec coverage:** Tasks 1–2 cover durable idempotent immutable persistence and API controls; Task 3 covers browser authority; Task 4 covers listing-first UX and evidence; Task 5 proves and documents the vertical slice. Exclusions have no implementation tasks.
- **Type consistency:** `TradeBookingRequest`, `book_listed_cash_trade`, `TradeDetailResponse`, `submitBookedTradeFromBff`, and `POST /api/trades` are introduced once and consumed under those exact names.
- **Review focus:** Every listed failure mode has an owning task and explicit test step.
- **Proportion:** Five independently reviewable tasks map directly to data durability, command behaviour, BFF authority, UI, and integration without duplicating production code.

