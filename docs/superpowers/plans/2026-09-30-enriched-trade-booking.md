# Enriched Trade Booking Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution or superpowers:subagent-driven-development if selected by the user. Track steps with checkboxes.

**Goal:** Book, review and inspect listing-backed cash trades with parties, trader, classifications, tags and typed tenant properties.

**Architecture:** Extend the existing trade command and normalized child tables; add a trade-specific property/tag registry and booking-context lookup. Keep session authority in the BFF, validate every selection on submission, and read back the persisted enrichment through the existing detail response. Split the client ticket by responsibility without replacing the route or introducing a parallel trade model.

**Tech Stack:** Existing Python/FastAPI/Pydantic/SQLAlchemy/Alembic/PostgreSQL stack; Next.js 16.3.4, React 19, TypeScript, Vitest and pnpm.

**Spec:** [Approved enrichment design](../specs/2026-09-30-enriched-trade-booking-design.md).

**Execution status:** Written plan awaiting review. No product implementation has started.

## Global Constraints

- Keep `/trades/new`, active tenant session, `TRADING`, and `TENANT_ADMIN` write authorization.
- Manual, already-executed, listing-backed cash trades only; `INVESTMENT` type remains fixed.
- Counterparty/broker use active shared organisations, explicitly not a tenant credit-approved list.
- Trader must be an active person linked to an active account with currently effective active tenant membership.
- Properties: `TEXT`, `DECIMAL`, `DATE`, `BOOLEAN`, single-choice `CHOICE`; optional empty values are omitted, false/zero retained.
- Preserve immutable property meaning and historical retired definitions/tags.
- Keep T+2 weekdays editable, preserving overrides and the holiday limitation.
- No fees/net settlement, OTC, off-venue, cancellation, allocation, valuation or P&L changes.
- Write lightweight failing tests first; then database/API/browser tests and full suites.
- Preserve all pre-existing dirty changes. Commit only task-owned changes, using selective staging where files overlap earlier work.
- No new runtime dependency without a demonstrated need; read installed Next.js guides before editing frontend code.
- Frontend paths beginning `src/` below are relative to `apps/ops-console/`; all other file paths are repository-relative.
- Alpha bounds: 100 active property definitions and 100 tags per tenant; at most 100 property values, 100 tag IDs and 20 structured references per booking; search text 250 characters; property text 2,000 characters; finite property decimals precision 30/scale 12; reference values 500 characters and source namespaces 100 characters; comments retain the existing 10,000-character bound.

## Review Focus

1. Legacy idempotency rows must still replay after new optional defaults are added (Task 3).
2. Uncertain submission outcomes must not generate a new key or mutate the retry payload (Tasks 3, 5).
3. False/zero and decimal precision must survive form, API and detail serialization (Tasks 1, 3, 5, 6).
4. Retired property definitions and changed requiredness must not reinterpret old trades (Tasks 1, 2, 6).
5. Switching tenant or retiring a selection between review and confirmation must reject safely (Tasks 3, 4, 5).

## Task 1: Tenant property/tag persistence and provisioning

**Files:** modify `security_master_schema/models.py`; create `alembic/versions/20260930_50_trade_properties.py`, `apps/reference_api/trade_properties.py`, `scripts/provision_trade_properties.py`, `tests/test_trade_properties.py`; extend `tests/test_schema_metadata.py`.

**Interfaces:** Export `m.trade_property_definition`, `m.trade_property_value`, `m.trade_tag`, `m.trade_tag_assignment`. In `trade_properties.py`, define `provision_trade_catalogue(connection, tenant_id, actor_id, definitions, tags) -> None`, validating tenant-admin trading permission and preserving immutable meaning. Provisioning script accepts explicit tenant/actor and JSON configuration; no tenant-wide destructive reset.

- [ ] Write `test_trade_property_assignments_are_unique_and_tenant_consistent`: duplicate trade/definition and trade/tag assignments fail; a definition/tag from another tenant cannot attach to the trade's strategy tenant. Write `test_property_meaning_cannot_be_rewritten`: type/choices/requiredness changes require a new definition; audited retirement is allowed.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/test_trade_properties.py -q`; observe failure because registry persistence is missing.
- [ ] Add registry tables with tenant/code uniqueness, actor/time evidence, controlled type/status checks, and child assignment uniqueness. Property values use validated JSON scalars (decimal strings, real booleans, ISO dates), not arbitrary documents. Add database checks/triggers that bind assignment tenant to the trade strategy and registry tenant; foreign keys alone must not permit cross-tenant attachment. Keep the existing `trd.trade` ownership model.
- [ ] Add migration revision `20260930_50`, predecessor `20260930_49`, after verifying Alembic heads at execution time. Create database protection against changing definition meaning and assigned values in place; allow audited retirement. Provisioning supports replacement definitions, not silent overwrite.
- [ ] Test provisioning denial for non-admin/missing entitlement, reserved standard-field codes, invalid choices, duplicate definitions and tenant separation. Seed optional examples only for the explicit demo tenant through the validated provisioning command; never make production tenants inherit demo requirements.
- [ ] Run focused schema/property tests after applying the additive migration to the local development database. Record migration and provisioning commands and counts in the delivery ledger. Do not downgrade or delete existing data.
- [ ] Commit only the task-owned migration, module, script and test/model hunks.

## Task 2: Booking-context API and tenant-scoped lookups

**Files:** modify `apps/reference_api/contracts.py`, `apps/reference_api/main.py`, `apps/reference_api/trade_properties.py`; create `tests/test_trade_booking_context.py`.

**Interfaces:** Add `TradePropertyDefinitionView`, `TradeTagView`, `TradeTraderOption`, `TradeBookingContextResponse`; expose `GET /v1/trades/booking-context` for active definitions/tags and actor context. Expose `GET /v1/trades/traders?q=&limit=` for bounded eligible-person search. Existing `/v1/organisations` remains the shared organisation search.

- [ ] Write tests: context returns only the caller tenant's active catalogue; traders exclude revoked/out-of-period memberships, inactive people/accounts and other tenants; duplicate account memberships return a person once; missing authority is denied.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/test_trade_booking_context.py -q`; observe missing endpoints/behavior.
- [ ] Implement `get_trade_booking_context(connection, tenant_id, actor_id) -> TradeBookingContextResponse` and `list_trade_traders(connection, tenant_id, query, limit) -> list[TradeTraderOption]`. Require the same `TRADE_WRITE` policy used by booking. Validate `q` length and `limit` 1-100. Registry results are deterministic and bounded (maximum 100 definitions/100 tags in the alpha); reject provisioning over that bound rather than silently truncate required fields.
- [ ] Run context/property tests; confirm no cross-tenant IDs or labels leak.
- [ ] Commit task-owned changes.

## Task 3: Enriched atomic booking and read-back contracts

**Files:** modify `apps/reference_api/contracts.py`, `apps/reference_api/repository.py`, `apps/reference_api/trade_properties.py`, `apps/reference_api/main.py`, `tests/test_trade_booking.py`, `tests/test_trade_booking_api.py`; create `tests/test_trade_booking_enrichment.py`; regenerate `packages/api-contracts/openapi/reference-data-api.v1.json` and `packages/api-contracts/src/generated.ts`.

**Interfaces:** Extend `TradeBookingRequest` with `executingBrokerOrganisationId`, `traderPersonId`, `tradePurpose`, `marketActivity`, `tagIds`, `properties: [{definitionId, value}]`, `externalReferences: [{referenceType, referenceValue, sourceSystemId?}]`. Purpose enum is `INVESTMENT|REBALANCING|HEDGING|OTHER`, activity `PRIMARY|SECONDARY|null`; `OTHER` needs comment. Reference types are `SOURCE_TRADE_ID|CLIENT_REFERENCE|BROKER_REFERENCE`; preserve `externalReference` and reject using both legacy/new references. Add detail `properties`, `tags` and `traderName` without removing existing fields. Existing `book_listed_cash_trade(...) -> TradeDetailResponse` remains the command.

- [ ] Write parametrized enriched BUY/SELL round-trip tests: same organisation in distinct roles, trader identity separate from booking actor, every property type (including false and zero), structured references and sorted tags. Assert actual persisted rows and read response, not mocked inserts.
- [ ] Add rejection tests: inactive/unknown organisations, trader outside membership, invalid choice/date/decimal, duplicate IDs/references, missing required properties, cross-tenant tags/definitions, and `OTHER` without note. Assert no trade/child/lifecycle/idempotency row survives rejected API commands.
- [ ] Add legacy replay fixture: persist the fingerprint of the pre-enrichment minimal request, then replay it after schema extension. Add equivalent reordering and changed-property conflicts. Run `.venv\Scripts\python.exe -m pytest tests/test_trade_booking_enrichment.py -q` and observe missing behavior.
- [ ] Validate the complete enriched request before inserting any child. Use row locks/revalidation to prevent catalogue retirement races; wrap API writes in the existing transaction/savepoint. Persist roles and references through existing tables; insert tags/properties through Task 1 structures. Keep sign, derived listing facts and original lifecycle semantics.
- [ ] Preserve pre-enrichment hash generation when no new enrichment is supplied (old request fields/defaults exactly); otherwise canonicalize explicit enrichment with sorted unordered sets and normalized decimal values. Replay the stored response path before applying new requiredness rules. Do not turn an existing successful booking into a failed retry after definition retirement.
- [ ] Extend detail reads after tenant ownership is resolved. Include retired definitions/tags and immutable values; older trades have empty arrays. Add safe field-associated problems for enrichment validation rather than losing the field path in a generic 422.
- [ ] Run booking/context/property/history tests. Run `pnpm contract:export`, `pnpm contract:generate`, `pnpm contract:check`; prove generated TypeScript reproducibility by rerunning generation and comparing hashes when pre-existing dirty generated files make a HEAD-based check unsuitable.
- [ ] Commit task-owned hunks and generated artifacts without staging earlier unrelated history work.

## Task 4: BFF, client contracts and tenant-context protection

**Files:** modify `apps/ops-console/src/app/api/trades/route.ts`, its `route.test.ts`, `src/lib/browser-api-client.ts`, `src/lib/reference-api-client.ts`, `src/lib/trades.ts`; create `src/app/api/trades/booking-context/route.ts`, `src/app/api/trades/traders/route.ts` and their tests.

**Interfaces:** Export `getTradeBookingContextFromBff(fetchImpl?)` and `searchTradeTradersFromBff(query, fetchImpl?)`. Enriched ticket sends `X-Expected-Tenant-Id` as a consistency check, never authority; actual upstream tenant/actor remain session-derived. Require expected tenant on enriched requests, retaining legacy compatibility only for unenriched requests.

- [ ] Write tests for forwarding all enriched fields, rejecting expected/current tenant mismatch before upstream writes, ignoring forged actor headers, lookup authority and safe upstream field errors.
- [ ] Run focused BFF/client tests and observe missing behavior.
- [ ] Implement narrow lookup BFF routes and session consistency guard. Bound queries/limits. Return RFC-style safe errors through existing helpers. Update generated/manual client read types consistently, with optional arrays tolerated for old fixtures during rollout.
- [ ] Run `pnpm test:ops-console` and `pnpm typecheck:ops-console`.
- [ ] Commit task-owned changes.

## Task 5: Sectioned ticket, typed properties and review/retry state

**Files:** modify `src/app/trades/new/page.tsx`, `trade-ticket.tsx`, `trade-ticket.test.tsx`, `src/app/globals.css`; create adjacent `ticket-model.ts`, `ticket-model.test.ts`, `party-fields.tsx`, `property-fields.tsx`, `booking-review.tsx` and rendered-component tests under `apps/ops-console`.

**Interfaces:** `buildEnrichedTicketPayload(listing, draft, context) -> TradeBookingRequest`; `validateEnrichedTicketDraft(draft, context) -> {field: string, message: string}[]`; `grossConsideration(quantity: string, price: string) -> string`. State modes: `EDITING|REVIEW|SUBMITTING|RETRY_REQUIRED|BOOKED`. Hold a submitted `{payload, key, expectedTenantId}` snapshot for uncertain outcomes.

- [ ] Write lightweight tests for all typed controls, property false/zero, required-field errors, exact multiplication (`0.1 * 0.2 -> "0.02"`), normalized payloads and full review contents. Add state tests proving Back to edit preserves values and retry reuses an unchanged snapshot/key. Run focused Vitest tests and observe missing behavior.
- [ ] Load booking context on the server and pass expected tenant/actor to the ticket; fail closed if required catalogue cannot load. Preserve dedicated listing search. Extract model logic and focused party/property/review components, leaving route orchestration small.
- [ ] Add counterparty/broker organisation search using existing BFF, eligible trader search via Task 4, purpose/activity controls, repeatable references, controlled tags and type-specific property inputs. No raw JSON or inline definition authoring. Retain listing facts, positive economics, fixed type, settlement default/override behavior and current product boundary.
- [ ] Implement decimal-string multiplication without binary floating-point rounding. `BOOLEAN` control has unspecified/true/false, not a checkbox that confuses absent with false. Limit text/decimal precision/reference/property counts according to API validation; the UI cannot silently drop unsupported values.
- [ ] Add accessible linked error summary and field messages, focus handling, expanded error sections, loading/status announcements and unsaved-change warnings. Preserve values after errors. Cancel exits to history with a discard check where needed.
- [ ] Implement review/edit/confirm and uncertain-outcome retry. Disable duplicate confirmation in flight. Keep retry payload immutable; explain conflict without rotating key. A new ticket is explicit and separate. Requiredness/stale status changes are rechecked server-side when confirming.
- [ ] Run the full console suite, TypeScript and production build. Commit task-owned frontend changes selectively, preserving earlier settlement/history edits.

## Task 6: Detail read-back, robust verification and delivery evidence

**Files:** modify `src/app/trades/[tradeId]/page.tsx`, `src/app/trades/trade-history-page.test.tsx`, `src/lib/trades.ts`; create `docs/delivery/enriched-trade-booking-alpha.md`; update tenant-workspace delivery and research evidence register. Add missing robust cases to Task 1-5 test files.

**Interfaces:** Existing tenant detail route displays `properties`, `tags`, named trader and role-specific parties. History remains compact and its filters/navigation unchanged; new property-search/filter modules are deferred.

- [ ] Write rendered detail tests covering false, zero, precision, retired definitions/tags, party-role labels, trader versus booker, and old trades with empty arrays. Run targeted tests and observe missing display.
- [ ] Add complete enrichment rendering without inferring missing values or changing historical property meaning. Preserve history return URLs, existing fee/lifecycle/reference sections and safe tenant reads.
- [ ] Run `.venv\Scripts\python.exe -m pytest` (complete suite), `pnpm test:ops-console`, `pnpm typecheck:ops-console`, `pnpm build:ops-console`, contract checks and `git diff --check`. Record actual failures/warnings, not just counts.
- [ ] Exercise local browser search, parties, typed properties, review/edit, stale/missing selections and detail read-back. Use rollback-backed integration records or the local synthetic fixture; never submit a real financial trade. Confirm the running development app has the additive migration and demo provisioning, and make it available for user review.
- [ ] Document exact verification evidence, source applicability, provisioning instructions and limitations. Update the execution ledger after each task; keep commentary updates during long test runs.
- [ ] Obtain one fresh-context read-only review of the scoped enrichment diff, fix substantive findings with failing regressions, rerun affected/full checks as appropriate, and hand off the finished feature. Do not merge/push without user request.

## Self-review

The six tasks cover the approved sections and use existing routes, persistence
and policy. The five review-focus cases each have named tests. Shared catalogue
eligibility and member-only traders follow the specification rather than implying
new onboarding. Minimal provisioning is included; a full configuration editor,
fees, arbitrary-property reporting and new booking products remain outside scope.

No tests have been run for the proposed implementation yet. Plan review and
execution-method confirmation precede implementation under the planning skill.
