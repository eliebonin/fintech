# Instrument integrity review — 2026-10-05

**Status:** Review complete; findings not yet remediated

**Scope:** Instrument approval, required terms, tenant visibility and new-booking eligibility across the seven supported booking paths. Sequential review of commit `3856214`; valuation/P&L, amendments and post-booking lifecycle are excluded.

**Follow-up:** Item 2 (FX inactive-scope enforcement) is implemented in the [FX scope hardening delivery](2026-10-05-fx-scope-hardening.md). Items 1 and 3 are implemented in the [cash and approval integrity delivery](2026-10-05-cash-and-approval-integrity.md); follow that record for verification status and exact limits. Findings below describe the reviewed baseline, not the follow-up code.

## Conclusion

Booking consolidation standardized actor authorization, strategy checks, replay and transaction boundaries. It did not standardize instrument eligibility. The remaining reference checks differ materially between the older cash/FX paths and newer specialist tickets. Prior consolidation test results must not be interpreted as instrument-integrity acceptance.

Harden the existing boundaries before adding products. No general-purpose instrument engine or new lifecycle model is needed for this slice.

## Confirmed findings

### P1 — listed-cash writer does not enforce instrument integrity

`apps/reference_api/repository.py::_book_listed_cash_trade` checks active listing and listing reference node, then excludes specialist product types. It does not enforce tenant visibility of the listing and canonical parent, approved definitions, active/tradable parent, listing tradability, active currency/venue or agreement with listing effective dates.

Disposable-database checks confirmed successful booking with each of these conditions independently:

- Another tenant's private listing or private canonical parent.
- Inactive visibility scope or inactive canonical parent.
- A non-tradable listing.
- A newly created draft listing definition or draft parent definition.
- Inactive listing currency or venue.
- A listing effective after the execution date.

The foreign-private-listing case also returned HTTP **201** from `/v1/trades`; this is not limited to a repository helper. Frontend filtering is not an authorization boundary. The existing database immutability trigger correctly rejected attempts to modify existing approved definitions; the draft diagnostics instead created fresh aggregates without disabling that protection.

**Required correction:** Authoritative checks inside the cash writer, with visibility/approval/active dependencies and relevant locking aligned with specialist writers. Explicitly enumerate supported cash products rather than allowing all types outside an exclusion set. Preserve endpoint replay compatibility and saved historical trades. Effective-date and quotation-convention rules require an explicit product policy, not silent inference.

### P1 — inactive visibility scopes remain usable on the FX path

`repository._visible_node_clause` admits shared or matching tenant-private scopes without requiring the scope itself to be active. The FX contract query uses this predicate. A newly approved FX contract remained eligible and bookable after its visibility scope was set inactive.

Newer `product_booking.visible_clause` uses a stronger predicate. This is implementation drift, not a reason to weaken the newer paths.

**Required correction:** Enforce active scope for current eligibility and new writes, and protect it against changes during booking. Audit callers of the older predicate. Do not indiscriminately hide historical trades or remove the intentional legacy treatment of records without a scope row.

### P2 — older approvals trust references validated only at submission

Approval materialization does not consistently revalidate dependencies. Isolated checks demonstrated:

| Proposal | Change between submission and approval | Current result |
|---|---|---|
| FX forward | Quote currency made inactive | Approved |
| Bond | Selected issuer made inactive | Approved |
| ETP | Reference instrument made private to another tenant | Approved; reference relationship retained |

Relevant functions are `decide_fx_forward_proposal` / `_materialize_fx_forward`, `decide_bond_proposal` / `_materialize_bond` and `decide_etp_proposal` / `_materialize_etp` in `repository.py`.

**Required correction:** Revalidate the required active/visible/approved dependencies at approval, within the materialization transaction and appropriate locks. Return a useful refusal when a dependency has changed. Submission validation remains useful but is not sufficient.

## Coverage and existing protections

| Product | Review outcome |
|---|---|
| Listed cash | Confirmed tenant/approval/active-dependency gaps above; first remediation priority |
| FX forward | Confirmed inactive-scope booking and stale-currency approval gaps |
| Listed option | Stronger local scope predicate and approval reference revalidation exist; underlying helper still warrants caller audit |
| Structured security | Stronger specialist eligibility checks and approval-time dependency revalidation exist |
| Future | Family/contract approval uses locked reference revalidation; physical/crypto creation remains intentionally excluded from booking |
| Bond | Specialist booking convention/terms checks exist; stale selected issuer approval confirmed |
| Swap | Generic approval and specialist booking use stronger reference checks; no new swap-specific defect established in this review |

This is targeted review coverage, not an exhaustive concurrency or security sign-off for each product. Actor authorization, strategy scoping, governed annotations, immutable definitions and specialist booking snapshots remain useful existing protections.

## Policies and UX to clarify, not automatically expand

- **Approved is not necessarily bookable.** Sparse reference creation and creation-only physical/crypto futures are intentional. Show approval and booking readiness separately, with actionable missing-term reasons.
- **Historical execution dates:** FX/option eligibility uses current-date checks in places, while specialist product context can use execution date. Agree the historical-booking policy before normalizing it; do not silently enable booking expired instruments.
- **Cash quote conventions:** Review supported quote factors and multipliers before accepting scaled quotations on the generic cash ticket. This review does not establish correctness for arbitrary cash quote conventions.
- **Reference changes after booking:** Existing saved facts must remain readable. Amendment/versioning and trade correction are separate workstreams.

## Recommended narrow implementation order

1. Add lightweight failing safety regressions for the cash tenant, draft-definition and inactive-parent cases; fix authoritative cash eligibility first.
2. Correct active-scope enforcement for new FX bookings and relevant current-reference callers; cover stale reviewed tickets and concurrency-sensitive reference changes.
3. Revalidate older approval dependencies; add submission-to-approval change regressions for FX, bonds and ETPs.
4. Add broader cross-product negative tests and clear readiness reasons. Run the robust backend/frontend checks after the focused fixes, keeping operating data untouched.

No production fix was made during this review. Remediation needs its own desired-behaviour tests and acceptance evidence.

## Diagnostic evidence

The local ignored diagnostic module is `.superpowers/sdd/2026-10-05-instrument-integrity/test_review.py`. It deliberately characterizes unsafe current behaviour; its passing assertions are **not** safety acceptance tests and must not be promoted unchanged to the standard suite.

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py .superpowers/sdd/2026-10-05-instrument-integrity/test_review.py -q -s --tb=short
```

Latest result: **15 passed in 2.41 seconds**, exit 0. The runner created a uniquely named `fortem_isolated_tests_…` PostgreSQL database, migrated/seeded it and removed it afterward. Each diagnostic used rollback; the HTTP diagnostic used a dependency override bound to the same isolated connection. No operating tenant data, trades, services or migrations were changed.

The earlier diagnostic run had two failures because immutable-definition triggers correctly refused definition updates. Those diagnostics were replaced with fresh draft aggregates, retaining the triggers. No full Python or frontend suite was rerun for this documentation-only review; prior consolidation results remain recorded separately in [its acceptance review](2026-10-05-booking-consolidation.md).
