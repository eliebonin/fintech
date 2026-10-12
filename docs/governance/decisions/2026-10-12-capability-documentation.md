# Decision: capability-led documentation retrieval

**Status:** Accepted under user-authorized documentation reorganisation  
**Content type:** Decision  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-12

## Context

Current indexes lag delivery; chronological plans retain outdated pending/single-currency descriptions, and module/table names can look like completed products. The user wants an extensible desired-versus-implemented list with Markdown links, statuses and cuts/trade-offs/weaknesses/remaining work, without another layout approval.

## Decision

Add one [feature register](../../product/feature-register.md) with stable IDs and grouped focused records. Current architecture/reference explains boundaries; specs/plans/progress remain linked dated evidence, not competing backlogs. Repair drift and add supersession pointers while preserving existing paths and the immutable archive.

## Alternatives and consequences

- Mass rewriting/moving historical files risks broken links/lost evidence without improving status retrieval.
- Another chronological report does not answer the next reader's desired/current/gap lookup.
- Inferring status from tables, route presence or plan boxes cannot establish support limits or user deferrals.

Manual evidence-based curation adds a small upkeep cost: update register and record together after changes. New ideas receive stable IDs and an origin/scope qualifier, not automatic approval. Existing paths/evidence stay recoverable. This extends the September information architecture, not a reason to rewrite accepted ADRs. No product change, migration, deployment or GitHub write is implied.

## Sources

[Diátaxis](https://diataxis.fr/start-here/), [arc42 decisions](https://docs.arc42.org/section-9/) and [risks/debt](https://docs.arc42.org/section-11/), opened 2026-10-12. The chosen register/layout is our application of the guidance.
