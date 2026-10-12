# Documentation, conversation and implementation reconciliation

**Status:** Documentation review completed; validation results below  
**Content type:** Dated quality review  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-12  
**Code baseline:** main `76f6292`, implementation `c96c614`

## Outcome

The platform has substantial working local-alpha reference/booking/access/data/review workflows. It is not a production tenancy platform, complete settlement/accounting system, universal instrument valuation engine or full fund NAV service. The [feature register](../../product/feature-register.md) now identifies 50 capabilities; eight focused records carry per-item desired scope, backend/frontend state, cuts/trade-offs, weaknesses, remaining work and Markdown evidence links.

The existing domain organisation was retained. A capability-led entry point and complete spec/plan/delivery indexes improve retrieval without mass file moves or loss of historical evidence. Add future desired features to the register, not to another chronological progress log.

## Review scope and limits

Inventory: 355 tracked Markdown files at the baseline, including 286 under `docs/` and 93 immutable archived snapshots. The active document inventory was read for titles/status/collection; maintained entry points, capability-specific delivery/specification evidence and relevant backend/frontend ownership/guard paths were inspected for reconciliation. Conversation decisions supplied desired scope and explicit deferrals. Archived snapshots and dated plans remain historical evidence, not rewritten current-state claims.

Source checks covered access management/sessions/actions, tenant workspace, strategy/reference/proposal APIs, shared/product booking, navigation/BFF transport, market-data rights/priority/policy/calendar/normalization boundaries, position support/reconstruction, valuation product guards/FX/accrual/flows/operator review and storage. This is **not an exhaustive line-by-line code/security audit** or a rerun of browser/financial acceptance. Absence of an established end-to-end path is labelled FOUNDATION/PARTIAL, not inferred delivered from a table or helper.

No operating DB query/write, seed, migration, app restart or provider acquisition was performed for this review. Previous activation counts are dated evidence, not new live-state certification. No application behaviour was changed.

## Drift corrected or explicitly classified

| Previous ambiguity/drift | Reconciled current position |
| --- | --- |
| “Tenant databases provide isolation” sounded deployed | Shared local DB with logical scopes is implemented; separate topology/routing and production identity remain foundations. |
| Module catalogue looked like delivered products | AMC/fund operations/distribution/UCITS/risk records distinguish labels/foundations from complete specialist workflows. Structured-product terms/booking exist but full management does not. |
| September access page still deferred UI/middleware/groups | Local platform/tenant management, action checks and context switching are delivered; production identity/commercial provisioning still pending. |
| Single-currency TRADE P&L described as current | Position-owned economic v3 supports governed FX, fund NAV/clean bonds and assessed economic inputs; derivative/final-maturity/full NAV/cash-stock paths remain excluded. |
| Yahoo events “cannot establish proof” read as permanent | Later anchored split-only RAW reconstruction and activation supersede the initial blocker, under explicit provider-method assumptions. It does not certify official data or replay quantities. |
| OFFICIAL_CLOSE versus CLOSE looked like mandatory parallel feeds | Current CLOSE family separates optional official closing designation; old vocabulary remains compatibility history. |
| “Latest EoD” suggested unrestricted last-price fallback | Flexible policy is rule coverage; matched missing input still fails, and freshness/semantics/rights remain explicit. |
| Generic tenant data supplier implied upload UI | Ownership/ingestion foundation exists; generic self-service upload API/UI does not. Saved priority suggestions are not automatic publication. |
| Lifecycle prototype implied resumption/completion | FX-delivery code/evidence is retained but parked/not signed off. User-deferred settlement/accounting remains deferred. |
| Catalogue and strategy labels implied universal economics | Product-specific creation, listing, booking and valuation capabilities remain distinct. |
| Tenant trade properties were described as “unlimited” | The schema is not a fixed field1…30 layout, but provisioning enforces 1,000 active field definitions per tenant and a separate 1,000-tag quota. |
| P&L “immutable results” wording blurred stored evidence and workflow status | Financial attribution versions and operational events are protected/append-only, while attempt and batch statuses transition; a later publication marks the prior batch `SUPERSEDED` without rewriting its financial values. |
| Old delivery index ran pytest against `fortem_secm` | Current instructions use owned disposable databases; guard/CI isolation and forward-only migration rules are explicit. |
| Old merged-work tests could be read as one clean full pass | Preserve partitioned failing diagnostics and successful focused remediation; no single clean final full-suite rerun is claimed. |
| Prior browser success was generalized to newer UI | Earlier trade journeys are dated evidence; latest access/P&L/market chart interactions still need appropriate sign-off. |

## Main weaknesses to retain visibly

1. **Acceptance:** Latest financial/provider reconciliation and visual/mobile/accessibility walkthroughs are incomplete. The reported explorer date/basis refresh concern is a reproduce/sign-off item, not a bug declared fixed by docs editing.
2. **Economic completeness:** Corporate-action quantity replay, derivative/final-maturity handlers, complete cash/NAV, automated accrual/income/reset reconciliation and wider attribution ownership are missing.
3. **Data operations:** Full pre-valuation validation/review, tenant uploads, authoritative ongoing calendars, commercial rights administration and periodic entitlement evidence are incomplete.
4. **Production/scaling:** Local identity is not production authentication; synchronous workers, history materialization, audit durability, deployment isolation and large-registry/read performance need separate hardening.
5. **Maintainability:** Some large API/repository surfaces and test-fixture assumptions require care. Capability records now expose cuts; they do not eliminate technical debt merely by documenting it.

These are existing gaps, not authorization to implement deferred products during this documentation task. Relevant next work should be selected through the register and scoped acceptance criteria.

## Best-practice review

Opened/read on 2026-10-12:

- [Diátaxis primer](https://diataxis.fr/start-here/): distinguish factual reference, explanation and task-oriented guidance. Application: capability/reference pages separate from dated plans, evidence and safe run instructions.
- [arc42 risks and technical debt](https://docs.arc42.org/section-11/): retain identified risks and mitigation directions. Application: explicit per-feature weaknesses/remaining work plus the prioritized themes above.
- [arc42 architecture decisions](https://docs.arc42.org/section-9/): retain significant decisions and consequences. Application: a [documentation decision](../../governance/decisions/2026-10-12-capability-documentation.md), stable historical paths and supersession pointers rather than hidden evidence rewrites.

These living engineering guides are recommendations, not regulatory requirements. Fifty IDs, grouped records, status vocabulary and folder choices are project decisions inferred from the user's needs. Sources are also registered in the [evidence register](../../research/evidence-register.md).

## Validation

Documentation-only checks cover feature row/record consistency, required per-item fields, local Markdown targets/anchors, changed-file whitespace and unchanged archive/application source. No full application regression run is warranted for Markdown-only edits. Results are recorded after those checks below; this review must not imply new database/browser/financial acceptance.

The initial targeted link check was not sufficient for headings containing an em dash. A corrected repository-wide inline-link pass used [GitHub's documented section-link rules](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#section-links): 368 Markdown files and 1,369 local link candidates were scanned. It found three broken anchors in maintained capability records; those were corrected. After correction, all 1,368 local targets whose files exist resolve, with no broken anchors outside the archive. One relative code link in the preserved September archive points to a source file that was not retained in that snapshot; it remains historical and was not rewritten.

The 50 feature IDs and required record sections remain consistent. The register contains 29 ALPHA, nine PARTIAL, six FOUNDATION, three DEFERRED and three NOT IMPLEMENTED entries. These are bounded capability counts, not completion percentages. Scoped whitespace checks allow existing intentional Markdown hard line breaks. Only Markdown is changed, with no archived snapshot changes; no schema/source/test files are modified. Repository integration is recorded separately in Git commit/push history.

## Second pass — behavior and historical supersession

A further source/test reading checked tenant/group actions and local sessions, cash historical definition selection, bounded option/FX/future economics, valuation recognition, cancellation reconstruction, provider ranking, FX resolution, calendar composition and economic-flow/accrual ownership. Tests were inspected for assertions; application suites were not rerun for these documentation changes.

Corrections and clarifications:

- The implementation map now links the existing tenant-edit, Users/Groups, context-selector and profile component/handler tests. The previous absence wording missed component tests outside the route directories.
- The maintained tenancy architecture no longer lists delivered middleware/navigation/group administration as deferred.
- Yahoo's reporting-only state and the permission task's single-currency/RAW blockers are clearly dated, with links to later scoped activation and economic/RAW delivery. Earlier P&L retirement, correction handling and instrument-integrity reports identify their later implementation evidence.
- F23 states that recognition overrides can only defer the UTC execution date, require a reason, and do not enable historical cash booking across materially changed current/reference economics.
- F22 identifies the opening-boundary restriction on correction replay; a historical removal is distinct from an unsupported in-period removal.
- F28 states the actual selection order: newest eligible market date, then configured dataset rank, then observation/arrival tie-breakers; explicit dataset pins and CUSTOM exclusions remain binding.
- F37 states the current FX gate: RAW rates, explicit timing, sealed governed calendar, bounded staleness, and inverse-pair use only when no direct pair with an active qualifying FX series is found and inversion is permitted.

These clarify existing behavior and its operational consequences. No additional product scope, test execution, live activation or financial acceptance is claimed.

Second-pass verification: 368 Markdown files, 1,387 resolved local inline links and zero current-document file/heading failures; the same single archived missing source target remains. All 50 register IDs match the 50 capability sections, and all 115 implementation-map source line anchors remain within existing files. The code baseline is still `76f6292`; no Python/TypeScript/JavaScript source changes are present in the working tree.
