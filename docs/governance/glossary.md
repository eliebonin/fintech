# Glossary

**Status:** Draft  
**Content type:** Reference  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-09-10

| Term | Meaning |
| --- | --- |
| Canonical instrument | Economic financial contract, distinct from venue representations. |
| Financial-reference node | Common identity layer that supports instruments, listings, indices, currencies, and related reference objects. |
| Listing | A tradable venue representation of an economic instrument. |
| Provider mapping | Effective-dated mapping from an internal UUID to an external party’s identifier. |
| Dataset | Licensed, attributable grouping of provider-supplied data. |
| Valuation cut | Governed local-time/calendar rule resolving to a UTC cut-off. |
| Observation | Immutable market-data fact with source, publication/receipt timing, and provenance. |
| Valuation mark | Attributable valuation input, distinct from a raw observation. |
| Strategy | Portfolio/ledger container; a fund or AMC may be represented through it. |
| Tenant overlay | Tenant-local reference-data extension or override of the canonical plane. |
| Archive | Immutable evidence snapshot, not a current source of truth. |
