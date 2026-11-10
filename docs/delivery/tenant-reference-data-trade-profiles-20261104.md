# Tenant reference data and strategy trade profiles

**Reviewed:** 4 November 2026. **Status:** implemented alpha; local activation evidence is recorded below. This is a bounded delivery review, not a full repository audit or production sign-off.

## Delivered behavior

Maintain shared sources at **Tenant profile → Reference data**. Custom catalogues retain their original stable record identities; counterparties, brokers and traders use existing canonical organisations and eligible people/users. Sources offer server-side search, pagination, entries, scoped usage and reasoned history. No duplicate organisation master is created.

At **Tenant profile → Trade configuration**, use **Profiles**, **Field library** and **History**. The library owns a field's meaning, scalar type and catalogue binding; it has no global Required toggle. Profiles select standard/custom fields as Required, Optional or Not used and specify lifecycle Allocation, Inherit or Input behavior. Standard sources remain fixed. A row editor, separate lifecycle tab and explicit review avoid mixing catalogue maintenance with booking rules. Clone copies rules, not source values.

Published versions are immutable. Publishing does not change any assignment or default. Set an explicit tenant creation default, then review adoption on **Strategy → Overview → Trade configuration**, or select writable strategies in **Apply version**. Batch adoption validates every selected strategy and commits all or none. Read-only strategy users can inspect the pinned version without assignment controls. Usage counts, histories and assignment targets apply strategy scope before pagination.

All supported native writers—cash/listed instruments, FX forwards, options, futures, structured products, bonds, swaps and AMCs—resolve the assigned version. Fund transfers/reinvestments, linked corrections, Excel template/review/confirmation and bounded bond/FX maturity handlers use the same authority. Native product requirements remain mandatory even when a profile marks a standard field Not used. Stale configuration is a conflict; ticket reload preserves entered execution data. Imports require a new current review instead of silently changing rules.

## Data and code boundaries

- [Schema](../../security_master_schema/trade_profile_tables.py): five normalized relations, `trd.trade_profile`, `trd.trade_profile_version`, `trd.trade_profile_field_rule`, `ten.strategy_trade_profile_assignment`, `ten.tenant_trade_profile_default`. Version membership and assignment/default revisions are append-only and owner-scoped.
- [Migration 111](../../alembic/versions/20261104_111_trade_profiles.py): additive relations; nullable booking profile/version proof; database-derived source-inheritance markers and deferred provenance checks. Existing economic values and immutable BOOKED payloads are not rewritten.
- [Reference domain](../../tenant_reference/sources.py) owns shared source discovery/options/usage; [catalogue commands](../../tenant_reference/catalogues.py) own audited maintenance. [Profiles](../../trading/profiles/) own publication, resolution, assignment, impact checks and cutover below HTTP.
- [API](../../apps/reference_api/trade_profile_routes.py) and [reference API](../../apps/reference_api/tenant_reference_routes.py) own transport and audited transactions. BFF routes verify opaque context and use exact path allowlists.
- [Profile UI](../../apps/ops-console/src/features/trade-profiles/) and [reference UI](../../apps/ops-console/src/features/tenant-reference/) separate source maintenance, field meaning, profile rules and strategy adoption. Searchable selectors submit canonical identities, not display labels.

TRADE_CONFIGURE governs configuration. Adoption additionally requires STRATEGY_WRITE for each strategy. Inspection uses STRATEGY_READ; creation-default discovery uses STRATEGY_CREATE. Booking/lifecycle consumers retain their native action and scoped authority. No new permission grants accompany this change.

## History, allocations and source retirement

New trades retain the exact profile version, assignment revision and configuration hash. Successful receipt replay preserves its original result; it does not rebook under a newer profile. A missing strategy assignment is an explicit conflict, never a runtime tenant-default fallback.

Changing allocation dimensions assesses complete eligible history and frozen economic scopes before adoption. Open classified dimensions cannot disappear or gain missing required classifications silently. Booking and assignment share lock order; a waiting adoption rechecks a concurrently committed trade. No FIFO, tax logic, economic aggregation across incompatible contracts, payment generation or historical relabelling is added.

Label-only field successors preserve semantic identity. New type/source meanings require another field code. Old installations may contain earlier repurposed optional input families: Input behavior uses compatible definition IDs only; Allocation/Inherit reject mixed meanings rather than aliasing them. Source-preserving corrections and lifecycle postings may retain exact original hidden/retired values only with server-verified ownership and original source evidence. Deferred database checks require the completed correction links or actual lifecycle posting receipt; fabricated JSON proof alone is insufficient.

The trusted [cutover command](../../scripts/cutover_trade_profiles.py) copies actual existing tenant settings into a Standard profile and materializes current strategy assignments. It is explicit, repeatable and unavailable as an HTTP fallback. Existing global required flags/allocation rows remain historical provisioning inputs, not a second booking authority. Cutover creates no trades, financial runs, source values or grants. Preview rolls back; apply verifies retained financial/grant hashes.

## Verification

- Full frontend regression: **249 files, 1,163 tests passed**.
- Final mounted browser acceptance: **8 passed**, including catalogue correction/read recovery, server search, keyboard tabs, immutable publish without assignment, read-only strategy inspection, assignment conflict, cash draft preservation and mandatory FX counterparty.
- Consolidated focused backend regression: **66/67 passed** initially; its only failure was the missing `or_` import in scoped audit history. After correction, final scoped API/concurrency/lock-order/domain-boundary checks: **51 passed**, including that API suite.
- Separate source-preservation/native-writer checks: **13 passed**, including real bond post, retired source inheritance, forged evidence rejection and all eight native families. Additional focused import, FX maturity, atomic batch and cutover checks are retained in the task ledger.
- TypeScript check and OpenAPI export check passed. Generated TypeScript reproducibility is checked against the current working artifact; the repository's Git-diff-to-HEAD generator gate necessarily reports uncommitted intended contract additions.
- No full Python suite or operating financial acceptance run was performed. Browser tests use synthetic isolated services. Local read-only walkthrough and migration results are separate from these checks.

## Trade-offs and remaining work

- Published versions have no server-saved mutable draft. Editing uses an in-page draft with navigation protection; closing the page discards it.
- Profiles use all currently eligible source values. Profile-specific source subsets, cascading fields, applicability expressions, inheritance trees, external synchronization and catalogue file import/export are deferred.
- Existing field/tag safety quotas remain; pagination limits metadata reads, never financial trade populations. Profile batch adoption requires an explicitly selected population, maximum 1,000 per command.
- Native product tickets and supported lifecycle handlers remain separate. This does not add option/futures/note lifecycle, notifications, valuation rules or accounting.
- A profile can be deliberately unbookable until required source data is curated. Current backend source/native validation remains authoritative; profile publication does not certify operational completeness for every product.

## Design evidence

The [reviewed design and source links](../superpowers/specs/2026-11-04-tenant-reference-data-trade-profiles.md#research-basis-and-application) record the online research. The UI applies separate field schemes/source maintenance, review before consequential changes, manual activation of data-loading tabs, explicit labels and errors, and contained tables. See [WAI tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/), [GOV.UK check answers](https://design-system.service.gov.uk/patterns/check-answers/), [Atlassian field configurations](https://support.atlassian.com/jira-cloud-administration/docs/configure-field-layout/) and [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html). These support the interaction/constraint choices; the particular profile model is the project's design decision.

## Local activation

Migration **20261104_111** is applied. The trusted cutover created **3 Standard profiles, 3 explicit tenant creation defaults and 10 retained strategy assignments**. Its initial rollback-only preview exposed an older BOOKING_BUCKET choice-to-catalogue conversion; a focused regression reproduced the ordinary-input alias bug, and the fix preserves strict Allocation/Inherit rejection. The final affected cutover/impact/inheritance/database-guard run passed **5 tests**.

Streaming pre-migration and post-cutover hashes match for all **1,549 trades, 1,557 lifecycle events, 500 scalar properties, 491 party roles, 1 tag assignment, 503 external references and 90 access grants**; governed trade-reference rows were also checked (zero present). New configuration audit/assignment rows are intentional. No existing financial values, BOOKED payloads or user permissions changed.

The normal API was restarted on **127.0.0.1:8000** using its existing non-owner runtime configuration; the existing frontend serves **localhost:3001**. Live read-only verification covers the tenant profile register/default, published rules, scoped usage and strategy context; no operating booking, configuration adoption, source edit or valuation was submitted. The duplicated embedded help widgets found during this pass were removed; the shared shell supplies the single top-page guide. The affected final frontend checks passed **24 tests**. Eight synthetic browser checks and the complete frontend regression above remain separately identified.


## Catalogue History follow-up — 4 November

A live History-tab click exposed a frontend race: changing tabs rendered the previous Entries result through the audit-row renderer before the loading effect ran, causing `action.replaceAll` to fail. Catalogue results now carry the exact tenant/source/tab/filter/page/reload key; a different query shows loading instead of interpreting stale rows. No audit data, permissions or API/database behavior changed. A delayed-response mounted browser regression failed with the original exception before the fix, then all four catalogue browser cases passed, including Entries → History → Used by → History → Entries.

## Lifecycle rule explanations — 4 November

Published and draft lifecycle sections now show a compact comparison of operator input, agreement-based inheritance and allocation-preserving closure. The active dropdown has an accessible description; Comment explains why it cannot allocate exposure. Published profiles explicitly say read-only and direct users to Create next version, review/publication and explicit strategy adoption. Drafts remain editable before publication. This changes explanatory presentation only: published immutability, current rules and strategy assignments are unchanged. Three focused browser journeys passed, including the choice explanations, Comment's two allowed options, mobile layout and publication without adoption.
