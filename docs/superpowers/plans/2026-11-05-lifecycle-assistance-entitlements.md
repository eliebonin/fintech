# Lifecycle assistance entitlements implementation plan

**Execution:** Implemented sequentially on 5 November 2026. [Delivery, exact verification and limits](../../delivery/lifecycle-assistance-entitlements-20261105.md); the checklist below retains the approved acceptance intent, not a claim that every listed permutation has a separate test. KEEP became an explicit preview-only response; full-population configuration authority means actual target coverage, including unions of SELECTED groups. Strategy UI integration uses the existing overview route. Local policy-copy cutover is preview-only unless explicitly applied.

> **For agentic workers:** Use superpowers:executing-plans sequentially, task-by-task. Do not delegate. This is a plan, not delivered functionality. Preserve unrelated working changes; do not commit/push, grant commercial access or apply operating cutover without the task's actual authorization.

**Goal:** Let a platform administrator grant a tenant a maximum lifecycle-assistance tier and let authorised tenant users select a supported level per strategy/event, with enforced limits and retained history.

**Architecture:** Reuse existing tenant module entitlement, lifecycle action/scope controls, bond/FX native handlers and reviewed UI patterns. Add two small typed append-only relations for the tenant ceiling and explicit strategy/event selections. One shared domain decision gates all assisted effects; existing execution/review policy remains independently authoritative.

**Tech stack:** Existing PostgreSQL 18, SQLAlchemy/Alembic, FastAPI, Next.js BFF/React, generated contracts, Vitest and Playwright.

**Spec:** [Product rules, storage, runtime matrix and rollout](../specs/2026-11-05-lifecycle-assistance-entitlements.md).

## Global constraints

- Tiers are exactly 0 Fully manual, 1 Notifications, 2 Assisted preparation, 3 One-click booking; higher ceilings include lower choices, never automatically select them.
- Scope initially BOND_MATURITY and FX_FORWARD_MATURITY. Do not advertise new handlers or notification discovery as implemented.
- Keep subscription, strategy assistance, native review policy, user permissions and source readiness separate. No user grants or review bypass from purchase.
- Keep financial quantities/prices, allocation preservation, original evidence and native correction rules unchanged. No cash/payment/valuation generation.
- Existing ordinary manual booking, authorised retained history, coupon schedules/confirmations and interest maintenance retain current access rules.
- Billing integration and general notification dashboard are separate subsequent work. No default paid grants or silent workflow fallback.
- Planning-only changes do not authorize executing these tasks. At implementation time inspect Git state and next migration revision; retain the user-requested sequential execution method.

## Review focus

1. A Tier 3 tenant selects level 1/2 for one strategy: forged direct posting must fail even though the subscription ceiling is high (Tasks 2/3).
2. A downgrade races with booking/approval or a proposal already exists: serialize commit, retain old evidence, block later effects without mode fallback (Tasks 1/3).
3. Another group/tenant grants a matching action but not the same strategy: no combined-scope bypass or revealing counts (Tasks 2/4).
4. Subscription upgrade or a new higher selection tries to turn an independent-review proposal into direct booking: retain source policy/proof and refuse (Task 3).
5. Grant is suspended/expired, the response is lost after save, or a successful booking is retried: explain current state, recover by read/receipt, never duplicate effects (Tasks 1/3/4).

## Task 1 — Typed subscription ceiling and reviewed platform command

**Files:** create `security_master_schema/lifecycle_entitlement_tables.py`, `lifecycle/assistance_contracts.py`, `lifecycle/entitlements.py`, and the next additive Alembic revision; modify `security_master_schema/models.py`, `security_master_schema/access_management.py`; test `tests/test_lifecycle_entitlements.py`.

**Interfaces:** `lifecycle_subscription_view(c, tenant_id) -> SubscriptionView`; `preview_subscription_change(c, platform_actor, tenant_id, maximum_tier, expected_revision) -> ChangePreview`; `change_subscription(c, platform_actor, real_operator, tenant_id, request) -> SubscriptionView`. Request requires `maximumTier`, `expectedRevision`, `expectedImpactHash`, nonblank `reason`, and explicit confirmation. DTOs retain current revision/source and affected-policy/proposal counts without financial rows.

- [ ] Write failing pure/DB tests: range0–3, absent/suspended/expired module returns ceiling0, ambiguous grants refuse, platform-only mutation, stale revision/impact conflict, same-day changes retain all tier revisions, generic boolean LIFECYCLE_MANAGEMENT toggle refuses, unrelated module changes unchanged.
- [ ] Run `scripts/run_isolated_python_tests.py tests/test_lifecycle_entitlements.py -q --tb=short` and inspect the expected failures.
- [ ] Implement the two composite-owned/revisioned relations from the spec, current module registration, immutable history, shared/exclusive lifecycle lock helpers, and atomic module/tier/access-audit transaction. Do not widen existing ACTION_MODULES OR semantics.
- [ ] Verify focused tests and schema/upgrade checks on a disposable DB; test that tier changes do not alter financial/access-grant rows and tenant suspension remains effective.

## Task 2 — Scoped strategy/event configuration and decision model

**Files:** create `lifecycle/assistance.py`, `apps/reference_api/lifecycle_assistance_routes.py`; modify `apps/reference_api/main.py`, `access_boundary.py`, `workload_admission.py`; test `tests/test_lifecycle_assistance.py`, `tests/test_lifecycle_assistance_api.py`.

**Interfaces:** `assistance_view(c,tenant,actor,strategy,event_type) -> AssistanceView`; `configure_assistance(c,tenant,actor,real_operator,request) -> AssistanceView`; `require_assistance(c,tenant,actor,strategy,event_type,operation) -> AssistanceProof`. View includes `maximumTier`, `selectedTier`, `availableTiers`, `subscriptionRevision`, `assistanceRevision`, `processingPolicyRevision`, `status`, `reasons`, `handlerSupported`, `notificationDiscoveryAvailable=false` until dashboard delivery. Status does not silently clamp the selection. Operations distinguish discovery, assisted preview/prepare, prepared confirmation, direct posting and history/correction.

**Routes:** GET/POST `/v1/lifecycle/assistance` with explicit strategy/event scope, expected revisions and reason; platform GET and PUT `/v1/platform/tenants/{tenant_id}/lifecycle-subscription`, and POST `/v1/platform/tenants/{tenant_id}/lifecycle-subscription/preview`, live in this thin adapter. Add an exact BFF POST preview allowance; preserve same-origin and platform-context checks. Define typed request/response models here or in a focused contracts module; do not move orchestration into routes.

- [ ] Write decision-matrix tests for ceilings0–3 × selected0–3 × operations, supported event validation, unconfigured0, above-ceiling BLOCKED_BY_SUBSCRIPTION, reviewed downgrade choices, current STRATEGY scope and configure/read separation.
- [ ] Reproduce missing behavior with the focused disposable runner; implement server resolution and exact API/middleware/admission registration, including routes outside tenant impersonation for platform admin commands.
- [ ] Test hidden strategy filtering before pagination/count, cross-tenant target refusal, own-tenant admin without scoped LIFECYCLE_CONFIGURE denial and no lookup fallback to old REVIEW as a paid entitlement.
- [ ] Run the two new suites plus `tests/test_lifecycle_authority.py`; export/generate/check contracts. Preserve unrelated previously generated additions.

### Task 2b — Explicit tenant downgrade preparation

**Files:** create `lifecycle/assistance_transitions.py`, `tests/test_lifecycle_assistance_transitions.py`; extend Task2 contracts/router and `src/features/lifecycle-assistance/` (Task4).

**Interfaces:** `preview_assistance_transition(c,tenant,actor,request) -> AssistanceTransitionPreview`; `apply_assistance_transition(c,tenant,actor,real_operator,request) -> AssistanceTransitionResult`. Request pins `proposedMaximumTier` and current subscription revision; `scope` is `ABOVE_NEW_CEILING`, `ALL_CONFIGURED` or `SELECTED`; `replacement` is `HIGHEST_AVAILABLE` or `EXPLICIT`; explicit replacement requires `targetTier`. SELECTED has explicit strategy/event IDs. Apply adds the exact preview `inputHash`, reason and confirmation; ALL_CONFIGURED requires additional `confirmReplaceAllowed=true`. Keeping all choices unchanged is a valid skip of this transition, not an empty fake update. Routes POST `/v1/lifecycle/assistance/transitions/preview` and `/apply` use tenant context and exact BFF allowlists.

- [ ] Write failing cases for3→2 with existing3,2,1,0: recommended2,2,1,0; affected-only explicit1 produces1,2,1,0; all-to0 produces0,0,0,0; all-to2 produces2,2,2,2 ONLY after the broader confirmation. With new maximum0, changed positive selections become0. No-op rows do not gain false revisions.
- [ ] Verify that existing valid rows remain untouched for affected-only choices, unknown targets/tiers reject, target tiers above either the proposed or current ceiling reject, current pages do not truncate ALL_CONFIGURED, unconfigured strategies remain0, future strategies receive no inherited setting, and a scoped user cannot apply whole-tenant changes or learn hidden strategy counts.
- [ ] Apply an exact reviewed population atomically under the shared lifecycle lock and ordered strategy locks, with explicit same-strategy configure checks. New/changed targets, changed subscription, changed actor authority or a single stale row invalidate the whole transition; no partial success. Retain per-policy revisions and a change-summary audit. No financial effects or permission changes.
- [ ] Preserve the platform/tenant authority boundary. Tenant transition and platform subscription change are two named transactions. Test tenant-only users cannot lower the commercial ceiling, platform-only users cannot rewrite tenant strategy settings, and a failed/later commercial change does not falsely roll back a previously confirmed tenant transition. Intervening higher selections invalidate the platform preview.
- [ ] Run `scripts/run_isolated_python_tests.py tests/test_lifecycle_assistance_transitions.py -q --tb=short`. The eventual platform downgrade may proceed with unchanged above-ceiling selections only after explicit blocked-workflow acknowledgement; expiry/revocation still blocks immediately without waiting for transition approval.

## Task 3 — Enforce assistance in existing bond and FX workflows

**Files:** modify `security_master_schema/lifecycle_authority.py`, `lifecycle/bond_service.py`, `lifecycle/fx_service.py`, `apps/reference_api/bond_redemption_routes.py`; test `tests/test_lifecycle_subscription_enforcement.py`, `tests/test_lifecycle_subscription_races.py`; reuse existing bond/FX service and allocation suites.

**Interfaces:** consumers use Task2 `require_assistance` and retain its revisions/proof with NEW proposal/posting evidence only. Existing native proposal/posting payloads remain unchanged. Non-REVIEW (MANUAL or DIRECT) prepared confirmation uses the retained proposal plus existing LIFECYCLE_BOOK/TRADE_WRITE; REVIEW still requires LIFECYCLE_APPROVE, both identities independently checked. DIRECT posting without a proposal needs selectedTier3 AND ceiling3 AND native DIRECT policy.

- [ ] Write failing entry-point tests for options/preview, prepare, book, approve, non-REVIEW prepared-confirmation and cancellation on both registered prefixes. Tier1 may inspect history, but cannot call assisted preview/preparation; Tier2 cannot call direct posting. No UI-only enforcement.
- [ ] Make Tier2 non-REVIEW (MANUAL or DIRECT) confirmation consume a current retained proposal, add a specific confirmation operation/path if necessary, and preserve current review/correction actions. Do not accept a browser `reviewed=true` substitute for server evidence.
- [ ] Take the lifecycle shared lock before native instrument/configuration/strategy locks; platform changes take its exclusive counterpart through outer commit. Bind current revisions in fingerprints. Test actual concurrent commit order and no deadlock, not only mocked locks.
- [ ] Verify upgrade cannot reuse REVIEW proof as DIRECT, stale proposals require a new review, selectedTier2 in a ceiling3 tenant still denies direct calls, current source/maturity/allocation failures remain blockers, and successful unchanged receipt replay has no duplicate effects after downgrade. New effects remain blocked; corrections retain native authority.
- [ ] Run focused enforcement/race suites plus existing `test_bond_redemption_service.py`, `test_fx_maturity_service.py`, `test_lifecycle_allocation_store.py`, `test_trade_profile_lifecycle.py`, `test_trade_profile_fx_lifecycle.py`. These existing service suites are present; add the new suites before invoking them.

## Task 4 — Platform selector, strategy settings and clear operational states

**Files:** modify `apps/ops-console/src/components/platform-tenants.tsx`, its typed client/contracts, `apps/ops-console/src/components/tenant-profile-overview.tsx`, `apps/ops-console/src/components/strategy-workspace.tsx`, `apps/ops-console/src/components/bond-redemption-console.tsx`, `apps/ops-console/src/app/trades/lifecycle/page.tsx`, existing platform/lifecycle BFF allowlists and `src/lib/page-guides.ts`; create `src/features/lifecycle-assistance/` for focused subscription/strategy controls and decision presentation. Tests: feature unit tests, affected BFF tests, `browser-tests/lifecycle-assistance.spec.ts`.

**Interfaces:** consume generated Task2 contracts through verified transport. Strategy card uses `assistance_view`; platform selector uses reviewed preview/change and expected revisions. Do not compute authoritative eligibility in the browser.

- [ ] Add tenant Downgrade preparation: show the proposed new ceiling, four choices from the spec, strategy/event before→after table, unchanged/changed/blocked counts, and preparation reassessment impact. Default the preview to Preserve valid; reduce higher to new maximum, but require explicit review/apply. All-to0 and all-to-any-tier explain that currently valid choices are replaced. Clearly separate saved strategy changes from the later platform subscription change.
- [ ] Show a labelled 0–3 subscription selector with comparison, current grant/source/revision, reviewed reason and downgrade impact. Remove/replace only the new lifecycle boolean checkbox with the dedicated selector; retain other modules. Read refresh failure after confirmed save must preserve saved confirmation.
- [ ] Add Strategy Overview → Lifecycle assistance, clearly separate from Trade configuration. Show one row per supported event, selected level, ceiling, review requirement and availability; edit/review one row at a time. Unavailable higher choices have visible reasons. No implicit tenant default or bulk policy update; the separate downgrade preparation flow is explicit and reviewed.
- [ ] Update current bond/FX console to show assistance status and separate subscription, permission, unsupported-handler and data-readiness reasons. Keep historical receipts/correction accessible. Explicitly label notification discovery as planned; reserve the dashboard route/navigation for its actual delivery.
- [ ] Run lightweight UI/BFF checks, then mounted synthetic browser journeys: platform downgrade review/stale form/read-refresh failure; all four downgrade previews, all-to0 confirmation, affected-only preservation and two-transaction completion messages; strategy level2 under ceiling3; read-only scoped user; keyboard/mobile; expired access with retained history; independent-review proposal cannot gain a direct action after upgrade. Assert no runtime/HTML console errors.

## Task 5 — Explicit cutover, documentation and bounded acceptance

**Files:** create `scripts/cutover_lifecycle_assistance.py`, update `docs/product/features/trade-operations.md`, `docs/product/feature-register.md`, `docs/product/feature-implementation-map.md`, root KNOWLEDGE/FIX guidance and a dated delivery record. Do not rewrite prior dated delivery evidence.

- [ ] Provide rollback-only preview by default. Only an explicit `--apply` records suggested strategy selections from current explicit native policies: DIRECT→3, REVIEW/MANUAL→2. Unconfigured remains0. Never grant an operating tenant a positive subscription automatically; no permissions, economic rows or native history updates.
- [ ] Test repeatability, cross-tenant isolation, retained financial/group-grant hashes and existing prepared work still readable. A new entitlement/assistance revision may require re-preparation before execution; do not rewrite an old proposal to pass new checks.
- [ ] Run final affected backend suites, one frontend regression after integration, typecheck, OpenAPI/generated reproducibility and synthetic browser acceptance. No repeated full Python suite. Report actual counts, failed gates and unsupported paths; local migration/activation is separate from test success.
- [ ] Reconcile F51/F24 and delivery documentation with implemented behavior, online sources and deferred dashboard/billing boundaries. Verify Markdown links and scoped diff; preserve unrelated work and do not commit/push unless requested.

## Delivery B handoff, not part of these implementation tasks

Build the general event worklist next: start with upcoming/overdue bond maturity; date/strategy/type and actionable/informational filters; detail and appropriate action by selected assistance level; then integrate FX-forward maturity. Use Task2 decisions. Retained notifications must not themselves prove settlement or payment. Coupon information can be added after its informative versus actionable semantics are defined. A separate dashboard plan will define event identities, refresh/reassessment, deduplication and full-population query behavior before coding that detector.

## Self-review

Spec sections map to Tasks1–5: ceiling/storage/admin→1; per-event selection/permissions→2; explicit downgrade policy transitions and authority separation→2b; native execution, reviews, retries and downgrade races→3; user-facing states→4; cutover/history/docs→5. The five review-focus risks each have an explicit owning test task. This plan adds no notification detector, payment integration, automatic financial scheduler or new instrument economics. It is intentionally a foundation delivery followed by a separate dashboard delivery.
