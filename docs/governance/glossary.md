# Glossary

**Status:** Maintained reference
**Content type:** Reference  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-10-12

| Term | Meaning |
| --- | --- |
| Canonical instrument | Economic financial contract, distinct from venue representations. |
| Financial-reference node | Common identity layer that supports instruments, listings, indices, currencies, and related reference objects. |
| Listing | A tradable venue representation of an economic instrument. |
| Provider mapping | Effective-dated mapping from an internal UUID to an external party’s identifier. |
| Dataset | Licensed, attributable grouping of provider-supplied data. |
| Valuation cut / policy context | Governed context identifier required by the policy/request. A rule's session, fixing or explicit pricing cut determines observation timing; the context is not necessarily one universal closing hour. |
| Observation | Immutable market-data fact with source, publication/receipt timing, and provenance. |
| Valuation mark | Attributable valuation input, distinct from a raw observation. |
| Strategy | Portfolio/ledger container; a fund or AMC may be represented through it. |
| Tenant overlay | Tenant-local reference-data extension or override of the canonical plane. |
| Archive | Immutable evidence snapshot, not a current source of truth. |
| Tenant | Service customer/workspace owning strategies, users/groups, private data and configuration; logically scoped in the current shared-database alpha. |
| Real actor / selected subject | Actual operator versus effective tenant user selected for local testing. Independent review checks the real actor. |
| Module entitlement | Effective tenant grant enabling a product capability; does not grant user actions or market-data licences by itself. |
| Action grant | Group-conferred operation permission, effective only with active membership and the corresponding tenant module. |
| Coverage package | Reviewed content-owner/market/timing scope within a dataset, such as COMEX versus NYMEX; not a separate delivery provider. |
| Source priority | Versioned order of eligible datasets. It cannot override rights, price semantics, market date, fixing or freshness. |
| STRICT / FLEXIBLE | Explicit rules only versus explicit rules then configured defaults when no explicit rule matches. Matched missing data still blocks. |
| CLOSE / official designation | Closing-price family versus metadata declaring the closing method/official requirement. Legacy OFFICIAL_CLOSE remains historical compatibility vocabulary. |
| RAW / AS_TRADED | Observation basis versus economic requirement that price units match booked units. Derived RAW retains source/conversion proof, not just a relabelled number. |
| SPLIT_ADJUSTED | Historical prices expressed on an evidenced split-adjustment reference basis; not necessarily original traded share units. |
| VENDOR_ADJUSTED | Provider-adjusted stream that can incorporate dividends/other transformations; not automatically eligible for holdings valuation. |
| Economic / information date | Date to which a fact belongs versus cutoff for knowledge/publication/receipt available to the calculation. Fund NAV for T can be published T+1. |
| Effective valuation date | Built-in optional trade recognition date, defaulting to execution UTC date; distinct from settlement date. |
| Record correction / contractual event | Cancel/replace an erroneous booking versus actual delivery, exercise, redemption or reset. Neither is automatically an opposite execution. |
| Daily accrual / accrued balance | Interest earned during the day versus accumulated receivable. Only daily earnings enter daily ACCRUAL P&L. |
| Staged / published | Immutable review candidate versus independently approved official selection. Amendments replace versions rather than editing historical results. |
| ALPHA capability | A bounded working path, not commercial rights, complete product economics, latest visual acceptance or production readiness. |
