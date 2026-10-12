# Scoped market-data entitlements

Date: 2026-10-08. Scope: persisted coverage model and consumer enforcement; not a completed licensing administration UI or pricing-priority engine.

## Delivered

- Keep one provider identity for an organisation such as CME Group; COMEX and NYMEX are coverage packages, not cloned providers.
- `md.dataset_coverage_package` records the dataset, package code/label, original content-owner provider, optional reviewed licensing market, timing (real-time, delayed, EoD, historical), effective dates, status and evidence reference.
- `md.market_data_series_coverage` explicitly classifies each actual dataset/series pair into a package. A series may be supplied by multiple datasets; each supplier has its own classification. Package codes can represent narrower product/field bundles where agreements require them.
- `ten.tenant_dataset_entitlement.coverage_mode` distinguishes existing whole-dataset grants (`DATASET`) from package-limited grants (`SCOPED`). `ten.tenant_dataset_coverage` associates the permitted packages with the effective-dated tenant/purpose grant.
- Composite foreign keys reject package grants and classifications belonging to another dataset.
- The shared eligibility predicate gates candidate selection, catalogue pages/counts/observations, instrument-detail observations and retained snapshot/valuation evidence. Missing classification/context cannot satisfy a scoped grant. Existing conjunctive activity-right checks remain in force; this is not legal clearance.
- `md.data_provider.owner_tenant_id` supports tenant-private source identities. Consumer eligibility prevents another tenant borrowing that source even if an erroneous dataset entitlement is added.
- Migration 73 is additive. Existing grants retain their prior dataset-wide meaning; it creates no COMEX/NYMEX permissions or operating packages. Downgrade refuses to discard scope restrictions/evidence.

## Configuration procedure

Platform data/licensing operations must review this configuration; a tenant's source-preference setting must never manufacture a coverage grant.

1. Catalogue the distributor/product/dataset separately from the original content owner.
2. Create reviewed packages with explicit coverage, timing and evidence. A licensing market is not necessarily the delivery venue/channel; never infer COMEX versus NYMEX from Globex.
3. Classify the dataset's series into their actual packages, using governed source/reference mappings or a reviewed bulk configuration, not per-trade configuration.
4. Create or amend the tenant/purpose entitlement to `SCOPED` and associate only the authorised packages. Ensure no overlapping active whole-dataset grant remains when the intended permission is package-only; a whole-dataset grant is intentionally broader.
5. Confirm required provider/owner activity grants and prerequisites independently. Source priority is applied only after eligibility and price-semantics checks.

No production licensing provider or tenant may use synthetic test evidence as proof of commercial rights.

## Tenant-supplied series

A tenant can act as a data supplier in the model: use a tenant-owned provider identity, its datasets, and the same provenance, permissions and series semantics. Uploading third-party prices does not remove their original licensing obligations or make the tenant their legal content owner.

The API code inspected for this delivery does **not** expose a general tenant market-time-series upload endpoint. Acquisition currently uses governed ingestion paths, including Yahoo. Therefore this delivery does not claim a working generic upload UI/API.

For the forthcoming source-priority implementation, a tenant's **designated validated dataset/series** should default to first priority for that tenant. A newly uploaded/unvalidated record must not automatically replace a price. Tenants should be able to reorder or disable this preference. Preserve original provider provenance, and freeze the chosen observations for each valuation run.

## Deferred

- Platform default and tenant source-priority lists, including tenant-supplied defaults.
- Strict/flexible policy mode and comprehensive pre-valuation price-validation workflow.
- Coverage/licensing management UI and package labels in source pickers.
- General tenant upload UI/API, corrections, validation and intake audit flow.
- Quarterly entitlement review workflow, provider reconciliation and contract-specific reporting automation.
- Connecting real commercial CME/Bloomberg feeds and reviewing their current agreements.

## Verification

The catalogue regression first reproduced two visible series under a one-package grant. Focused tests cover permitted/forbidden/unclassified series, tenant isolation, suspended/future/expired packages, inclusive boundaries, whole-dataset compatibility, wrong-dataset foreign keys, actual resolver filtering, evidence disclosure and migration round-trip/downgrade safety. Tests run against disposable PostgreSQL databases and an in-memory SQL predicate fixture, never operating trade data. The full suite is intentionally not run.

Final verification: **79 focused tests passed** using the disposable database wrapper. The run included dataset coverage, SQL eligibility, layered rights, market-data display, resolver selection, valuation evidence/follow-up and resolution snapshot repository tests. There were 16 existing SQLAlchemy seed-loader deprecation warnings; no failures. Python compilation and scoped `git diff --check` passed. No full suite was run.

Migration **20261008_73 is applied** to the local app database; Alembic reports it as head. No operating coverage packages, tenant-private providers or scoped permissions were created. This delivery does not include an application restart, browser acceptance or UI changes.

Review was performed sequentially by the implementing agent, as requested, not by an independent subagent. The review retained explicit classification, current disclosure checks, cross-dataset foreign keys and guarded downgrade. A proposed temporary removal of resolver safeguards for an additional mutation check was rejected by the safety reviewer and was not performed; the original catalogue red-to-green regression and final resolver assertions provide the verification evidence.

## Best-practice evidence

- [CME entitlement systems](https://www.cmegroup.com/market-data/distributor/files/data-licensing-policy-guidelines-entitlement-systems.pdf), reviewed 2026-10-08: explicitly distinguishes designated contract markets (CME, CBOT, COMEX, NYMEX), further content limitations, timing and usage. This 2021 educational guidance informs the model; the current executed agreement determines actual obligations.
- [CME licensing options](https://www.cmegroup.com/market-data/license-data.html), reviewed 2026-10-08: internal display, non-display, distribution and derived-data are distinct arrangements. Neither a client's subscription nor our internal-use licence automatically covers hosted client services.
- [ESMA valuation review, section 6](https://www.esma.europa.eu/sites/default/files/2023-05/ESMA34-45-1802_2022_CSA_on_Asset_Valuation_-_Final_Report.pdf), reviewed 2026-10-08: justify/document source selection and independently challenge external marks. Tenant-source preference is our design decision, not a prescribed ranking or permission to bypass validation. Regulated-fund requirements are not asserted as requirements for this personal research project.
