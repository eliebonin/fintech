# Tenant administration versus operational authority

Subsequent [strategy scopes](strategy-access-scopes.md) add per-group ALL/SELECTED
coverage, preview/matrix and separate STRATEGY_CREATE. The revision-84 evidence
below describes its original activation; revision 85 preserves that access explicitly.

**Status:** Implemented; activation/verification record below.  
**Reviewed:** 2026-10-13  
**Capability:** F02/F04; second slice after effective-access transparency.

## Approved behavior

TENANT_ADMIN grants ACCESS_MANAGE only: users, groups, role/status changes and
effective-access inspection. Every operational action, including trade reads,
booking/correction, instrument proposal/approval and valuation run/review, requires
an explicit active group grant for admins as well as members. Tenant subscriptions
remain the upper bound. ACCESS_MANAGE cannot be delegated by a group. Existing
independent valuation-review and last-active-admin safeguards are unchanged.

New admins are management-only. Creating/promoting an admin never assigns an
operational group automatically. Changing/demoting a role does not remove existing
group assignments: administration and operations are independent. Suspending a
membership/account/group and disabling a module still remove effective authority.
Users & groups and Explain access now explain this distinction and name actual
group grant sources; only ACCESS_MANAGE cites the administrator role.

An admin can assign themselves a permitted operational group. This is deliberate
for the alpha: it separates default authority, not protection against a malicious
access administrator. Self-assignment stays audited. Independently approved access
changes, periodic certification and production identity remain later work.

## Compatibility transition

Forward-only data migration `20261013_84` assigns each current existing tenant-admin
membership its own **Existing administrator operational access** group. Its grants
snapshot the frozen 16 operational action codes applicable to currently enabled
modules. No group contains ACCESS_MANAGE or platform authority. Suspended current
admin memberships retain explicit assignments for eventual reactivation, but their
status still blocks access. Expired/future memberships are not transitioned.

Per-user groups avoid one admin's compatibility edits changing another admin's
access. The group is ordinary, editable/suspendable/removable in Users & groups;
prefer curated job-responsibility groups as tenants refine duties. Migration/fixture
events retain tenant, subject, recording actor, group, action/module snapshot,
business date, reason and transition revision. For migration rows, the required
actor identity is the affected admin and revision/reason identify the system
transition; this is not presented as a user-initiated access request.

`ADMIN_OPERATIONAL_ACCESS_BOOTSTRAPPED` is the durable one-time marker. Re-running
migration or local seed does not recreate removed assignments, re-enable groups or
restore edited grants. Later subscriptions/actions do not expand the snapshot;
admins must explicitly grant them. Downgrade refuses to restore implicit authority.
This is access data only, not a business-data reseed.

Empty-database demo loading grants only the loader-owned demo admin explicitly,
because migration executes before fixture users exist. Local three-tenant access
seeding gives its known fixture admins explicit operations once. Neither path is
called by application user creation/login/promotion. Do not run the general demo
loader on operating data to activate this feature.

## Verification and activation

Test-first failures demonstrated admin-without-groups could read trades and the
old explanation claimed implicit operational authority. Pure and disposable-DB
checks cover management-only admins, explicit read-only grants, immediate removal,
subscription bounds, retry-safe compatibility assignment, actual migration reruns,
role downgrade, future module activation and retained last-admin/context boundaries.
The first broader run exposed an HTTP-test fixture leaving an active admin behind;
cleanup was added before the final successful runs. No full Python suite was run.

Frontend guidance/component/editor tests and TypeScript are separate from browser
click-through acceptance. No new route or contract shape was introduced in this slice.
Self-reviewed sequentially; no independent reviewer or production sign-off claimed.

Activation targets the existing local `platform_secm`, verified at revision 83 before
transition, with three current admin memberships, nine groups, 11 trades and seven
strategies. Apply only migration 84, then restart the local API so the resolver
changes become active. No operating synthetic trades/users are created for verification.

Final focused run: **72 backend tests passed** across authority separation,
permissions/explanations, access management/API/sessions, effective-access API,
source-evidence scope and platform tenant updates. A prior successful expanded
run included tenant-workspace tests (78 tests before the final migration test).
**34 frontend tests passed** across seven access UI/session files; TypeScript,
OpenAPI freshness and diff whitespace checks passed. Existing dependency
deprecation warnings were reported, not treated as authorization failures.

Applied `20261013_84` to local `platform_secm` and restarted the verified API process
on port 8000. UI remains available on port 3000 (HTTP 200). Live before/after
workspace reads confirm identical permission sets for all three existing admins;
trade-booking explanations now cite the explicit compatibility group, not the
admin role. Counts: groups 9 → 12, memberships 9 → 12, group grants 51 → 87,
three transition audit events. **Trades remain 11; strategies remain seven.**
No synthetic operating users/trades were created, and no commit/push was requested.
Interactive browser acceptance and independent production security review remain
unclaimed. Permission and compatibility regression tests used disposable DBs only.
