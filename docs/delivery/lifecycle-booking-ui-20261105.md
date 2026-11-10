# Lifecycle search and maturity-workspace presentation

5 November 2026. Scope: lifecycle worklist instrument filtering and existing bond/FX-forward maturity workspace presentation.

## Design

Instrument search accepts a name, stored identifier or canonical UUID. The scoped repository filters candidates before reconstruction, counts and pagination. Search text is retained in the applied URL and uses the existing Apply filters action; it does not search only the visible page or broaden authority. Literal SQL wildcard characters are escaped.

The booking workspace separates selection, processing controls, closing inputs, prepared entries and posting/correction history into distinct cards. Context is preselected from the worklist link. A readable summary precedes allocation fields; source evidence remains expandable. Tier entitlement and the independent-review/direct policy remain separate and visible. After a processing-control change, the console reloads current assistance decisions before displaying booking actions; a failed refresh keeps actions unavailable and identifies the already-saved change. Existing handlers, permissions, fingerprints, confirmations, idempotent retries and correction controls are retained. No migration or operating financial command is required for this presentation change.

## Research

Read on 5 November 2026: [Scottish Government search filters](https://designsystem.gov.scot/patterns/search-results/search-filters) supports labelled filters and an explicit apply action for narrowing a result set. [GOV.UK summary lists](https://design-system.service.gov.uk/components/summary-list/) supports semantic key/value summaries; [details](https://design-system.service.gov.uk/components/details/) supports progressive disclosure of secondary detail; [buttons](https://design-system.service.gov.uk/components/button/) supports descriptive action labels and a clear primary action. The card grouping and exact workflow arrangement are project design choices.

## Verification

- Disposable database: **24 worklist/API tests passed**, including name/identifier/UUID search, literal wildcard escaping, listing identifiers, full counts before pagination and existing tenant/strategy boundaries. The new search test first failed because the query parameter was unsupported; a missing synthetic identifier fixture was then supplied explicitly.
- Frontend/BFF: **12 focused tests passed**; TypeScript passed; OpenAPI was exported and generated types refreshed, with exporter check passing.
- Mounted browser: **8 tests passed**, covering search beyond the initial page, filtering/pagination, context preselection without automatic booking, desktop/mobile layout, populated posting HTML, mode refresh, assistance and allocation regressions. A separate regression reproduced stale action availability after a saved mode change, then passed after current assistance was reloaded. No full Python/frontend suite was required for this scoped change.
- Own browser: linked FCPGF/bond context loaded; preview showed the existing 500,000 nominal, sourced redemption price 100 and required allocation fields. Search for ISIN GB00BSGQN319 returned one overdue event. Preview/navigation did not prepare or book a trade or change operating settings.
- Local API on port8000 restarted successfully (`/health` returned ok); existing frontend3001 remains running. No migration, permission, subscription or financial data change.
