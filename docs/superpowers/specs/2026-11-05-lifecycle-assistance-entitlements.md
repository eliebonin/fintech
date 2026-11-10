# Lifecycle assistance subscriptions and strategy configuration

**Status:** Delivery A implemented; Delivery B now has [bond discovery](../../delivery/lifecycle-worklist-20261105.md); other detectors remain deferred. [Current delivery and evidence](../../delivery/lifecycle-assistance-entitlements-20261105.md). **Reviewed:** 5 November 2026. **Capability:** F51/F24.

## Product decision

Offer one Lifecycle management module with cumulative assistance tiers. The platform administrator enables the tenant's maximum tier. A tenant configures an available level separately for each strategy and supported event type. Individual action permissions, strategy scope, data readiness and review requirements remain independent controls.

| Tier | Label | Capability |
| --- | --- | --- |
| 0 | Fully manual | Existing authorised trade booking; Ops identifies and handles events themselves. No new lifecycle discovery/preparation service. |
| 1 | Notifications | Lifecycle event worklist/notifications, with manual handling. |
| 2 | Assisted preparation | Tier 1 plus prepared entries that Ops completes and reviews before posting. |
| 3 | One-click booking | Tier 2 plus a fully prepared entry Ops explicitly clicks to post when current rules permit direct execution. |

Higher subscriptions include lower assistance levels. No unattended scheduler is implied. A purchased tier is an access ceiling, never a command to upgrade strategies, grant users actions or remove an independent-review requirement.

## Two bounded deliveries

**Delivery A, implemented:** subscription ceiling, strategy/event choices, reviewed admin controls, authoritative enforcement in existing bond/FX maturity handlers, downgrade recovery and acceptance. It enables the commercial/configuration foundation and integrates existing preparation/posting; it does not implement the general event detector/dashboard.

**Delivery B, next:** general chronological event worklist, actionable/information filters, upcoming/overdue bond maturity discovery, then FX-forward maturity. This is what delivers the complete Tier 1 notification experience. Until then, subscription/configuration UI must explicitly label notification discovery as planned; do not describe granting Tier 1 as delivery of an operating notification service or start charging through this project.

Payment collection, Stripe integration, invoicing, usage metering, product-specific pricing, email/SMS delivery, broad derivative lifecycle, settlement, accounting and new valuation formulas are outside Delivery A.

## Pre-delivery implementation and reuse (design baseline)

- [Tenant module entitlement](../../../security_master_schema/models.py) and [module commands](../../../security_master_schema/access_management.py) already support platform-owned subscriptions and audited changes. Current ordinary toggles are boolean; same-day changes use immutable before/after audit but update that day's entitlement row.
- [Authority](../../../security_master_schema/lifecycle_authority.py) already binds lifecycle actions to the strategy, requires trading permission for posting and enforces independent selected-user/real-operator review.
- [Bond](../../../lifecycle/bond_service.py) and [FX](../../../lifecycle/fx_service.py) retain product policies, proposals, native posting receipts, source fingerprints, allocations and cancellations. Existing DIRECT/REVIEW/MANUAL values describe execution/review paths; they are not subscription tiers.
- [Lifecycle HTTP adapter](../../../apps/reference_api/bond_redemption_routes.py) serves both products; FX is registered under `/v1/lifecycle/fx-forward` in `main.py`. There is no separate FX maturity router file to invent.
- [Platform UI](../../../apps/ops-console/src/components/platform-tenants.tsx), [existing lifecycle UI](../../../apps/ops-console/src/components/bond-redemption-console.tsx), existing opaque-session BFF and generated contracts are reused.

## Ownership and storage

Register stable platform module code `LIFECYCLE_MANAGEMENT`. Its presence and an explicit subscription record are both required for a positive tier; module absence, suspension, expiry or absent tier record yields available ceiling 0. Ambiguous entitlement history produces an explicit configuration error, not a guessed tier.

Add two typed, normalized append-only relations:

1. `ten.tenant_lifecycle_subscription`: tenant/revision, predecessor revision, maximum tier 0–3, source (`MANUAL`, `TRIAL`, `CONTRACT`, `MIGRATION`), reason, verified platform actor/real operator and UTC recording time. Initial implementation changes take effect immediately; future scheduling is deferred. Existing effective-dated module state still limits current use.
2. `ten.strategy_lifecycle_assistance`: tenant/strategy/event type/revision, predecessor revision, selected tier 0–3, reason, verified actor/real operator and UTC recording time. Composite owner FK must bind the strategy to the tenant. Supported event types initially are `BOND_MATURITY` and `FX_FORWARD_MATURITY`.

Use checks, composite ownership/revision FKs, latest-revision indexes and append-only protection consistent with current profile/configuration history. Do not use an untyped settings JSON or four independent paid-module flags. No generic subscription engine is needed.

The reviewed subscription command updates the existing module entitlement and appends the typed tier/audit atomically. Generic boolean module mutation must reject `LIFECYCLE_MANAGEMENT` and direct callers to the tier editor; it cannot become a second mutation authority. Changing other modules remains unchanged. No subscription command inserts user/group grants or alters financial records.

Strategy assistance and current product processing policy remain separate records for separate questions: assistance selected versus execution/review requirements. Read DTOs combine them with provenance; neither silently overrides the other. Saving a policy that requests a currently unavailable path is refused with a readable explanation.

## Runtime rules

A decision returns `maximumTier`, `selectedTier`, available choices, subscription/assistance revisions, current processing-policy revision, handler support and permission/readiness reasons. Never calculate `min(selectedTier, maximumTier)` and silently execute a different workflow. A selection exceeding the ceiling remains visible as `BLOCKED_BY_SUBSCRIPTION` until explicitly changed or access restored. The reviewed bulk transition below creates explicit policy revisions; it is not a runtime clamp.

- Configure assistance: require LIFECYCLE_CONFIGURE on the same strategy; tier must be available and event supported. Tenant administration alone is not a strategy bypass.
- Tier 0/1: no assisted financial preview, proposal preparation or assisted posting. Existing ordinary trade booking/corrections and authorised historical lifecycle reads remain available under their existing controls.
- Tier 2: allow current supported prefill/preview, retained preparation and reviewed completion. Confirmations must reference a current retained proposal; a browser assertion that a form was reviewed is insufficient.
- Tier 3: permit Tier 2 work and direct one-click execution only when the selected strategy assistance is 3, the native processing mode is DIRECT, source inputs are ready and the user has current required actions. A tenant ceiling of 3 with strategy level 2 cannot call the direct endpoint.
- REVIEW continues to require an independent approver, regardless of subscription. Do not rename REVIEW to Tier 2 or DIRECT to Tier 3. Non-REVIEW (MANUAL or DIRECT) assisted confirmation, when selected with level 2 or 3, must use retained preparation plus the existing LIFECYCLE_BOOK/TRADE_WRITE authority; this is operator confirmation, not an independent approval. Native DIRECT execution remains the separately gated path.
- Missing price, conflicting allocation, retired reference or stale proposal cannot be repaired by upgrading a subscription. Existing economic validators remain authoritative.
- Coupon schedules, existing coupon payment confirmations, existing interest maintenance and ordinary financial audit are not newly paywalled by this change.

Apply checks below HTTP so API calls and future workers cannot bypass UI restrictions. Do not modify ACTION_MODULES by adding LIFECYCLE_MANAGEMENT as an alternative to TRADING: its existing set-intersection semantics are OR, whereas these commands require trading authority AND the lifecycle entitlement.

## Reviewed downgrade choices

A requested commercial downgrade must include a clear configuration transition. Downgrade preparation pins the proposed lower ceiling; replacements must be within both that ceiling and the currently available subscription. It cannot grant a feature that is currently unavailable. Preserve existing settings that remain within the new ceiling by default. Offer these explicit tenant choices:

| Choice | Settings already allowed | Settings above new ceiling |
| --- | --- | --- |
| Preserve valid; reduce higher to new maximum — recommended | Unchanged | New revision at the new maximum |
| Preserve valid; move higher to a chosen tier | Unchanged | New revision at selected tier 0 through the new maximum |
| Set all currently configured events to a chosen tier | Explicitly replaced too | New revision at selected tier; Tier 0 is a visible fully-manual preset |
| Keep configuration unchanged | Unchanged | Retained and blocked until explicitly resolved |

The recommended radio choice is a proposal for human review, not an automatic system fallback. Example, ceiling3→2 and configured tiers3,2,1,0: the recommended preview is2,2,1,0; a chosen fallback1 gives1,2,1,0; setting all to0 gives0,0,0,0. Do not increase an existing lower choice merely because the target tier is higher than that choice. The deliberately broader Set all option requires a separate confirmation that it replaces currently valid settings, including settings below the target tier.

“All” means every CURRENT explicit supported strategy/event configuration in the tenant, not the loaded page, historical revisions, trading positions, future strategies or future event types. Unconfigured remains0. A full-population change requires LIFECYCLE_CONFIGURE across the whole target scope; partial users may review/apply only explicitly selected authorised targets, with no claim that the whole tenant was updated. Apply the reviewed population atomically, using current revisions and a whole-population hash. A new/changed target since preview invalidates the review. Never silently skip inaccessible or conflicting rows.

Commercial administration does not confer tenant strategy authority. For Delivery A, tenant-authorised users first preview/apply the chosen configuration transition under their normal tenant context. The platform administrator then refreshes the impact and applies the lower ceiling under platform context. These are explicitly TWO audited transactions, not a falsely atomic wizard: if the commercial change fails, the independently approved lower strategy settings remain and the UI reports that result. A subscription preview must detect any intervening policy re-increase before commit.

No extra approval-request subsystem is needed for this first delivery. An eventual tenant self-service billing portal can coordinate these steps later; it must not merge platform and tenant privileges. A platform-only downgrade, expiry or suspension without an authorised transition leaves selections unchanged and blocks those above the ceiling. If paid access is revoked immediately, enforcing the ceiling cannot wait for Ops to review fallback choices.

Every changed event receives a new assistance-policy revision with reason and actor. Keep prior choices and proposal/booking evidence. Native independent-review requirements, allocation rules, quantities, prices and user permissions are not changed by a downgrade. DIRECT and MANUAL retain their original review meaning: under selected assistance2, either non-REVIEW policy may use retained operator confirmation; a direct no-proposal booking still requires assistance3 plus native DIRECT. This allows3→2 assistance reduction without silently rewriting approval policy.

Changed selections or subscription revisions make open preparations require reassessment/re-preparation before new execution, even if the new tier still supports preparation. Do not convert a one-click/prepared event into an independently approved event, submit a booking during the downgrade, or cancel an existing booking. Upgrading later never restores old higher selections automatically.

## Changes, concurrency and retries

Use optimistic revisions and a reviewed impact hash for platform tier changes. Show counts of affected selected policies and retained proposals; do not return trade quantities/prices or financial payloads to the platform administrator. Enforce platform authority outside tenant impersonation. Strategy policy changes show their exact before/after, target event and reason.

Subscription changes and lifecycle financial commands coordinate through one documented tenant lifecycle advisory lock: exclusive for subscription changes; shared for financial use/configuration. Acquire it before existing instrument/configuration/strategy locks; retain it through outer transaction commit. A committed downgrade blocks subsequent financial effects. A financial command that already holds the shared lock completes before a waiting downgrade; the UI must not claim already-started transactions were cancelled. No lock order may be reversed by preview, preparation, approval, correction or module-change paths.

Every first-time financial effect rechecks current subscription, selected tier, native processing policy, action scope and source proof in its transaction. A changed revision after preparation requires refresh/review; do not mutate the original proposal. No automatic cross-mode fallback.

Successful unchanged idempotent replay returns the original receipt only after current native identity/action/strategy checks, without new financial effects; a downgrade does not erase that receipt. A different/new request must satisfy the current tier. Cancellation/correction of existing records retains native TRADE_CORRECT authority and is not blocked merely by loss of a paid assistance tier. Scope/identity revocation still denies access.

## UI

**Platform → Tenants:** one Lifecycle assistance selector, levels 0–3, current revision/source, concise tier comparison, and Review change. Review requires a reason, shows the exact change and affected-policy/proposal counts, and explicitly confirms downgrade impact. Keep confirmed-write/read-refresh failure handling and stale-form conflicts. Existing unrelated module checkboxes remain.

**Strategy → Overview → Lifecycle assistance:** a separate card/link from Trade configuration. Per supported event, show selected tier, subscribed ceiling, current review requirement, availability status and explanatory disabled higher choices. Ordinary editing reviews/saves one event at a time. A separate Downgrade preparation action supports the explicit reviewed bulk transitions above; no implicit bulk change, tenant-default inheritance or product-wide auto-upgrade. A missing choice displays Fully manual / not configured, not the old REVIEW default as a paid grant.

**Existing lifecycle workspace:** display selected assistance and subscription constraint. Distinguish insufficient subscription, insufficient permission, unsupported handler and invalid/missing data. Retained history remains readable. Existing independently reviewed preparations cannot become one-click entries merely because the ceiling rose. Notifications are explicitly labelled planned until Delivery B exists.

## Migration and acceptance

Use the next available additive migration after the verified current head; 112 is a provisional number, not reserved authority. Register the module and relations without granting any operating tenant a paid capability or changing group grants. Preserve existing native policy/proposal/posting bytes. A trusted preview can list existing explicit policies and suggest assistance 3 for DIRECT or 2 for REVIEW/MANUAL; applying those selections requires an explicit cutover command. Unconfigured strategies default to 0. No automatic grandfathered commercial access, financial booking or valuation.

Verify initially with pure decision tests, then disposable DB/API tests and synthetic browser journeys. Cover all tiers, BOTH ceiling and selected level, every existing bond/FX entry point, two-person review, MANUAL retained confirmation, forged direct calls, scoped reads/counts, stale preview/proposal, downgrade/upgrade, runtime expiry/suspension, cancellation, receipt replay, tenant isolation and commit races. Compare financial and access-grant hashes before/after local activation. No full Python suite for every iteration; run affected suites and broaden for demonstrated regressions. Keep production identity/billing and full portfolio financial sign-off separate.

## Research basis

Checked 5 November 2026. [Stripe entitlements](https://docs.stripe.com/billing/entitlements?dashboard-or-api=api) separates product features from commercial packages and provisioning. Applied as a platform-owned ceiling; Stripe integration is not required now. [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) supports default denial, current-request validation, protected object identities and tested authorization logic. Applied to server enforcement and scoped proofs. [WAI radio-group guidance](https://www.w3.org/WAI/ARIA/apg/patterns/radio/) supports a labelled single-choice control; use native controls with visible descriptions. The particular four tiers, downgrade policy and rollout are project design decisions, not requirements imposed by these sources.

[Implementation plan](../plans/2026-11-05-lifecycle-assistance-entitlements.md).
