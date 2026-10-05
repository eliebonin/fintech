# Shared booking controls

**Status:** Implemented and verified for the stated alpha scope

**Owner:** Engineering delivery team

**Last reviewed:** 2026-10-05

This reference describes consolidation, not a universal booking engine or production-readiness sign-off. Product formulas, forms, fingerprints, snapshots and endpoints remain distinct. See the [capability matrix](booking-capability-matrix.md) and [implementation plan](../superpowers/plans/2026-10-05-booking-consolidation.md).

## Authoritative write boundary

Every public cash, FX-forward, option and shared product writer uses `booking_controls.authorize_booking`: the actor account must be active and the effective tenant membership must permit `TRADE_WRITE` under existing role/module rules. This check precedes replay as well as new writes. HTTP permission checks remain defense in depth; they do not replace service authorization. This is not authentication of trusted identity headers, JWT integration, tenant database routing or serialized permission-revocation processing.

Each writer owns a SQLAlchemy savepoint. The caller owns the outer transaction and commit. Trade, annotations, initial BOOKED evidence and replay registration succeed together. A direct caller can catch a late persistence failure and continue using its outer transaction without retaining a partial cash booking. Helpers never commit.

For a new write, `lock_booking_strategy` requires an active strategy in the selected tenant. Product services retain their own locked authoritative instrument/terms eligibility, calculations and saved snapshot construction.

## Retry compatibility

The lock identity remains SHA-256 of `tenant + U+001F + endpoint + U+001F + key`, first eight bytes interpreted as a signed big-endian integer. The durable lookup remains tenant/endpoint/key scoped. A shared helper acquires the advisory transaction lock, reads replay evidence with `FOR UPDATE`, refuses a changed fingerprint, or returns the original trade ID. Missing saved trade evidence is a controlled error, not permission to create another trade.

Request normalization remains in each original product adapter. Cash normalization has not been broadened to match FX/option/product normalization. Historical omission, property canonicalization and collection ordering rules remain unchanged. No fingerprint migration or snapshot rewrite occurred.

An authorized exact retry returns saved history before checking current strategy, instrument, terms or catalogue eligibility. Retirement therefore cannot turn an uncertain successful booking into a second booking. An inactive/revoked actor cannot use the write endpoint to obtain a successful replay. Read access remains a separate concern.

## Concrete locking boundaries

These are actual path phases, not a claim that every resource in the application follows one global order:

| Phase | Scope and acquisition |
|---|---|
| Replay | Tenant/endpoint/key advisory transaction lock, then replay row |
| Product references | Existing product-specific locked loaders. Generic swaps acquire currency, then all reference identities/scopes in UUID order before shared type/profile catalogue phases; legacy swaps retain their ordered reference acquisition |
| Strategy | One active tenant strategy row, for new writes only |
| Annotation catalogue | Existing tenant `trade-catalogue` advisory transaction lock, shared with configuration/publication paths |
| Definitions / reference values / tags | Definitions and tags in UUID order; governed reference checks under the catalogue boundary |
| Counterparty and broker | Distinct shared organization IDs in UUID order, then separate role-specific tenant eligibility checks |
| Trader | Active person/account/effective tenant membership join, then curated trader eligibility |
| External references | Existing source/type/value namespaces in sorted tuple order, with advisory locks before duplicate checking |

The organization change fixes a demonstrated cross-tenant deadlock: one tenant selected A as counterparty/B as broker while another selected B/A. Tenant catalogue locks cannot serialize globally shared organization rows. The scheduled PostgreSQL regression first reproduced SQLSTATE `40P01`; ordered shared acquisition then passed. Missing/inactive organizations still produce the applicable party-field error.

Inventory included convention approval and product loaders (`product_booking`), swap reference validation/materialization (`swap_creation`), and catalogue/eligibility publication (`governed_trade_configuration`, `trade_configuration`, `trade_properties`). Catalogue management acquires the same tenant catalogue boundary before catalogue/record changes; booking remains product-reference-first and then annotation-catalogue. No blanket global lock or extra tenant-wide lock was introduced. Existing currency/reference locks and eligibility checks were not removed. Existing scheduled swap concurrency tests remain necessary. New combinations of product issuer/underlying locks and annotation locks must be reviewed before being enabled; this slice does not prove application-wide deadlock freedom.

## Browser and BFF boundaries

`booking-decimal` uses bounded decimal coefficients/scales and BigInt arithmetic. Number is used only for bounded scales, not consideration. Scientific API convention values are accepted exactly. Product consumers retain their formulas and sign/precision rules: zero is not absence, swap leverage is not applied twice, and bond DIRTY quotes do not add accrual twice. A nonrepresentable exact result is shown as unavailable rather than silently rounded. Legacy cash/FX multiplication previews retain their more permissive preview limits; authoritative execution validation remains server-side.

`booking-submission` clones and deeply freezes the reviewed payload together with its idempotency key and expected tenant. An uncertain retry uses that envelope rather than the current draft. Tickets retain their own edit/review/submitting/conflict states and discard protection.

`booking-write-guard` centralizes required key, JSON-object validation, selected server tenant and stale-tenant refusal. The actor is obtained from server context, never a browser header. Specialist tickets require the expected-tenant header. The historic unenriched cash API exception is retained explicitly; enriched cash requests still require it. Proposal semantics are unchanged. Malformed/non-object JSON now returns a controlled 400.

## Verification and limits

Focused evidence: 208 cross-product backend checks passed; 79 control/generic-swap checks passed after the lock repair; 59 decimal/model checks and 162 ticket/BFF checks passed. Complete isolated Python acceptance passed 723 tests with 479 warnings in20m21s. Full frontend rerun passed 435 tests in 98 files. The first full run had two import/load timeouts (433 passes), with no assertion failures; no code/test changes intervened before the successful rerun. Typecheck, production build and generated Python/TypeScript contract checks passed. Author self-review identified no new Critical/Important finding; remaining limitations and minor cleanup are explicit below.

Commands, final review and acceptance status are maintained in the [dated acceptance record](quality-reviews/2026-10-05-booking-consolidation.md).

Browser acceptance uses only API 8003/UI 3003 and the retained synthetic database `fortem_generic_swap_browser_20261005_6ef2829c`. Review of 250,000 nominal at -2 produced -5,000 GBP; back-to-edit changed the quote to zero without losing party/property details. Confirmation created synthetic trade `3b73f678-3906-445a-b6b9-6479ea655512`; detail showed zero value, 250,000 booked nominal versus 1,000,000 contractual nominal, the immutable snapshot, custom TEXT property and one BOOKED event. No cash entry was generated. This is ledger-recording acceptance, not execution of a financial order.

Cross-tab tenant acceptance: a cash draft reviewed in Demo Tenant calculated 10 × 1.23 = 12.3 GBP. After selecting Second Tenant in another tab, confirmation on the stale original ticket returned the explicit tenant-changed refusal and disabled confirm/edit; no backend booking was invoked. The test was not a second successful cash booking. Uncertain retry and envelope identity are covered by automated ticket-state tests, not a claimed browser fault-injection run.

No schema migration, dependencies, operating activation/restart, GitHub push, valuation/P&L or lifecycle processing is included. Review is sequential author self-review, not independent subagent sign-off.

## Execution rulings

- Execute after the user's explicit implementation approval, without another approval loop; cost: less opportunity to amend the task breakdown before edits.
- Use the previously selected existing feature checkout; cost: shared-checkout interference instead of worktree isolation.
- Self-review without subagents, following the user's instruction; cost: weaker independent assurance, mitigated by RED/GREEN and full suites.
- Preserve per-path fingerprint adapters and the explicit legacy-cash header exception; cost: a larger compatibility surface than one normalization rule.
- Keep the existing cash freeze helper's argument order and expected-tenant naming rather than the plan's illustrative signature; cost: initial interface-text inconsistency, corrected in the plan.
- Group the interconnected tasks into one verified implementation commit; cost: less granular bisect/revert than separate task commits.

Deferred: broad repository decomposition, management/authentication consolidation, general formatting cleanup, UI density/scientific-zero display, and exhaustive cross-resource concurrency proof. None is claimed fixed by this delivery.
