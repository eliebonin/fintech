# Market data — capability records

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Market-data engineering/operations  
**Last reviewed:** 2026-10-12

[Feature register](../feature-register.md). Storage, display rights, valuation-use rights, policy eligibility and financial acceptance are separate states. Counts below are dated activation evidence, not a new live-DB audit.

## F25 Public reference universe

- **Desired:** Known shared S&P 500/CAC 40 canonical instruments/listings, available to all entitled tenants.
- **Status / backend / frontend:** ALPHA. Dated manifest/operator seed with approval/source provenance and historical booking bounds; visible through normal catalogue/search.
- **Cuts/trade-offs:** October 6 snapshot: 503 S&P securities plus 40 CAC securities, 543 instruments/listings. Provider history estimates and specific primary regular-way bounds, not certified history for every identifier.
- **Weaknesses:** Not continuously current constituents, delisting/IPO history, historical ticker/venue continuity or index weights.
- **Remaining:** Govern membership updates, historical identity changes and source freshness; never blindly broaden booking validity beyond evidence.
- **Evidence:** [Universe seed](../../delivery/index-universe-seed-2026-10-06.md), [trading history](../../delivery/index-trading-history-and-yahoo-2026-10-08.md), [operator orchestration](../../../apps/market_data_ingestor/index_trading_history.py).

## F26 Ingestion boundary and operations

- **Desired:** Provider-neutral ingestion isolated from API request handling, with retries, provenance and operational recovery.
- **Status / backend / frontend:** ALPHA. `market_data` contracts/rights/publication, Yahoo adapters and operator entry points; durable jobs/attempts and partial/gap retries. UI inspects stored results, not acquisition orchestration.
- **Cuts/trade-offs:** Serial paced CLI with bounded backoff; no transaction held during HTTP waits. Operator policy/reference setup lives in `apps/market_data_ingestor`, not core/provider packages.
- **Weaknesses:** No scalable scheduled worker service, distributed leases, complete administrative recovery UI or production SLOs.
- **Remaining:** Scheduling, monitoring, safe stale-worker recovery and large-history performance. Keep source completion distinct from RAW normalization readiness.
- **Evidence:** [Boundary](../../delivery/market-data-ingestion-boundary.md), [hardening](../../delivery/md-ingestion-hardening.md), [CLI](../../../apps/market_data_ingestor/yahoo.py), [dependency regressions](../../../tests/test_market_data_boundaries.py).

## F27 Licensing and scoped rights

- **Desired:** Layered provider/content-owner permissions by display/non-display/purpose, scope, timing and tenant, including COMEX versus NYMEX.
- **Status / backend / frontend:** PARTIAL. Activity grants/prerequisites, dataset profiles, coverage packages/classification and scoped tenant grants enforced in selection/disclosure; source UI exposes safe scope summaries.
- **Cuts/trade-offs:** Provider → product → dataset → coverage package, not inventing a provider per exchange. Whole-dataset grants remain intentionally broader. Personal declarations/research exceptions are not commercial contracts/provider consent.
- **Weaknesses:** No complete coverage/licence management UI, quarterly evidence/entitlement recertification or commercial vendor reconciliation.
- **Remaining:** Reviewed commercial agreements and rights administration before hosted commercial use; decide provider-versus-client licensing from actual agreements, not a universal rule.
- **Evidence:** [Scoped rights](../../delivery/scoped-dataset-entitlements.md), [Yahoo permissions](../../delivery/yahoo-personal-valuation-permissions.md), [rights evaluator](../../../market_data/rights.py).

## F28 Provider catalogue and priority

- **Desired:** Inspect available provider scopes; platform defaults per instrument type, tenant reorder/exclusion and preference for validated tenant data.
- **Status / backend / frontend:** ALPHA. Versioned dataset orders with tenant/platform scope; `/market-data/sources` catalogue, ranking editor and inheritance.
- **Cuts/trade-offs:** The newest eligible market date wins first; dataset priority resolves competition on that date before observation/arrival timestamps. Explicit policy dataset pins remain binding. Omitted sources in CUSTOM are excluded, including a pinned source; empty CUSTOM excludes all. Tenant-owned suggestions are not active until saved. Ranking never grants legal access.
- **Weaknesses:** No general tenant upload workflow; ranking cannot fix missing observations, wrong semantics or missing rights. Unconfigured legacy arbitration remains explicit.
- **Remaining:** Validated tenant-source intake/default selection and entitlement administration. Preserve chosen rank/version in frozen evidence.
- **Evidence:** [Sources UI/rules](../../delivery/market-data-sources-ui.md), [ranking](../../../market_data/source_priority.py), [API catalogue](../../../apps/reference_api/market_data_sources.py).

## F29 Yahoo historical data

- **Desired:** First personal-project EoD equity/reference source and GBP conversion rates; no live-price requirement.
- **Status / backend / frontend:** ALPHA. Historical daily equity bars and FX pair series with original payloads, normalization and personal-purpose controls; explorer/coverage inspection.
- **Cuts/trade-offs:** Five-year equity history has known short/missing histories. FX EOD is not a timed fixing. UK/US research cuts use separate exact completed five-minute/hourly series; two-year hourly extension is partial, not fabricated complete coverage.
- **Weaknesses:** Provider precision/rate limits, missing bars and unproved issuer continuity. Yahoo samples are not official WMR benchmarks. Valuation-use activation is purpose/series/date scoped, not every stored price.
- **Remaining:** Repeatable ongoing refresh, reviewed calendars/gaps and real-price/financial acceptance; commercial source qualification before commercial use.
- **Evidence:** [Equity/backfill](../../delivery/yahoo-five-year-backfill.md), [FX history/retention](../../delivery/yahoo-gbp-fx-backfill.md), [bounded EURGBP activation](../../delivery/yahoo-eurgbp-valuation-setup-2026-10-09.md).

## F30 Price basis and RAW reconstruction

- **Desired:** Book as traded and use comparable as-traded marks; distinguish split-only from dividend/provider adjustment.
- **Status / backend / frontend:** ALPHA. RAW/split-adjusted/vendor-adjusted retain separate semantics, proof and immutable derived observations; policy AS_TRADED/conversion controls and original/used evidence in valuation.
- **Cuts/trade-offs:** One CLOSE family; official designation is separate metadata/requirement. Yahoo derived RAW explicitly reverses evidenced split factors, preserving source precision, reference date and payload lineage.
- **Weaknesses:** Derived RAW is not newly certified exchange official data. Completeness/source-method assumptions remain consequential; price conversion is not quantity replay.
- **Remaining:** Validate further providers' semantics and corrections independently; preserve complete anchored proof rather than relabelling adjusted values. Explorer chart/date/basis interaction needs current visual acceptance.
- **Evidence:** [Closing family](../../delivery/closing-price-consolidation.md), [RAW activation](../../delivery/yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09), [normalizer](../../../market_data/providers/yahoo/raw_prices.py).

## F31 Corporate actions

- **Desired:** Source corporate actions and adjust historical holdings during valuation without editing original trades; recognize distributions correctly.
- **Status / backend / frontend:** PARTIAL. Yahoo split/dividend import/provenance/quarantine, split price proof and conservative exposure safety guards. No complete review/replay UI.
- **Cuts/trade-offs:** Imported ANNOUNCED facts are not reviewed cash flows. An affected interval blocks rather than guessing transformations, even if raw quantities appear flat.
- **Weaknesses:** No automatic split quantity replay, merger/spin-off mappings, entitlement generation or complete dividend income engine.
- **Remaining:** Governed effective/recorded-date replay, transformed positions/cost bases and attributable distributions, with original trade facts retained. Keep price normalization and position transformation distinct.
- **Evidence:** [Safety guard](../../delivery/corporate-action-valuation-guard.md), [source actions](../../delivery/yahoo-market-data-alpha.md#corporate-action-import-and-evidence-assessment--2026-10-09), [reconstruction safeguards](../../../positions/reconstruction.py).

## F32 Pricing policies

- **Desired:** Strict explicit coverage or flexible EoD defaults with explicit exceptions, e.g. exchange closes plus London FX.
- **Status / backend / frontend:** ALPHA. Immutable versioned rules/defaults, precedence, calendars, freshness, source eligibility and preview; `/market-data/policies`, identifiable version choices and compatibility messages.
- **Cuts/trade-offs:** FLEXIBLE fills rule coverage only; a matched but missing/ineligible observation fails, not another fixing. SAME_DAY/zero stale sessions is distinct from explicitly allowed prior observations. Policy valuation context is not one global closing hour.
- **Weaknesses:** Complex configuration and source/calendar stewardship remain operational responsibilities. Unsupported economics are not rescued by a policy.
- **Remaining:** User acceptance and guided source/semantics configuration; retain original requested/used market dates and rule/version evidence. No hidden nearest/last tick substitution.
- **Evidence:** [Flexible/strict semantics](../../delivery/flexible-pricing-policies.md), [form clarity](../../delivery/pricing-policy-rule-form-2026-10-09.md), [selection](../../../market_data/policy_selection.py).

## F33 Calendars

- **Desired:** Exchange sessions/holidays and tenant-specific fund/strategy schedules, including joint Irish/UK/US holiday rules and dated exceptions.
- **Status / backend / frontend:** ALPHA. Published immutable schedules, ALL_OPEN/ANY_OPEN composition, evidence exceptions and recorded-time pinned assignments; calendar administration/inspection paths.
- **Cuts/trade-offs:** Valuation/dealing/settlement purposes differ. A known closed day differs from missing/UNKNOWN calendar coverage; latest current settings cannot reinterpret old runs.
- **Weaknesses:** Ongoing authoritative exchange/fund schedule ingestion and full historical coverage are not certified; administrators own exceptions.
- **Remaining:** Source/maintenance ownership, annual extensions and revised-calendar acceptance. Fund NAV economic date remains separate from T+1 publication availability.
- **Evidence:** [Calendar delivery](../../delivery/tenant-fund-and-strategy-calendars-alpha.md), [composition](../../../market_data/calendar_composition.py), [stored schedules](../../../market_data/calendar_store.py).

## F34 Inspection and validation

- **Desired:** Inspect price/reference series, source evidence, coverage and validate marks before valuation.
- **Status / backend / frontend:** PARTIAL. Stored series/history/provenance, eligibility diagnostics, coverage reconciliation and price-policy compatibility; `/market-data`, explorer, coverage and source/policy pages.
- **Cuts/trade-offs:** Missing inputs block calculation. Readable operational errors coexist with JSON; visible data is not automatically valuation-eligible.
- **Weaknesses:** No complete anomaly challenge, tolerance/override, independently reviewed price-validation state or provider comparison workflow. Chart date/basis refresh acceptance was interrupted, not proven fixed by this docs review.
- **Remaining:** Reproduce/sign off explorer interactions, define explicit pre-valuation validation workflow, exceptions and independent comparison; no silently fabricated marks.
- **Evidence:** [Workspace](../../delivery/market-data-workspace-2026-10-09.md), [compatibility UX](../../delivery/pricing-policy-clarity.md), [resolver](../../../security_master_schema/market_data_resolver.py).

## F35 Tenant time-series upload

- **Desired:** Tenants supply governed prices/NAVs as data providers, curate corrections and optionally prioritize validated series.
- **Status / backend / frontend:** FOUNDATION. Provider/tenant ownership, generic ingestion, provenance and rights model support the direction; no general self-service time-series upload API/UI is exposed.
- **Cuts/trade-offs:** Upload must retain original third-party provenance/licensing; ownership of a file does not establish legal content ownership. New/unvalidated values must not automatically replace market marks.
- **Weaknesses:** Intake templates, validation, duplicate/correction workflow, rights declaration and priority activation are missing as one operational journey.
- **Remaining:** Tenant-scoped intake API/UI, reviewed source identity and semantics, publication/correction evidence and configurable validated-source priority.
- **Evidence:** [Tenant-supplied boundary](../../delivery/scoped-dataset-entitlements.md#tenant-supplied-series), [generic ingest](../../../market_data/ingestion.py), [priority semantics](../../delivery/market-data-sources-ui.md).
