# Effective-access transparency and source-evidence isolation

**Status:** Implemented; focused verification, no browser/live activation claim.  
**Reviewed:** 2026-10-13  
**Scope:** First slice of platform/tenant/user/module-access recommendations.

## Using the feature

Tenant profile → **Explain my access** opens `/tenant-profile/effective-access`.
Active members can inspect themselves even without module/group actions. Tenant
admins can use **Explain access** beside a user in Users & groups, including a
suspended member. The page shows membership/account status, groups (including
suspended groups whose grants are ignored), subscriptions, action decisions,
grant sources and blocking reasons. Multi-module actions require any one listed module.

Delivery is separate: bounded alpha, foundation, partial, planned or unassessed.
Enabling a future module does not implement its workflow. `MODULE_DELIVERY` in
`security_master_schema/access_explanations.py` must track capability records as
product scope changes. Modules with no standalone actions say so explicitly.

## Authority and boundaries

GET `/v1/tenant-workspace/effective-access`, optionally `userId`, requires an active
account/tenant/membership. The narrowly exempted read-only middleware path does
not bypass checks for arbitrary workspace paths or mutations. Inspecting another
user requires ACCESS_MANAGE and current membership in this tenant; foreign and
unknown targets receive opaque denial. Suspended targets gain no permissions.
The private BFF supplies actor/tenant context, forwards only the inspection target
and disables caching. The page is keyed by verified tenant, selected user and
inspection target to avoid retaining another member's result on navigation.

The actual `effective_permissions` resolver produces decisions; this is not a
second authorization engine. The subsequent [authority separation](admin-operational-authority-separation.md)
changes TENANT_ADMIN to ACCESS_MANAGE only; all users need active group grants for
operations, bounded by subscriptions. Existing admin operations have explicit
compatibility groups. The subsequent [strategy-scope slice](strategy-access-scopes.md)
binds each operational action to its granting group's ALL/SELECTED strategies. Dataset/provider
licences are separate. This is current-state inspection, not historical replay.

## Structured-product source evidence

Submission validates source evidence before insertion **and idempotent replay**.
A payload requires a source system. The active source must be shared (`tenant_id
IS NULL`) or owned by this tenant; the payload must match that source and tenant
or explicit shared scope. UUID existence/FKs are insufficient. Missing, foreign
and wrong-system evidence produce opaque errors without payload contents. Shared
transactional row locks pin scope/status while allowing concurrent provider submissions.

Only trusted ingestion should assign shared/null ownership. A future tenant-upload
endpoint must default to tenant ownership and enforce retrieval checks. No upload
or document-read endpoint was added; other legacy source consumers are not claimed
to have been exhaustively audited.

## Verification and cuts

Test-first checks reproduced foreign/mismatched evidence acceptance and retry
bypass before the fix. Focused tests cover owned/shared acceptance and rejection
without proposal insertion; self/admin inspection, foreign/unknown targets,
suspended membership, group/module decisions and zero-grant HTTP module boundaries.
83 focused backend tests passed using the owned disposable PostgreSQL runner;
36 frontend tests, TypeScript and isolated production build passed. OpenAPI was regenerated and checked.
Final verification updates appear in the [plan](../superpowers/plans/2026-10-13-effective-access-transparency.md).

No full Python suite, migration, operating seed/restart, merge or push. Component,
BFF and HTTP tests are not interactive browser acceptance. Real authentication and
trusted ingestion remain separate boundaries; local headers are not production identity.

## Remaining ordered work

1. Access/operational authority separation is implemented in the subsequent slice;
   independent approval of access changes remains deferred.
2. Strategy scopes and administration previews/matrix are implemented in the subsequent slice.
3. Production identity/onboarding rather than local simulation.
4. Governed time-limited support access rather than production impersonation.

## Guidance

[OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
supports deny-by-default and per-request resource checks.
[OWASP authorization regression testing](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Regression_Testing_Cheat_Sheet.html)
supports actor/resource/action matrices, reflected in the HTTP boundary tests.
[OWASP multi-tenant security](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html)
supports server-verified context and tenant-scoped resources, applied to evidence IDs.
[Microsoft SaaS identity/access](https://learn.microsoft.com/en-us/azure/well-architected/saas/identity-access)
supports delegated administration and application authorization. These sources
informed the boundaries, not a compliance certification.
