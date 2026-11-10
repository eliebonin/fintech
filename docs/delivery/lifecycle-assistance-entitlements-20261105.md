# Lifecycle assistance subscriptions — 5 November 2026

**Status:** Implemented bounded alpha (Delivery A). **Capabilities:** F51/F24.
[Accepted design](../superpowers/specs/2026-11-05-lifecycle-assistance-entitlements.md) · [Execution plan](../superpowers/plans/2026-11-05-lifecycle-assistance-entitlements.md).

## What is delivered

The platform administrator sets one tenant-owned `LIFECYCLE_MANAGEMENT` subscription ceiling. Tenant-authorised operators select assistance separately for each strategy and supported event: `BOND_MATURITY` and `FX_FORWARD_MATURITY`. No other product handler is implied.

| Tier | Available behavior in this delivery |
| --- | --- |
| 0 Fully manual | Ordinary authorised booking remains. No assisted lifecycle preview or preparation. |
| 1 Notifications | Selection/entitlement foundation only; the general notification detector/dashboard is **not delivered**. The UI labels this explicitly. |
| 2 Assisted preparation | Retain a proposal, then review/complete and explicitly confirm it, or obtain independent approval when native REVIEW requires it. |
| 3 One-click booking | Tier2 plus Ops-triggered direct posting, only when this strategy/event also selects3 and its native processing policy permits DIRECT. No unattended booking. |

A ceiling never grants user actions, removes strategy scope, upgrades selected strategies or bypasses data/allocation readiness. TRADING and the existing action-bound permissions still apply. Native DIRECT/REVIEW/MANUAL remain execution/review controls, not commercial tiers. REVIEW requires an independent selected user **and** real operator. A non-REVIEW retained confirmation requires LIFECYCLE_BOOK and TRADE_WRITE on the same strategy; preparing it still needs LIFECYCLE_PREPARE.

## Where to use it

- **Platform → Tenants:** Lifecycle assistance subscription; choose0–3, review impact, provide a reason, explicitly acknowledge blocked workflows and confirm. The ordinary lifecycle boolean checkbox is replaced by this control. Other module controls are preserved.
- **Strategy → Overview → Lifecycle assistance:** one row per supported event, current selected/available tier, native review mode and status. Authorised users edit, review and save one event. Missing settings display0; above-ceiling settings remain visible and blocked.
- **Tenant profile → Lifecycle assistance:** `/tenant-profile/lifecycle` prepares a commercial downgrade's strategy changes. Searchable, scoped strategy register and per-event selection; preview covers the full requested current population, not its loaded25-row page.
- **Trades → Lifecycle:** existing bond/FX sections display subscription/selection constraints, preparation, retained confirmation or independent approval, direct actions when eligible, history and native correction. Notifications remain labelled planned.

The Strategy card is integrated in `app/strategies/[strategyId]/page.tsx`; this replaces the plan's proposed integration in `strategy-workspace.tsx` without duplicating its state.

## Downgrades are explicit, reviewed changes

| Choice | Before3,2,1,0 when new ceiling is2 |
| --- | --- |
| Preserve valid; cap higher (recommended) | 2,2,1,0 |
| Choose affected-only fallback1 | 1,2,1,0 |
| Set all configured events to0 | 0,0,0,0; additional confirmation required |
| Leave unchanged | 3,2,1,0; first workflow blocked after commercial downgrade; preview only, no fake update |

The all-events choice may also deliberately replace valid lower choices with another permitted tier, with its broader confirmation. Unconfigured and future strategies remain0. Explicit selection narrows the population; it does not change the affected-only rule. Full-population commands require action-bound configure coverage of every current target, which can come from several SELECTED groups; an unrestricted ALL grant is not required. Hidden targets deny the full-population command without disclosing their rows or counts.

Tenant strategy changes and the platform commercial change are **two audited transactions** with different authority. Saved strategy changes persist if a later commercial change is cancelled or fails. A platform downgrade, expiry or suspension without tenant changes retains higher choices but blocks their use. There is no silent fallback, automatic clamp, permission grant or automatic restoration after an upgrade.

## Backend, database and audit

- [Typed schema](../../security_master_schema/lifecycle_entitlement_tables.py): append-only `ten.tenant_lifecycle_subscription` and `ten.strategy_lifecycle_assistance`, revisions/predecessors, reason, selected actor and real operator; composite tenant/strategy ownership. [Migration112](../../alembic/versions/20261105_112_lifecycle_assistance.py) registers the module without tenant grants.
- [Commercial service](../../lifecycle/entitlements.py) resolves current module/tenant status and a typed ceiling; absent/inactive/expired access is0. Overlapping entitlement periods are excluded by the existing DB constraint; the resolver also rejects ambiguity. Reviewed impact binds choices, native policies and exact pending preparation identities/hashes.
- [Assistance service](../../lifecycle/assistance.py) resolves scoped choices and operation decisions below HTTP. [Transitions](../../lifecycle/assistance_transitions.py) validate exact reviewed populations, lock deterministically and atomically append changed choices/audit only; no-op choices acquire no false revision.
- [Thin API](../../apps/reference_api/lifecycle_assistance_routes.py): platform GET/PUT subscription and POST preview; tenant GET options/view, POST configuration and POST transition preview/apply. Generated contracts and exact BFF allowlists preserve verified opaque sessions, expected tenant and same-origin writes.
- Native [bond](../../lifecycle/bond_service.py) and [FX](../../lifecycle/fx_service.py) commands enforce both ceiling and selection, retain assistance proof in new inputs and revalidate it before financial effects. `/confirm` consumes a retained non-REVIEW proposal. Changing entitlement/selection revisions makes prepared work stale; retained bytes are not rewritten.
- Tenant lifecycle advisory locks are shared for native use/configuration, exclusive for commercial changes; acquire before instrument/configuration/strategy locks and hold through outer commit. Started shared transactions complete before waiting downgrades; later effects see the downgrade. Actual PostgreSQL blocking/release is regression-tested.
- Successful unchanged receipt replay still requires current native identity/action/scope authority, then returns the original receipt without a new paid-feature effect. Paid downgrade alone does not erase receipts. Native mode/authority changes can still require a different authorised read/recovery path. Cancellation retains native correction checks and is not commercially gated.

## Activation and technical cutover

Migration112 is applied to the local app DB. Financial/native-policy/proposal/posting and permission/module-grant hashes are compared before/after activation. No positive operating subscription, assistance selection, user grant, trade, payment or valuation is created by migration/startup.

[Explicit cutover tool](../../scripts/cutover_lifecycle_assistance.py) defaults to rollback-only preview. An explicit `--apply` can copy **current explicit** native DIRECT→3, REVIEW/MANUAL→2, under the shared lifecycle/configuration lock, with technical audit. Re-running preserves existing selections. It never grants paid access or rewrites native history. New native policies for tenants appearing after its initial discovery need a subsequent invocation. Local activation does **not** apply this policy-copy cutover automatically.

To enable an operating workflow intentionally: platform grants a suitable ceiling; a tenant user with existing scoped configure authority selects an available event tier; authorised Ops verifies native review/pricing/source settings, prepares again where needed, then posts through the appropriate path. No user permissions were invented to make this walkthrough pass.

## Verification

- New behavior was reproduced first with focused failing tests, then verified in disposable databases. Final affected backend regression: **71 passed**; additional bond-valuation/access/cutover checks: **24 passed**. The full Python suite was not run.
- Full frontend regression: **249 files /1,165 tests passed**; new platform-preview BFF security checks: **3 passed**.
- Mounted synthetic lifecycle, current trade-profile and ticket browser acceptance: **8 passed**, including 3 lifecycle journeys, covering commercial review/acknowledgement, confirmed-save/read-refresh failure, strategy conflict/intention retention, all four downgrade previews, all-to0 confirmation and mobile layout. The real administration CSS is included: the live-browser radio-sizing defect was reproduced, then fixed with scoped 18px controls and row labels. Follow-up 5 November: the two formerly obsolete `lifecycle-allocation-layout.spec.ts` cases were rewritten for the current profile editor and immutable publication flow. They now cover responsive long-label controls, keyboard focus, mandatory reason/review and the new-version payload without restoring global allocation authority. The earlier combined-run timeouts remain historical evidence; BROWSER-LEGACY-001 is resolved; all **10** current allocation/lifecycle/profile/ticket browser journeys pass together.
- TypeScript and OpenAPI/generated-contract reproducibility are checked on the final working snapshot. The generated `git diff --exit-code` gate cannot distinguish intended uncommitted contract changes from drift; regeneration hashes are used rather than staging unrelated work.
- Evidence/commands: `.superpowers/sdd/2026-11-05-lifecycle-assistance-entitlements/`. The in-app browser verified the live platform selector/review, normal 18px radio rows, unchanged Tier0 defaults and the tenant administrator’s explicit lifecycle-permission denial. Its captured warning/error console was empty. Activation and walkthrough evidence are recorded there separately from synthetic financial acceptance. No live financial commands were used for testing.

## Subsequent delivery

The [bond-maturity worklist](lifecycle-worklist-20261105.md) now supplies the first detector and contextual portal journey. The foundation verification above remains its original evidence; FX/other discovery and billing are still follow-up scope.

## Deliberate limits and next work (foundation delivery boundary)

General event discovery, actionable/informational filters and upcoming/overdue notifications are the next delivery. There is no billing provider, invoicing, pricing/metering, email/SMS, scheduled booking or account settlement. Only the existing bounded plain-bond/deliverable-FX maturity handlers consume this foundation. It does not add generic manual lifecycle tickets or other instrument economics. No production identity or commercial readiness is certified.

## Research applied

Checked 5 November 2026: [Stripe entitlements](https://docs.stripe.com/billing/entitlements?dashboard-or-api=api) supports separating commercial feature provisioning from packages; applied as a ceiling, without integrating Stripe. [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) informs default denial, request-time scope checks and tested object authority. [WAI radio guidance](https://www.w3.org/WAI/ARIA/apg/patterns/radio/) informs labelled single-choice controls with visible descriptions; native radios are used. The four tiers, downgrade choices and staged rollout are project decisions rather than externally mandated rules.
