# Strategy-scoped group permissions

**Status:** Implemented; focused verification and activation record below.  
**Reviewed:** 2026-10-13  
**Capabilities:** F02/F04/F05; third access slice.

## Model and user workflow

The [access UI refinement](access-management-ux.md) records the readable group
scope register, guided editor/review and filtered matrix, with primary UX sources.

Users & groups now includes a **Strategy access** matrix. Pick a strategy to see
each member's allowed strategy actions and source groups. This is administrative
metadata, not access to financial records. **Explain my access** lists the current
strategies covered by each allowed scoped action; empty scope is explicitly blocked.

Group editing saves actions and scope together:

- **ALL:** those actions apply to every current and future strategy in this tenant.
- **SELECTED:** only explicitly listed strategies. Empty selection grants no
  strategy access. Archived strategies remain selectable for history, not new booking.
- Access is additive only among groups granting the *same action*. An ALL reader
  never widens another group's selected booking grant. There are no explicit denies,
  nested groups, individual exceptions or automatic role/ownership overrides.
- Active account/membership/group, subscription and tenant ownership still bound
  every decision. Tenant admins grant administration only and do not bypass scopes.

**Preview access changes** reports strategy gains/losses and tenant-wide action
changes, plus the future-strategy consequence of ALL. Creating an unassigned group
does not immediately grant users access. Confirm saves the captured proposal;
editing the form invalidates its preview. Group `version_no` rejects stale edits.
The UI also supplies an access-state fingerprint, so changed assignments/modules/
strategies after preview require a new preview. Direct authorized API clients can
save explicit configurations without a UI preview; updates still require a revision.
This is not independent approval of access administration.

`STRATEGY_CREATE` is separate from existing-strategy `STRATEGY_WRITE`. Creation
offers explicit initial selected-scope groups. Admins can select active tenant
groups; other creators can select their own active groups only. ALL groups already
cover new strategies. Creation and selected-group associations commit atomically,
with an audit event and group version increment. There is no automatic creator
ownership or operational grant; creation can succeed without subsequent read access.

## Implementation boundaries

[Shared scope evaluator](../../security_master_schema/strategy_access.py) combines
authoritative strategy tenant, current permissions and a correlated same-group
action/scope predicate. [Transport guard](../../apps/reference_api/strategy_boundary.py)
resolves direct strategy/trade/valuation IDs through their actual owning strategy,
including attempts, batches, amendments and economic flows. Guessed/unavailable
scoped targets fail opaquely. Booking authorizers check strategy access before
idempotency replay; corrections/delivery check the original trade's scope.

Collection predicates are applied before trade/valuation pagination and totals.
Booking and valuation selectors use the relevant action, not generic read scope.
Strategy-specific policies, calendar assignments and resolution evidence also
respect strategy scope. Shared instruments, tenant-wide trade configuration,
provider licensing and explicitly shared market-data snapshots remain separate.
Group scope affects the controlled scoped actions; it does not turn every module
configuration action into a strategy-specific permission.

The API transaction binds its already-verified actor/action in `Connection.info`
and clears them before returning a pooled connection. This enables explicit query
filters without an implicit SQL rewrite or database RLS. Trusted internal financial
calculations retain complete inputs; request middleware and service-level write
authorizers protect external paths. Future endpoints must use the same predicates.
Current local header/BFF trust is not production authentication.

New resolution snapshots retain strategy context and distinguish SHARED, STRATEGY
and LEGACY_UNKNOWN. Migration can recover known context from a strategy-specific
immutable policy version. Other old snapshots are not fabricated as shared:
restricted users cannot read unknown legacy context; an appropriate explicit ALL
strategy-read grant can inspect it. Dataset display rights remain independently checked.

Revocations affect subsequent requests/checks and retries. This does not undo
completed trades or promise cancellation of an already-authorized in-flight calculation.

## Migration and compatibility

Forward-only `20261013_85` adds group scope/version, composite same-tenant strategy
associations, retained snapshot context and constraints. Existing groups become
explicit ALL to preserve their former tenant-wide meaning. Existing STRATEGY_WRITE
holders receive explicit STRATEGY_CREATE, preserving their ability to create.
New group API requests require an explicit scope. Group fixture/bootstrap paths
choose ALL explicitly; repeated seeds do not restore revoked permissions/scopes.
Revision 84's frozen operational catalogue remains unchanged; creation is a separate
current-fixture addition, and revision 85 supplies the existing-data transition.

No business-data reseed is needed. Root [AGENTS](../../AGENTS.md),
[KNOWLEDGE](../../KNOWLEDGE.md) and [FIX](../../FIX.md) were reconciled with the
md-document skill for this scope, preserving unrelated structured-product findings.

## Verification

110 focused backend tests passed, including scopes, direct/list/count enforcement,
preview rollback/staleness, atomic creation, existing booking/correction workflows,
valuation inputs and administration. The initial broader run's three fixture/denial
expectations were corrected and the bundle re-run green. Tests used the owned
disposable PostgreSQL runner, never the operating DB. No full Python suite was run.
Scope editor/matrix/initial-access rendering and preview-confirmation/invalidation
tests passed with existing access regressions; TypeScript passed. Generated contracts
are refreshed. Production build and local activation results are appended when checked.
Automated component/HTTP evidence is not an interactive browser sign-off.

Final verification: **57 additional focused access/backend tests passed** after
the complete before/after group audit update; **42 frontend tests across 11 files**,
TypeScript, isolated production build, OpenAPI freshness, documentation-link and
whitespace checks passed. Matrix loading feedback was reproduced and fixed with
a focused rendering test. The isolated build used its own cache; its generated
Next config changes were restored to the operating development settings.

Applied **migration 85** to local `platform_secm`, restarted the verified API on port
8000; frontend remains on 3000. Before/after checks covered **13 persona contexts**:
existing permissions were preserved, adding STRATEGY_CREATE only where prior
STRATEGY_WRITE already permitted creation. All 12 existing groups are explicitly
ALL, with 12 transition audit events. **11 trades and seven strategies are unchanged.**
Live BFF matrix returned 28 rows for the demo tenant, unchanged preview returned
zero changes plus a fingerprint, and access/strategies/booking pages returned HTTP
200. Only a temporary local context session and preview audit were used; no operating
permission, trade or strategy test edits were saved. The session was revoked.
Interactive browser click-through remains separate; no merge, commit or push requested.

## Trade-offs and remaining work

- Administrators can still self-assign permitted access; independent access-change
  approval/certification and production identity remain deferred.
- The alpha matrix and preview materialize the tenant's users × strategies and
  scan group relationships; large tenants need paging/targeted impact calculation.
- No desk/fund hierarchy, time-limited grants or individual overrides.
- Group scope is one scope for that group's scoped actions. Different read/write
  scopes use separate groups, preventing an action/scope cross-product.
- Unknown legacy snapshot context is restricted, not guessed. Recalculation creates
  explicit new evidence when a restricted user needs that workflow.

## Primary-source guidance

[OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
informed deny-by-default and per-request object checks.
[OWASP output handling](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Decisions_And_Output_Handling_Cheat_Sheet.html)
informed collection/count/evidence filtering and bounded reuse.
[OWASP service-level patterns](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Patterns_Cheat_Sheet.html)
supports keeping a shared evaluator inside this application with enforcement near
resources rather than requiring an external policy service.
[Microsoft RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)
illustrates bound principal/action/scope assignments and additive grants. Our ALL/
SELECTED defaults and initial-access/preview UX are application design decisions,
not a claim of a universal financial-industry requirement or certification.
