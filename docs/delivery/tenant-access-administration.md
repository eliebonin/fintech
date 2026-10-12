# Tenant access administration — local alpha

Implemented 9 October 2026 against the approved [design](../superpowers/specs/2026-10-09-tenant-access-administration.md) and [plan](../superpowers/plans/2026-10-09-tenant-access-administration.md). Sequential implementation in the existing feature checkout; unrelated changes were preserved. No commit or push was requested.

## Where to use it

- `/select-context`: select platform administration, or a tenant and active user. Older `/select-tenant` links redirect here.
- `/platform/tenants`: platform-only registry, tenant module toggles and active user lists.
- `/tenant-profile`: distinguishes tenant subscriptions from the selected user's accessible modules, and links to administration.
- `/tenant-profile/access`: tenant-admin Users and Groups. Add users, change membership role/status, assign groups, create/edit/suspend groups, and inspect effective permissions.

Switching performs a full page navigation. The tenant shell identifies the selected user and offers a switch/return action. An expired session can be reset from the selector. Failed switches preserve the existing cookie/context.

## Authority model

The `access_control` action catalogue maps group permissions to modules. Effective access requires an active account, one unambiguous active tenant membership, active group membership, and enabled tenant subscriptions. Group grants combine; a group cannot override a disabled tenant module. Unknown actions fail closed.

Tenant administrators receive enabled-module permissions plus `ACCESS_MANAGE`. Only separately recorded platform administrators can change tenant subscriptions. An impersonated tenant user never inherits the operator's platform authority. Shared canonical reference data remains shared deliberately; tenant business/configuration data is scoped independently.

Default seed personas:

| Persona | Default capabilities |
| --- | --- |
| Tenant admin | Tenant users/groups and enabled-module actions; no platform administration |
| Traders | Instrument search, strategy/trade reads and new trade booking |
| Operations | Reference stewardship, trade reads/cancellation/delivery, market-data and valuation operations where subscribed |
| Read Only | Read actions only, intersected with enabled modules |

These are editable group defaults, not special role-name magic. Creating strategies requires `STRATEGY_WRITE`; configuring trade fields requires `TRADE_CONFIGURE`. Replacement booking needs both `TRADE_WRITE` and `TRADE_CORRECT`; cancellation/delivery need `TRADE_CORRECT`. A trader's booking permission alone does not permit replacement/cancellation. Calendar, market-data and valuation input services use their own action checks rather than the old booking/admin gate.

The operations queue filters inaccessible valuation categories before pagination and total counts. Module toggles preserve business data and existing group definitions, and take effect on subsequent requests.

## Local context and evidence

`ten.local_access_session` stores only a SHA-256 hash of the opaque token, real operator, effective subject, tenant, expiry and revocation. The browser cookie is HttpOnly, SameSite Strict, expires after four hours, and is not returned as frontend JSON. Backend validation rechecks active operator and selected membership. Token-bound requests must match the selected user and tenant. Session credentials are forwarded only to the configured private API origin, never external or relative browser requests.

Context switching and new access-management writes require same-origin requests. Access-management submissions also supply expected tenant and user IDs so stale forms are rejected. The local selector and seed are disabled outside local/test/development; the BFF also disables selection in a production Next runtime.

`ten.access_audit_event` records module, user, group and session changes. Successful tenant mutations retain real operator and effective subject, request path/action and result IDs, without copying prices or credentials. Switching the effective subject does not let the same real operator review their own valuation work. Existing domain review checks remain in place. Audit transport is supplemental, not a replacement for transactional domain evidence.

## Database activation

Additive migration `20261009_82` creates tenant-scoped groups, group members/grants, audit events and local sessions. Same-tenant composite foreign keys constrain group assignments/grants; services additionally validate the user's current tenant membership. Existing effective-date module tables are reused; same-day changes retain before/after audit evidence rather than inserting overlapping same-day grants.

Applied to local `fortem_secm` on PostgreSQL port 54329. Registry backup: `logs/tenant-access-registry-complete-20261009.sql` (8,235 bytes). This is a data-only recovery snapshot with self-referencing entitlement records; restoration requires a controlled dependency/trigger-aware procedure, not blindly replaying it into a populated database.

`scripts/seed_tenant_access.py` adds access fixtures only; it does not call the business-data demo loader. It reuses Fortem Demo and Second tenants and adds Fortem Third. Each has an admin, trader, operations user and reader, and three tenant-local groups. Demo subscriptions were preserved; Second has Security Master/Trading/Market Data; Third has Security Master/Trading. The existing demo administrator retains their name, **MVP Operations Booker**. Their older Second-tenant membership remains, but has no implicit group privileges.

The seed was run twice. Three tenants and nine groups exist; **11 trades and seven strategies stayed unchanged**. Deliberate subsequent group removals/configuration edits are not re-granted by repeat seeding. API/frontend were restarted on ports 8000/3000.

## Verification and limitations

Focused isolated-database tests cover permissions, direct HTTP enforcement, cross-tenant assignment, role/module changes, last-admin protection, revocation, expired/tampered sessions, real/effective actor audit, independent review, idempotent seed, positive non-admin booking, correction permissions, and delegated configuration/calendar/valuation access. Existing booking/reference/correction/calendar/configuration regressions were included. The full Python suite was not requested or run.

`scripts/check_tenant_access.py` exercises the real local BFF and API for all 12 seeded personas, platform return/denial, tenant-admin/non-admin access, read-only booking denial, foreign trade IDs, stale access submissions, reset, and server-rendered user identity. It writes sessions only, not trades/strategies or group grants.

The frontend suite, TypeScript and production build are checked separately; exact final results and log paths are maintained in [the progress record](tenant-access-administration-progress.md).

Final evidence: **124 focused backend tests and 744 frontend tests passed**, TypeScript and production build passed, and all 12 seeded personas passed the real HTTP acceptance script. The initial wider backend run's two outdated role-fixture expectations were corrected and rechecked; that original run is not claimed as green.

**Browser click-through acceptance remains pending.** The provided browser automation kernel failed before initialization with `windows sandbox failed: helper_unknown_error: setup refresh had errors`. HTTP/server rendering and component tests are not presented as browser interaction evidence.

This is a local testing harness, not production login/SSO, email invitation or customer authentication. Existing API actor headers remain a trusted private BFF boundary; do not expose this API/local selector publicly. Production needs verified identity-provider tokens, session lifecycle/CSRF design, stronger audit durability/retention, security review and deployment isolation. Market-data licences and provider evidence are not granted by subscription toggles or impersonation. Small alpha registry queries are not optimized for a large tenant population.

## Platform tenant detail editing

The platform administrator can edit tenant display name and optional operational contact name/email at `/platform/tenants`. UUID and tenant code remain read-only. Contact details are informational: no account, invitation, email delivery or access grant is created. Module subscriptions remain a separate operation.

Suspension and reactivation are separate confirmed actions, not an easily changed dropdown in the profile form. Suspension blocks every tenant workspace, including already-issued local tenant sessions; strategies, trades, subscriptions and memberships remain stored. Reactivation restores only the access permitted by existing active accounts, memberships, groups and module grants. Retired tenants cannot be reactivated or edited through this alpha workflow. No tenant-deletion endpoint was added.

`PUT /v1/platform/tenants/{tenant_id}` accepts a strict `TenantUpdate` command. Names are trimmed, blank optional contacts become null, contact email receives basic format validation, unknown fields are rejected, and `expectedVersion` is mandatory. A locked tenant row serialises edits; a stale version returns 409 rather than overwriting another administrator's work. Status transitions additionally require `confirmStatusChange`. The same transaction updates the row and records `TENANT_PROFILE_CHANGED` with real platform actor and before/after profile values. Platform role checks and the existing BFF same-origin/context gates remain authoritative.

Migration `20261009_83` adds nullable operational contact fields and `profile_version` (default zero). It is additive and forward-only, with bootstrap-safe column creation. Applied to the isolated test DB and the operating `fortem_secm` database; the API was restarted on 8000, and the development UI on 3000 serves the new editor. OpenAPI and generated TypeScript contracts were refreshed. Existing tenant names, statuses and contacts were not altered by feature acceptance checks.

Verification: **41 focused backend tests passed** (12 existing dependency deprecation warnings); **764 frontend tests passed** across 164 files; frontend and contract TypeScript checks, deterministic OpenAPI check and production build passed. Logs: `logs/tenant-edit-backend.log`, `logs/tenant-edit-ui-tests.log`, `logs/tenant-edit-build.log`. Backend tests exercise platform-only writes, immutable identity, contact validation, stale writes, audit evidence, confirmed suspension and session denial/reactivation. UI checks cover separate actions, no write before confirmation, cancellation, retained failed edits and refreshed success. Live BFF checks verified new fields, 422 validation, 409 stale conflict, wrong-origin rejection and tenant-admin denial without changing tenant profiles. Browser visual walkthrough remains pending because the browser automation environment was already unavailable.

### Test fixture safety correction

The first expanded backend run finished with 40 passes and one failure in `test_expired_entitlement_removes_strategy_write_permission`. That older module also hard-coded the operating `fortem_secm` database and reran demo seeding, ignoring `DATABASE_URL`. Its expiry update attempted to end newly seeded grants before their start date and failed the valid-period constraint.

The fixture now requires an environment-selected isolated database and explicitly rejects `fortem_secm`. Its historic expiry test only edits grants that began by the expiry date. The corrected 41-test run used `fortem_tenant_edit_20261009`. The accidental platform account/grant created by the first run was identified by exact UUID and creation time, backed up in `logs/tenant-edit-accidental-fixture.json`, and removed. All pre-existing platform grants were preserved. Operating counts remained three tenants, seven strategies and eleven trades; tenant names/statuses were confirmed unchanged. Demo seeding did run on operating sample data, so these count checks are not presented as proof that every seeded field was unchanged.

## Tenant administration UX refinement

The October 9, 2026 refinement covers `/tenant-profile`, `/tenant-profile/access` (Users and Groups), and `/select-context`. The permission model, management endpoints and database schema are unchanged. No user accounts, module grants or business data were edited as part of this UX work.

The profile now separates tenant subscriptions from the selected user's module access, identifies the user and membership, and places technical identifiers and detailed effective actions behind disclosures. Management links remain conditional on the existing granted actions.

Users and groups are searchable, compact tables with explicit row actions. Creation and editing open one inline editor at a time instead of exposing every user's controls and every permission on initial load. Group actions are organised by module, with disabled-module grants clearly explained. Existing disabled grants and suspended assignments can still be removed, but new ones cannot be added. The group list shows member counts and granted-action counts; the user list shows assigned groups and effective-action counts.

Role selection is a draft until **Save role**. Role and group saves are separate requests, and the editor stays open after either save so other pending changes are not discarded. Suspension/reactivation requires an explicit confirmation. Failed saves retain the editor and display the error; a successful new-group create closes and unmounts its form, clearing the previous values. Only one editor is open at a time; save or close it before changing tabs. Closing an editor explicitly discards unsaved changes.

The context picker prioritises tenant entry, with tenant and user selections followed by a preview. Platform administration is a secondary, visibly separate route. A tenant change clears the selected user. Missing tenants/users and loading/failure states have explanatory messages; previews identify tenant subscriptions without claiming they are the user's effective permissions. Context switching still performs a full navigation and uses the same server-validated session.

Shared styles add clearer primary/secondary actions, consistent spacing, quieter borders, readable status labels, responsive columns and scrollable tables. Tabs have linked tab/panel semantics, roving tab stops, Arrow/Home/End keyboard navigation and a query parameter preserving the selected view across refresh. Forms retain native labels, fieldsets and validation; save feedback uses a live status region. This is not a claim of complete WCAG certification.

Source-backed choices, accessed October 9, 2026:

- [Carbon data-table guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines), updated September 30, 2026, informed compact lists, toolbar search and progressively disclosed row editing. Local search is appropriate for the seeded alpha population; production server pagination remains separate work.
- [GOV.UK button guidance](https://design-system.service.gov.uk/components/button/) informed descriptive action labels and primary/secondary hierarchy rather than presenting every action with equal weight.
- [W3C ARIA tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) informed tab/panel associations and keyboard navigation. Native disclosure elements are used for supplementary details instead of custom modal dialogs.

The layout and the choice to use inline editors are project design decisions informed by these sources, not mandatory industry rules. No component-library dependency was added.

Verification: 163 frontend test files / **759 tests passed**, TypeScript passed, and the production build passed in isolated `.next-access-ux-build`. Logs: `logs/tenant-access-ux-tests.log` and `logs/tenant-access-ux-build.log`. New component and handler checks cover compact browsing, profile access/management visibility, keyboard tab movement, search, user reset on tenant changes, explicit role saves, membership confirmation, suspended-group restrictions, retained drafts and failed/successful group saves. Critical new behaviour was observed failing before implementation.

Live HTTP checks passed for all three seeded tenant administrators (profile, Groups route and access API), and a read-only user (identity rendering, hidden administrator links and API denial). Only local testing sessions were created/revoked. An initial acceptance script stopped because its reader-name lookup used the wrong spelling; the corrected reader check passed. No application defect was inferred from that fixture error.

Visual browser acceptance remains pending: both browser-tool retries failed before initialization, including `windows sandbox failed: helper_unknown_error: setup refresh had errors`. HTTP rendering and handler tests do not replace a desktop/mobile visual walkthrough. The running development app serves the changes on port 3000; no backend restart or migration is required.

## Access architecture sources

The approved design's [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) drove deny-by-default and per-request checks. [OWASP multitenancy guidance](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html) drove validated tenant context, scope checks and uncached responses. [Microsoft control-plane guidance](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/control-planes) drove platform/tenant authority separation. [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693.html) informed separate actor/subject evidence, without implementing a token-exchange service.

## Valuation access corrections — 12 October 2026

The valuation page now derives calculation/input/amendment-request controls from
`VALUATION_RUN`, and amendment decisions/publication from `VALUATION_REVIEW`.
Group-granted members can use their delegated actions without becoming tenant
administrators. Read-only users retain history and evidence access. The API remains
authoritative; the frontend does not calculate financial totals or grant access.

Economic-flow cancellation now requires `TRADE_CORRECT` in both the HTTP action
boundary and the domain writer. It retains valuation/market-data access checks,
but does not require `TRADE_WRITE` or `VALUATION_RUN`. New flow booking remains
separate and still requires booking and valuation-run authority.

Real-operator independence is also enforced transactionally through retained
valuation events, including replacement candidates. See the
[economic P&L correction record](economic-pnl-implementation-2026-10-09.md#review-authority-corrections--12-october-2026)
for lineage, historical compatibility and verification scope. No schema migration,
operating seed, service restart, commit or push was performed for these corrections.
