# Project state and high-level roadmap — 2026-10-05

**Status:** Review complete; recommendations proposed, not new policy  
**Content type:** Dated engineering review  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-10-05

## Conclusion

The platform has a credible **instrument-to-booking alpha**, not yet a complete investment-management platform. Tenant context, strategies, governed instrument proposals/listings, trade annotations and several product-specific tickets form a substantial working vertical slice. Lifecycle processing, positions, valuation and production identity are materially less complete. The next milestone should consolidate the booking foundation and then close the trade-to-position lifecycle, rather than keep adding tickets indefinitely.

Generic swap creation/booking is now alpha-accepted in an isolated environment. It has not been activated in the operating database. Detailed implementation, four mock browser bookings and remaining limitations are in the [swap delivery record](../generic-swap-creation-and-booking.md) and [execution log](../generic-swap-execution-log.md).

## Review coverage and confidence

Repository-wide inventory and domain review covered architecture/product/platform indexes, governance and delivery records, API/UI entry points, migrations/schema, contract generation, CI, tests and seed tooling. Detailed code inspection concentrated on tenant/session boundaries, governed configuration, product booking, market-data resolution, cash P&L, Soft NAV and lifecycle helpers. Approximately 520 maintained files were inventoried, excluding dependencies, build outputs and archived copies.

This is **not a claim that every line of every file was read**, a penetration test, a licensing/legal assessment or production certification. Earlier delivery/browser records provide historical evidence for other tickets; fresh browser acceptance in this pass covered generic swaps. Fresh full test suites cover the current checkout. Operating deployment state, load, disaster recovery and every provider integration were not revalidated.

Code baseline: `codex/enriched-trade-booking`, implementation commit `0c43108`. Recommendations below are review findings; no unrelated runtime fixes were made during this review.

## What is genuinely delivered

| Area | Current usable capability | Important boundary |
|---|---|---|
| Tenant workspace | Membership-aware switching, tenant profile/modules and action checks | Demo identity seam, not authenticated support impersonation or tenant provisioning |
| Strategies | Tenant-scoped register, classifications and creation | Not a full fund/AMC administration workflow |
| Instruments | Search/pagination/details, creation requests, steward approval, contextual listing creation and Operations inbox | Product eligibility and approved/current definitions matter; not every schema type is operational |
| Trade configuration | Standard-party eligibility; typed custom fields; tenant catalogues, versioned entries and retirement | No full MDM, dependent fields, bulk import or maker-checker configuration |
| Cash tickets/history | Dedicated booking, parties/tags/properties, review/edit, immutable history/detail and durable retries | Already-executed manual trades, not orders/fills/allocation or cash accounting |
| FX forwards | Single-trade deliverable booking with explicit currency obligations and term-derived settlement | No NDF/FX-swap, settlement engine or forward valuation |
| Options | Listed vanilla premium booking, integer contracts, shared OPEN/CLOSE intent | No holdings check, exercise/expiry processing or options valuation |
| Structured products | Listed/OTC funded-security booking with governed quotation/unit conventions | Not a payoff engine or every possible structured derivative |
| Futures | Family → canonical contract → listing; month/year conventions, multipliers, cash-settled index booking | Physical/crypto futures creation does not imply booking, delivery or margin support |
| Bonds | Supported fixed/zero-coupon nominal booking, CLEAN/DIRTY and recorded accrued interest | Manual execution accrual, not coupon/accrual calculation or all bond types |
| Swaps | Generic reference/funding terms, contractual/booked nominal, whole-swap quote, immutable snapshots; legacy path preserved | No automatic payment, funding accrual, reset, termination or swap MTM engine |
| Market data | Series/observations, provenance, cut/policy/entitlement resolution and persisted selection evidence | Not uniformly consumed by all calculations; external feeds need operational validation |
| Valuation | Display-only cash P&L and a separate constrained Soft NAV service | Not authoritative multi-product NAV or accounting |

For product-specific evidence and limits, use the [delivery index](../README.md), not old test totals or a table's existence as proof of a delivered workflow.

## Strengths worth preserving

- Contract terms and execution are separated. Booking snapshots preserve agreed facts rather than recomputing old trade economics from today's master data.
- Exact decimal calculations, authoritative eligibility/fingerprint checks, transactional annotation writes and durable booking idempotency are consistently important design choices.
- Governed custom fields use identities and versions, not a fixed set of repurposable Field X columns. Retirement preserves history.
- Instrument creation and review are attributable workflows, with separate listings and a discoverable operational queue.
- Real PostgreSQL tests, generated-contract checks and isolated browser evidence complement unit tests. Unsupported derivative valuation is explicitly refused rather than included in a partial cash total.

## Biggest weaknesses and drift

### 1. Identity is an alpha seam, not a production security boundary

The API accepts tenant/actor headers in [`tenant_context.py`](../../../apps/reference_api/tenant_context.py). Membership checks are useful, but do not prove the caller's identity. The console's [`tenant-session.ts`](../../../apps/ops-console/src/lib/tenant-session.ts) still supplies `DEMO_USER_ACCOUNT_ID` (including a fallback); a signed tenant-selection cookie is not a login system. [`packages/auth`](../../../packages/auth/README.md) is a placeholder.

Before external use, establish verified identity, bind it to selected tenant membership, protect the API/header trust boundary, and test denied access on every protected path. This is a production blocker, not evidence that local membership checks are absent. OWASP recommends treating client tenant identifiers as selectors and binding context to verified identity and current authorization. [OWASP multi-tenant guidance](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html).

### 2. Documented isolation topology is ahead of deployed code

The [tenancy architecture index](../../architecture/tenancy-and-entitlements/README.md) describes shared canonical data plus isolated tenant overlay databases. The API currently obtains connections from one configured engine in [`db.py`](../../../apps/reference_api/db.py). [`tenant_routing.py`](../../../security_master_schema/tenant_routing.py) supplies a tested selection primitive, not integrated request routing.

Choose and document the actual deployment model before real tenants: shared database with systematically enforced tenant boundaries, or genuinely routed overlays. Neither architecture is automatically correct for all deployments. PostgreSQL RLS can add defense in depth to shared tables, but owner/bypass-role behavior must be designed and tested; it is not a substitute for identity. [PostgreSQL 18 row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html).

### 3. Cash P&L has dangerous approximation paths

In [`repository.py`](../../../apps/reference_api/repository.py), `portfolio_pnl` chooses demo cuts from strategy-code suffixes, uses limited seeded FX pairs, returns FX 1:1 when conversion is unavailable, and silently skips trades without opening/closing observations. Its direct series selection differs from the governed resolution service and does not visibly apply that service's entitlement/policy pathway. The route checks membership; this review has not demonstrated a specific cross-tenant exploit.

The display-only label limits its intended use but does not make an apparently complete numeric total safe. Before promoting this view, fail closed or expose explicit incomplete coverage; remove guessed FX; use one governed resolver. Until then, treat it as demonstration output, not fund performance. This is the highest financial-correctness risk observed, separate from the intentionally unsupported derivatives.

### 4. Position and lifecycle closure are not delivered end to end

Shared OPEN/CLOSE metadata records execution intent; it does not check lots or settle/expire exposure. Lifecycle helpers and corporate-action derivation code exist, but they do not amount to an operator workflow for delivery, maturity, option exercise, swap resets, cash entitlements and termination.

The next major domain slice should produce explicit effective-dated events and reproducible positions, separating economic recognition from payment/settlement status. Do not manufacture opposite trades solely to hide matured exposure. This is a project recommendation; FINOS CDM's separation of product terms and lifecycle concepts is useful evidence, not a requirement to implement the entire CDM. [FINOS product model](https://cdm.finos.org/docs/product-model/).

### 5. The two calculation paths are converging too slowly

The [`soft_nav_service.py`](../../../security_master_schema/soft_nav_service.py) deliberately refuses unresolved inputs and unsupported FX/cash/accrual. That is a stronger fail-closed foundation than the display P&L pathway, but remains a constrained service rather than the full operator experience.

The governed resolver converts database decimals into `float` candidates, then back into Decimal (`market_data_resolver.py`, candidate construction and selected-value conversion). Remove that precision round-trip before authoritative valuation. Product-dispatch rules, frozen conversion/convention inputs and reconciliation need their own acceptance criteria; do not assume a generic quantity × price engine supports every newly bookable product.

### 6. Delivery documentation and modularity need consolidation

The root README is only a heading. API and console READMEs describe older slices. The tenant workspace delivery record still states an initial cash-only exclusion list despite later extensions; newer product records are more accurate. Canonical topology/capability documents mix intended architecture with current delivery. Some plans retain unchecked historic task boxes despite completed status.

`repository.py` is 5,221 lines and `main.py` 1,057 lines at this baseline. Product services are a useful start, but shared locking, eligibility, annotations and wire-decimal rules can drift between paths—as the final swap defects demonstrated. Extract stable boundaries incrementally with behavior-preserving tests; no wholesale rewrite is warranted.

### 7. Test success is not operational readiness

CI checks Python/PostgreSQL, frontend tests, type/build, contracts and secrets. Browser cycles remain separately recorded, not a regular automated CI gate. Seed/master inconsistencies, migration sequencing, recovery, monitoring, capacity and deployment rollback need controlled operational exercises. Existing deprecation/schema warnings should be owned rather than hidden.

## High-level way through the project

1. **Consolidate the booking foundation.** Refresh entry documentation and capability matrix; resolve identity/isolation before external access; align migrations and deployment; add repeatable end-to-end smoke checks. Keep UX refinements bounded and preserve current tickets.
2. **Close the economic lifecycle.** Positions/lots where needed, correction/cancellation, maturity/delivery/expiry and basic linked cash entitlements with separate payment status. Begin with one cash/bond or FX maturity flow before generalizing.
3. **Unify market-data consumption.** One policy/cut/entitlement resolver, exact values, explicit missing-data decisions and frozen provenance. Remove the display P&L shortcuts before relying on its totals.
4. **Build authoritative valuation progressively.** Cash and supported bonds first; then FX forwards, options, futures and swaps with product-appropriate inputs. Reconcile against independent/custodian evidence before attribution or exposure reporting is called reliable.
5. **Operationalize and selectively expand.** Ingestion/reconciliation, alerts, recovery and tenant onboarding; then richer products, margin, accounting and reporting according to demonstrated user demand. Schema breadth alone should not drive the roadmap.

These are proposed milestones, not authorization to implement every item now. The immediate recommendation is consolidation plus lifecycle design, not another large product family.

## Fresh verification and swap completion

- Python: **696 passed**, 481 warnings, 20m26, isolated runner, exit 0.
- Frontend: **403 passed across 95 files**, exit 0.
- Typecheck, production build, API export and generated-contract reproducibility: exit 0.
- Isolated UI 3003/API 8003: two swap approvals and four booked trades, covering funded/unfunded, partial nominal, BUY/SELL, zero/negative quotes, custom properties, edit/review and saved history.
- Final fixes: exact scientific-notation parsing of actual API decimal JSON; consistent shared-reference lock ordering across legacy/generic swaps. Both had failing regressions before correction.
- Test services/tab were stopped/closed; synthetic database retained as evidence. No operating migration/restart, GitHub push or production sign-off.

Remaining minor swap observations: raw JSON reference links; zero SELL displays `-0 GBP`/raw `0E-12`; one rapid-navigation destination-stream warning despite successful acceptance. Seed inconsistencies and existing warnings remain recorded. These are not claimed fixed by passing suites.

## Subagent versus sequential execution: observed results

Separate implementer/reviewer attention found a financing-profile bypass, real lock cycles, stale ticket navigation and a historical-heading issue. The final whole-feature review also caught actual wire-decimal parsing and a mixed-currency legacy/generic lock-order gap. Those are concrete benefits of independent attention, not proof that a lone implementer could never find them.

Costs were context transfer, repeated review/fix rounds, shared-checkout coordination and test-harness assumptions requiring browser validation. No controlled native-only comparison or reliable speed/cost counterfactual exists. More agents did not guarantee faster completion. Following the user's instruction, final fix inspection, full verification, browser acceptance and this review were performed sequentially without new subagents.

### Execution rulings and their costs

1. Used the user-selected current checkout/feature branch instead of a new worktree; preserved existing edits, accepting shared-checkout coordination risk.
2. Lightweight tests first, broad suites at acceptance rather than every task; reduced repeated long runs but postponed some cross-product failures.
3. Kept tenant identifier as typed generic-swap metadata with normalized submission, rather than inventing a catalogue; this adds a small contract surface.
4. Retained the existing independent review, then inspected fixes directly after the user prohibited further subagents; less fresh independent post-fix assurance, mitigated by RED/GREEN regressions, full suites and actual browser checks.
5. Deferred valuation, lifecycle engines, multicurrency swaps, amendments, capacity/load validation and operating deployment; kept booking alpha bounded, with explicitly incomplete production coverage.

## Best-practice applicability

Sources were opened/reviewed on 2026-10-05. PostgreSQL references match the project's PostgreSQL 18 environment. OWASP ASVS 5.0.0 provides a security-verification framework, not a claim of compliance here. [OWASP ASVS](https://owasp.org/projects/asvs/). Consistent lock acquisition follows PostgreSQL guidance; the concrete UUID ordering is this project's choice. [PostgreSQL 18 locking](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS).

The sources support verified identity, deliberate isolation, separation of contract/lifecycle concepts and concurrency discipline. The proposed sequencing, fail-closed P&L remediation and incremental extraction are conclusions from this codebase, not universal standards or a recommendation to adopt a large framework wholesale.
