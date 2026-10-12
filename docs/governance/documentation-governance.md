# Documentation governance

**Status:** Accepted  
**Content type:** Reference  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-10-12

Canonical pages use this metadata block: `Status`, `Content type`, `Owner`, and `Last reviewed`.

- **Architecture** explains the current intended system boundary.
- **Decision** records one significant choice, alternatives, and consequences; superseded decisions remain readable.
- **Reference** records stable vocabulary, structures, or contracts.
- **Research**, **Specification**, **Plan**, and **Review** are evidence or time-bound records, not current architecture by themselves.

Update the canonical page first; then update a decision, plan, or review only when its own historical record changes. Every canonical page links to its principal historical sources. The archive is immutable and is never a destination for new authored content. New local Markdown links must resolve from the source file’s directory.

## Current capability maintenance

The [feature register](../product/feature-register.md) owns stable feature IDs and summary status. Its linked capability records own desired scope, backend/frontend evidence, deliberate cuts/trade-offs, weaknesses and remaining work. Update both when a capability changes; one successful test, a migration/table, module label or checked plan box is not end-to-end delivery.

Use the register's status vocabulary. State local activation, HTTP/component tests, browser walkthrough, financial reconciliation and production acceptance separately. Mark missing evidence **not verified**, not implicitly passed. New ideas must be identified as proposals/documented directions until the user prioritizes them.

Current architecture explains actual boundaries; detailed dated deliveries retain evidence. Add a current-status pointer when an old delivery is superseded rather than rewriting its earlier test results. Preserve accepted ADRs, original approvals, archives and compatibility paths. See the [documentation map](documentation-map.md) for precedence and [reconciliation decision](decisions/2026-10-12-capability-documentation.md) for the chosen organisation.

Research sources must be direct links with review date, applicability and a distinction between source-backed guidance and project choices. No file move should silently break an existing reference. Documentation-only changes use Markdown/link/status validation, not a full application regression run or operating-database writes.
