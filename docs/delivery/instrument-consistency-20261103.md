# Instrument consistency — 3 November 2026

## Authorized sequence

Creation cleanup → non-ledger source reassessment → bond monetary-preview accrued balances. [Implementation plan](../superpowers/plans/2026-11-03-instrument-consistency.md).

## Creation cleanup

Equity creation starts with an explicitly unresolved issuer. A debounced organisation search supplies active shared catalogue options; selection is retained across searches. No demo issuer or source identifier is inserted by default. This reuses the organisation directory without inventing issuer-role curation or granting trading-configuration authority.

Automated creation choices come from active shared/tenant-owned sources, effective equity-create policies and date-valid instrument namespaces. Tenant policy precedence matches the native writer. Listing-only namespaces are intentionally absent from canonical instrument creation; they belong to listing workflows. No eligible configuration leaves manual review available. Submission revalidates native permissions and policy; the automated writer additionally rejects another tenant's private source.

The futures creation picker now describes the implemented dated index/crypto scope. Other creation pages were searched for equivalent embedded demo identifiers; the identified constants were confined to the equity screen. This is not a browser/financial sign-off of every product form.

Creation verification covers source privacy, effective configuration, direct native HTTP authority, payload choices and BFF identity/date handling. Final counts and live findings are recorded below. No operating instruments, grants or source configuration were changed.

## Non-ledger source reassessment

New calculations retain versioned `sourceDependencies` beside the existing ledger, cash and accrued-stock evidence. SHA-256 fingerprints cover the scoped accepted market observations and their vintages, actual series metadata/dimensions, the selected policy/rules/cuts and source priorities, pinned calendar data and relevant valuation assignments/venues, and visible quantity-changing corporate-action/replay-decision chains.

Market windows follow the requested/used pricing dates, including fund NAV lag and explicit freshness allowances. A later economic-date NAV is not automatically an input to an earlier requested price date. Corrections that move outside the original window remain relevant through their predecessor linkage. Another tenant's unentitled observations are excluded. A new independent policy version does not silently replace the selected version; changes to the chosen version's effective configuration are tracked.

Detail, batched history status and the reassessment worklist share this comparison. Worklist filtering/counts happen in SQL before pagination. Source changes block stale staged publication; published financial amounts and original evidence stay frozen. The UI identifies market/FX, policy/priority, calendar or corporate-action changes in readable terms. Recalculation creates an explicitly reviewed successor and does not automatically reapply attribution amendments.

The tracker compares relevant candidate populations, not only the winning mark. A changed candidate or policy can therefore require reassessment even when recalculation ultimately gives the same amount. CURRENT is bounded source consistency, not external financial reconciliation or an assertion that all possible income is booked. Complex corporate actions remain unsupported by the existing replay engine. Publishing a new calendar/policy version alone does not reassign a pinned choice. General reference amendments, commercial entitlement recertification and deployment-scale certification remain separate.

Earlier batches without this new dependency proof remain readable with UNKNOWN_LEGACY source status; their values are not backfilled or rewritten. A fresh calculation supplies the proof needed for subsequent publication.

Eligible series and observation roots are reused inside the SQL statement. Focused profiling also established PostgreSQL JIT setup overhead (one synthetic probe: 0.5902 s on versus 0.1706 s off with identical fingerprints). Scoped metadata aggregates temporarily disable JIT and restore the caller setting; normal financial queries retain their configuration. Rollback/failure paths are tested. These fixture timings are not a production capacity benchmark.

Publication additionally reuses existing NON_DISPLAY rights evaluation for selected datasets. Historical/current tenant valuation eligibility participates in the market dependency fingerprint. These controls neither grant source rights nor bypass existing DISPLAY checks.

## Bond monetary-preview accrued stocks

Source DIRTY prices retain precedence. With a CLEAN price, the preview reads the exact-date maintained accrued-balance history and verifies the build's original source signature. It no longer treats a rich daily-interest payload as the published closing stock; such an input must first go through explicit balance maintenance.

The bond's local market value is clean nominal value plus its signed maintained closing stock, translated through the existing governed reporting FX. Reference notional/exposure stay available independently. Missing, unassessed, stale or currency-incompatible stocks make that market-value measure unavailable; they do not become zero or fail unrelated measures. The preview never rebuilds a balance. An instrument-level stock is not implicitly allocated or duplicated across multiple listing/currency positions.

Explicitly frozen ZERO coupon terms permit zero coupon-accrual when no stock was supplied; an explicit maintained zero is also distinguished from missing. No daily earned amount is substituted for the accumulated stock. Public preview evidence retains scoped history/build IDs, exact amount/date/nominal and source-proof hash; it does not copy other bonds' source catalogues or nested market-data values into the selected position's response.

## Verification and activation

Verification completed:

- 191 focused Python tests across creation, source reassessment, ledger publication, bond measures and the affected product/P&L integrations passed in an owned disposable database. The full Python suite was not run.
- The frontend regression passed: 1,151 tests in 242 files. After live review, 17 focused client/model/BFF checks also passed, including two added regressions for direct client transport and nullable issuer labels.
- A final 24-test disposable-database run passed for the new HTTP endpoint, equity onboarding, access API, boundary execution and reference API contracts.
- Frontend and API-contract TypeScript passed; the three API-contract tests, OpenAPI parity check, Python syntax scan (838 files) and working-tree secret scan passed.
- Read-only live creation review found and resolved stale development exports by restarting the frontend, and exposed an omitted exact API permission mapping. The new endpoint is explicitly REFERENCE_PROPOSE for reads; unknown paths and mutations remain denied. Native HTTP/access checks verify this path. Live reads then returned 200; the page showed the truthful manual-only configuration hint, issuer search omitted null labels, and the selected issuer survived a different search. No instrument proposal was submitted.

API port 8000 (healthy after restart at 15:53 UTC) and frontend port 3001 were restarted for activation. The API restart was preceded by a check showing zero running valuation attempts. This is bounded implementation/acceptance evidence, not financial reconciliation of a newly calculated operating run. No migration is needed: existing immutable batch summary and accrued-history tables hold the new evidence. No operating trades, grants, source data, balances or published valuations are changed by this delivery.
