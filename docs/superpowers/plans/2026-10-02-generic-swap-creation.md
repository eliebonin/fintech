# Generic Swap Creation and Booking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development if the user selects delegation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and approve tenant OTC performance swaps, then book against their versioned generic terms.

**Architecture:** Extend the existing proposal and product-booking flows. A focused typed generic definition stores additional contract economics without changing historical legacy swap interpretation. Creation and booking use one authoritative definition, with immutable booking evidence.

**Tech Stack:** Python/FastAPI/Pydantic, SQLAlchemy/PostgreSQL/Alembic, Decimal; Next.js 16.3.4, React, TypeScript, Vitest, generated OpenAPI contracts.

**Spec:** [Approved generic swap design](../specs/2026-10-02-generic-swap-creation-design.md), approved in chat on 2026-10-02.

**Status:** Implemented and isolated alpha acceptance completed2026-10-05. Tasks1–5 were subagent-driven and independently reviewed; the user then switched to sequential execution. Whole-feature review found two Important product defects; both reproduced and corrected, with direct fix inspection. Fresh full verification:696 Python/403 frontend passed, build/typecheck/contracts passed. User-authorized browser approval, booking and history completed on two mock contracts/four mock trades. No operating activation or push. See [execution evidence](../../delivery/generic-swap-execution-log.md).

## Global Constraints

- Creation first; booking then consumes those same terms.
- Funding is optional; first executable funding selector uses governed rate indices.
- Contractual notional and booked notional may differ; no aggregate contractual-capacity enforcement.
- Whole-swap quote uses `SWAP_VALUE_PER_NOTIONAL`; quote divisor is positive. Quote currency matches notional currency.
- `entry reference value = signed booked notional × execution quote ÷ quote divisor`; do not multiply contractual notional or leverage again.
- No automatic upfront cash trade, valuation, payment processing, termination/reset engine, or schedule generation.
- Preserve legacy eligibility, historic snapshots, idempotency, tenant permissions, and private-reference boundaries.
- Lightweight tests before implementation; broader integration/browser/full-suite checks after the working slice.
- No dependency additions, operating-database activation, or GitHub push implied by this plan.

## Review Focus

1. Funding switched off after input must clear dependent payload values, not retain an invisible spread (Task 3).
2. Excess-return references plus separate financing require explicit source-backed acknowledgement (Tasks 1–2).
3. References retired or made private between proposal submission and approval must reject atomically (Task 2).
4. Zero quotes and a 2x leveraged contract must retain exact booked-notional arithmetic (Tasks 4–5).
5. A new definition must not change historical snapshots or old idempotent replay results (Task 4).

## Task 1: Typed economics and versioned storage

**Files:** Create `apps/reference_api/swap_creation_contracts.py`, `tests/test_swap_creation_rules.py`, and `alembic/versions/20261002_60_generic_swap_definitions.py`; modify `security_master_schema/models.py` and `apps/reference_api/product_booking_contracts.py`.

**Interfaces:** Define `GenericSwapTerms` and `SwapProposalRequest` in the new contract module. Add nullable `genericTerms: GenericSwapTerms` to `SwapDetailsView`, and make existing funding view fields nullable for no-funding generic swaps while retaining their legacy values. Add table `swap_definition_version`, keyed by `instrument_definition_version_id`, storing schema version and validated economics JSON.

- [ ] Write pure failing tests for positive notional/leverage/factor, dates, quote currency alignment, optional funding, and `150 bp = Decimal('0.015')`. Reject funding-dependent values with no funding, non-finite decimals, and excess-return/separate funding without acknowledgement and evidence.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/test_swap_creation_rules.py -q`; confirm failures concern missing contracts, not fixture/environment errors.
- [ ] Implement strict contracts: core references/amounts/dates/direction/return profile/leverage; optional funding with spread, nominal basis, day count, calculation method, observation description, reset/payment frequency; performance frequency/custom schedule description; redemption rule/continuation description; source evidence. Use Decimal strings, not floats. Map enums to the exact choices in the spec.
- [ ] Verify Alembic head before finalizing revision 60. Add definition table and FK without rewriting revision 59 or populating guessed economics into legacy rows. Enforce one generic definition per instrument definition version.
- [ ] Run pure tests plus isolated migration/schema round-trip tests; commit the verified storage/contracts slice.

## Task 2: Proposal validation and atomic approval

**Files:** Create `apps/reference_api/swap_creation.py` and `tests/test_swap_creation_api.py`; modify `apps/reference_api/product_booking.py`, `product_booking_routes.py`, and `repository.py`.

**Interfaces:** `validate_swap_references(connection, tenant_id, terms: GenericSwapTerms, *, lock=False) -> dict` returns canonical checked reference facts. `materialize_swap(connection, tenant_id, actor_id, request: SwapProposalRequest) -> UUID` writes one approved canonical instrument. Add POST `/v1/instruments/swap-proposals` returning the same proposal response as future creation. Dispatch `CREATE_SWAP` through existing submit/approve/reject infrastructure.

- [ ] Add failing isolated API tests for no-funding and rate-funded proposals; approval creates canonical SWAP, approved definition, generic payload, dates, convention, performance leg, and funding leg only when specified. Assert the proposal appears in both creation requests and Operations.
- [ ] Test tenant/module/role denial, hidden/unapproved/retired references, swap-on-swap references, non-rate funding references, and concurrent/duplicate approval. Change reference visibility/status after proposal submission and assert approval fails with no partial instrument rows.
- [ ] Run `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py tests/test_swap_creation_api.py -q`; verify expected new-behaviour failures.
- [ ] Implement reference checks for visible approved active instruments and active indices; validate governed return profiles against funding treatment. Recheck and lock at approval. Materialize atomically through existing transaction/error conventions; do not create placeholder schedules.
- [ ] Extend request filtering, queue title/details, and approval dispatch for `CREATE_SWAP`, without changing unrelated proposal types.
- [ ] Run isolated creation tests and `tests/test_product_booking_api.py`; commit the verified backend creation flow.

## Task 3: Creation form, review, and instrument details

**Files:** Create `apps/ops-console/src/components/swap-creation-form.tsx` and its `.test.tsx`, `src/app/instruments/swaps/new/page.tsx`, and `src/app/api/instruments/swaps/route.ts` with `.test.ts`; modify `src/lib/instrument-create-options.ts`, `reference-api-client.ts`, and `instrument-requests.ts`. Extend the existing instrument detail renderer reached from `src/app/instruments/[instrumentId]/page.tsx` after confirming its actual location. Regenerate existing OpenAPI/TypeScript artifacts through repository commands.

**Interfaces:** `SwapCreationForm({tenantId}: {tenantId: string})` submits the Task 2 request through POST `/api/instruments/swaps`. `submitSwapProposal(context, request: SwapProposalRequest)` in the API client follows future-proposal authentication/error handling. Server page enforces existing creation permissions and wraps `WorkspaceShell`.

- [ ] Read `apps/ops-console/AGENTS.md` and relevant bundled Next docs before code. Confirm exact detail-rendering file in the execution log rather than creating a parallel detail subsystem.
- [ ] Write failing UI/BFF tests for reference lookup, four form groups, funding off/on/off payload clearing, precise spread conversion, review/back/edit preserving values, conditional custom/source requirements, and pending-not-approved submission copy. Include tenant switch and upstream field errors.
- [ ] Run focused Vitest paths under `pnpm --filter ops-console test`; establish the new failures.
- [ ] Implement the Swap creation card and page, searchable reference/rate selection, conditional funding controls, required quote convention, and review step. Default leverage to 1 but never default unknown contractual rates or quote divisor. Explain nominal distinctions and redemption rules.
- [ ] Render approved generic terms and reference links in instrument details; keep legacy swap display intact. Add `CREATE_SWAP` to frontend request classification if it maintains its own whitelist.
- [ ] Run `pnpm contract:export`, `pnpm contract:generate`, focused frontend tests, `pnpm typecheck:ops-console`, and contract checks. Commit the verified creation UI.

## Task 4: Generic booking context and immutable trade evidence

**Files:** Create `apps/reference_api/generic_swap_booking.py` and `tests/test_generic_swap_booking_api.py`; modify `apps/reference_api/swap_booking.py`, `product_booking.py`, and existing swap API tests as needed.

**Interfaces:** `load_generic_swap_context(connection, tenant_id, instrument_id, as_of, *, lock=False) -> tuple[SwapDetailsView, date]` loads the approved typed definition and checked references. The existing `load_swap_context` dispatches here only when the current approved definition has generic terms; otherwise its legacy rules remain unchanged.

- [ ] Add failing context/booking tests for optional funding, non-autocall reference, independent contractual/booked nominal, date boundaries, and source facts. Assert a 1m contractual / 400k booked / 2x leverage / quote 2 / divisor 100 trade has entry value 8000, not 16000 or an amount involving contractual nominal.
- [ ] Test zero/negative quotes and SELL orientation using the existing amount helper. Verify one trade plus BOOKED evidence, no automatic cash events, required custom properties, and no settlement-date invention.
- [ ] Test stale definition/reference/funding edits, private/retired references, persistence rollback, historical snapshot unchanged after current terms change, and legacy replay unchanged.
- [ ] Run isolated generic booking tests to demonstrate missing functionality; implement context loader, complete fingerprint/locking, and snapshot including both nominal amounts and all approved terms. Reuse existing booking arithmetic/writer rather than duplicate it.
- [ ] Run isolated new and legacy swap tests plus product/history regressions; commit the verified generic booking backend.

## Task 5: Generic swap booking ticket

**Files:** Modify `apps/ops-console/src/app/trades/new/product-ticket.tsx`, `product-ticket-model.ts`, `swap-ticket.test.tsx`, and `src/lib/trade-history.ts` with its tests. Reuse existing swap booking BFF rather than add a second endpoint.

**Interfaces:** Existing product context now exposes `swapDetails.genericTerms`; ticket uses its contractual nominal for initial quantity only. Submission still uses `ProductBookingRequest.quantity` as booked nominal and the existing terms fingerprint.

- [ ] Add failing tests for initial nominal prefill, editable partial nominal, no-funding display, rate-funded display, total/excess acknowledgement facts, reset/payment/redemption terms, and immutable review/back/edit. Verify a user-edited quantity is not overwritten on an ordinary rerender.
- [ ] Add tests for 2x leverage/whole-swap quote showing 8000 for the Task 4 example, zero/negative quotes, BUY/SELL, and unchanged custom-field submission.
- [ ] Run focused ticket/history tests; implement conditional generic rendering and nominal prefill without duplicating party/property/navigation machinery. Preserve legacy ticket behaviour and clear stale draft data on instrument/tenant changes.
- [ ] Ensure history/details read booked snapshot facts, show both nominal amounts, and never relabel entry reference value as an upfront payment or verified MTM.
- [ ] Regenerate contracts if needed, run focused tests/typecheck/contracts, and commit the verified booking UI.

## Task 6: End-to-end verification and delivery documentation

**Files:** Create `docs/delivery/generic-swap-creation-and-booking.md` and `docs/delivery/generic-swap-execution-log.md`; update `docs/delivery/README.md`, this plan's status, and the earlier swap alpha document with a link distinguishing legacy from new generic support.

- [x] In an isolated database/browser environment, create and approve one no-funding swap and one funded swap. Verify creation requests, Operations, instrument details, booking search, review/edit, custom fields, and trade history. Record exact environment and synthetic inputs; do not create operating test trades.
- [x] Add regression tests for acceptance-triage defects and rerun affected focused tests. No approval-dependent walkthrough defect can be assessed yet.
- [x] Run `.venv\Scripts\python.exe scripts/run_isolated_python_tests.py -q`, `pnpm test:ops-console` (maxWorkers=2), `pnpm typecheck:ops-console`, `pnpm build:ops-console`, `pnpm contract:check`, and `pnpm contract:generate:check`. Exact full failures and focused repairs are recorded; this is not an all-green full-suite claim. Browser/final review completion is still required.
- [x] Perform whole-branch review under the selected execution workflow. Fix and retest material findings before claiming completion. Final fix inspection performed directly under the user's sequential/no-subagent instruction.
- [x] Document implemented creation/approval/booking, quote and nominal rules, rate-index restriction, no automatic cash/lifecycle/valuation processing, primary research links, and operating activation status. Commit verified delivery docs; no push or operating activation.

## Self-review

All spec sections map to tasks: typed economics/storage (1), creation governance (2), creation UX/details (3), booking safety and compatibility (4), ticket/history (5), verification/documentation (6). The five review-focus risks have named tests in their owning tasks. Interface names and quantity/quote interpretation agree throughout. No generated schedules, automatic cash processing, or operating activation were introduced as hidden prerequisites.
