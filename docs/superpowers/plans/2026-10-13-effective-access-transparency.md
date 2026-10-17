# Effective-access transparency implementation plan

Historical first-slice record: subsequent [admin authority separation](../../delivery/admin-operational-authority-separation.md)
replaced implicit admin operations with explicit groups. The unchanged-admin
semantics recorded below apply to this first slice only.

> Execute sequentially with test-first checks. No subagents or operating database mutations.

## Design and scope

First slice of the platform/access recommendations: explain current access without
changing its meaning. Active members inspect themselves; ACCESS_MANAGE holders
inspect current members of the same tenant, including suspended members. Subscription,
active group grants, account/membership restrictions and delivery status are distinct.
The existing permission resolver remains authoritative. Tenant admins retain their
current implicit permissions; platform administration grants no tenant permissions.
Structured-product source evidence must belong to the submitting tenant or explicit
shared scope, and match the selected source system, before insertion or replay.

## Tasks

- [x] Backend: add `access_explanations.py` with pure `explain_actions` and scoped
  `effective_access_view`; GET `/v1/tenant-workspace/effective-access?userId=...`.
  Exact read-only middleware exemption still requires active tenant membership.
  Test empty grants, union, suspended groups/accounts/memberships, disabled modules,
  admin/self inspection, foreign users, and unknown paths/mutations denied.
- [x] Integrity: validate structured-product source ownership before replay. Test
  owned/shared evidence accepted; absent, foreign and mismatched evidence rejected.
- [x] Frontend: personal effective-access page, server-derived BFF context and links
  from tenant profile/user register. Show reasons and honest delivery limitations.
  Verify rendering, routing, query forwarding and type safety.
- [x] Documentation/contracts: regenerate OpenAPI, reconcile capability records,
  record focused verification and remaining recommendations.

## Review focus and constraints

- A zero-grant member can inspect self, never another member.
- Foreign/unknown member IDs disclose no user details.
- Suspended targets can be explained but gain no access.
- Delivery metadata must never gate authorization or promise future modules.
- Retry must not bypass source ownership checks.
- No migrations, production authentication changes, seed/restart or full suite.
- Preserve pre-existing termsheet documentation changes.

## Guidance

- [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): deny by default and check permissions per request/resource.
- [OWASP regression testing](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Regression_Testing_Cheat_Sheet.html): actor/resource/action matrix and horizontal isolation tests.
- [OWASP multi-tenant security](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html): server-verified context and tenant-scoped resources.
- [Microsoft SaaS identity/access](https://learn.microsoft.com/en-us/azure/well-architected/saas/identity-access): delegated administration and explicit authorization boundaries.

## Execution record

Ruling: use the existing feature-branch checkout and preserve unrelated changes,
as previously agreed; use focused disposable-DB tests rather than a full suite.
Ruling: author self-review rather than delegated review, respecting sequential execution.

Task evidence: 83 focused backend tests passed through the owned disposable DB
runner (source-scope, effective-access API, access management/API/control/explanations,
structured-product draft/API tests). 36 frontend tests passed across eight files;
TypeScript, isolated production build, OpenAPI freshness and diff whitespace checks
passed. Build used `.next-access-transparency-20261013` rather than the operating
cache; generated config changes were restored afterward. Test-first failures were observed for missing view/route,
foreign evidence and absent user navigation. No full suite run.

Final review: source reads use shared rather than exclusive row locks to pin scope
without serializing all provider submissions; final source regressions re-run after
this adjustment. Delivery labels reconciled against F41–F45: fund operations is
foundation, structured products partial. No auth semantics changed. No commit/push.
