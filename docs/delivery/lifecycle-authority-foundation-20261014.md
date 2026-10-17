# Lifecycle authority foundation — 14 October 2026

**Subsequent delivery:** [Plain-bond maturity redemption](plain-bond-redemption-20261014.md)
now consumes these guards and supplies retained mode settings, preparation,
approval, posting and cancellation. The no-consumer statements below describe
this earlier foundation checkpoint, not the current plain-bond capability.

## Delivered scope

Point 7 of the agreed lifecycle discussion: explicit tenant/strategy-scoped
permissions and a reusable server-side authorization foundation. This is not an
event dashboard, maturity detector, closing-price engine or booking workflow.
No financial entries, workflow settings or live group memberships were changed.

| Action | Meaning / additional condition |
|---|---|
| `LIFECYCLE_READ` | View lifecycle records within strategy scope |
| `LIFECYCLE_PREPARE` | Prepare closing entries within strategy scope |
| `LIFECYCLE_BOOK` | Ops-triggered Book now / manual booking; also `TRADE_WRITE` on the same strategy |
| `LIFECYCLE_APPROVE` | Approve review-required entries; also `TRADE_WRITE` and independent selected-user/real-operator ancestry |
| `LIFECYCLE_CONFIGURE` | Explicit strategy-scoped processing-mode configuration authority; no admin-role shortcut |
| Existing `TRADE_CORRECT` | Correct lifecycle postings through retained trade-correction semantics |

All new actions require the tenant's TRADING entitlement. Group preview/save,
audit, effective-access explanations and strategy matrix use the existing shared
catalogue and scope predicates. Existing administrators/Operations groups receive
no automatic new grants; frozen seed/bootstrap catalogues are unchanged. Access
administrators may explicitly assign the new actions in Tenant profile → People
and access → Groups. UI descriptions disclose workflow availability honestly.

`lifecycle_authority.required_permissions` distinguishes DIRECT, REVIEW and MANUAL.
DIRECT means an Ops click, never unattended scheduled posting. BOOK is rejected in
REVIEW mode; APPROVE is rejected outside REVIEW. Identity comparison normalizes UUID
representations and rejects missing/malformed reviewer/preparer evidence. The
combined guard checks every required action on the same strategy, before returning
actor/operator/action/scope evidence for a future posting transaction.

No lifecycle endpoint currently consumes this guard. Future handlers must load
mode and preparation ancestry from retained backend records, not browser inputs;
propagate the real operator from trusted request context; revalidate current inputs
and permissions before retries; retain the proof with the booked event. A proof
alone is not an approval, persisted audit event or successful posting.

## Agreed product rules for subsequent implementation

1. A closure effective on T contributes to T's P&L and removes closed quantity
   from T EoD holdings; payment date does not shift recognition.
2. Open exposure past maturity is an Ops exception. Its notification dashboard is
   deferred; unsupported final economics still block affected valuation.
3. Ops decides when to click Book now. Supported closing price, current exposure,
   permissions and duplicate checks remain mandatory. Review-required proposals
   become stale if material inputs change.
4. Backdated trades/corrections preserve original postings and published evidence;
   use linked corrections and recalculate affected dates.
5. Closing proceeds enter the execution-value bridge. Coupon/accrual/fees remain
   separate. Derivative price units and quote factors must be explicit.
6. Different OTC contracts are different canonical instruments, regardless of
   economic likeness. Close each strategy's remaining compatible position in that
   instrument, not an aggregate risk-equivalent position. Full termination closes
   to zero; partial redemption closes only the applicable portion.
7. Permissions above are explicit group grants. No mandatory new roles or service
   actor. Direct booking does not permit bypass of a configured review workflow.

## Remaining work / boundaries

- Persisted, versioned processing-mode settings with audited changes; labels/grants
  do not constitute a configurable workflow.
- Prepared-event records, independent approve/book endpoints, idempotent posting
  and a structured maturity/redemption trade type. Start with plain bonds.
- Contractual closing economics, quantity revalidation, short/partial redemption,
  price evidence, final interest and linked corrections.
- Lifecycle detector/notification dashboard, FX-forward maturity and subsequent
  products. Exposure closure remains separate from payment and uploaded cash.

## Verification

Focused tests written before implementation: module bounds/no implicit admin grants,
review-mode bypass denial, selected/real-operator independence, malformed ancestry,
same-strategy intersection of lifecycle and trade-write, cross-tenant denial and
broad-read versus restricted-config scope. UI labels clarify pending workflows.
Final verification: 30 focused backend tests passed in an owned disposable
PostgreSQL database (one existing Starlette/httpx deprecation warning); 12 frontend
tests passed across four files. TypeScript, OpenAPI consistency and diff whitespace
checks passed. Existing unrelated dirty-checkout changes were preserved.

The local API was restarted to activate the catalogue; no migration, seed run or
live permission expansion. Logs: `logs/api-lifecycle-authority-20261014.*.log`.
No full suite or maturity posting/browser financial acceptance was performed.
