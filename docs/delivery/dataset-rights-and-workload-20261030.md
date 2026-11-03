# Dataset rights and workload admission — 30 October 2026

**Status:** Implemented; local governance activated  
**Plan:** [Sequential implementation](../superpowers/plans/2026-10-30-rights-and-workload.md)  
**Maintained reference:** [Behaviour, configuration and limits](../platform/dataset-rights-and-workload.md)

## Delivered

Finding 5: missing/unknown dataset profiles now deny activity and display use.
Reporting purpose is enforced consistently in direct evidence release and
catalogue SQL. Existing date, private-parent, activity-layer and series/package
checks remain. Migration 106 introduces explicit SYNTHETIC origin evidence for
invented fixtures, without converting personal evidence into commercial rights.

Finding 7: configurable nonblocking local/global/tenant admission protects
calculation, preview, import and regulatory preparation/export paths. Shared
PostgreSQL slots work across workers; a separate bounded coordination pool keeps
the financial pool available. Retryable busy responses precede domain effects,
retain request identity and distinguish rejection from uncertain timeouts. The
frontend forwards Retry-After and requires explicit user retries. Ordinary run
status/log reads remain available.

This is admission hardening, not delivery of a new durable worker platform or
per-job OS memory/CPU limits. SEC-WORK-001 remains partially open for deployment.
No financial formulas, complete trade populations or published figures changed.

## Local activation

Applied migration **20261030_106** and explicitly provisioned the five exact
invented seed datasets. **Zero datasets lack profiles** afterward. All **seven
pre-existing profiles and 32 original grants** were compared field-for-field and
remain unchanged. Operating counts remain **162 trades / 3 tenants**. The action
is audited; there was no operating booking, cancellation, balance upload or
valuation/publication. No app server was started as part of the backfill.

## Evidence and scope

- RED probes reproduced missing-profile and reporting-purpose bypasses, missing
  admission, dropped Retry-After and alternative UUID path bypasses before fixes.
- Strict-profile/display integration: 12 passed; governance/admission API/unit
  selection: 28 passed. Authenticated busy/unavailable submissions create no
  attempt row and leave status reads available.
- Final numerical/publication and concurrency selection: 9 passed. Original
  P&L **109.877** and reviewed amendment **99.877** remain exact; unchanged-key
  retries do not duplicate runs, independent publication stays enforced and
  revoked DISPLAY rights hide retained financial evidence.
- Cross-worker capacity, tenant isolation, pooled-lock reuse, actual worker exit,
  body-send/error/cancellation cleanup and one-connection financial-pool cases
  pass. A correctly timed additional cancellation check confirms capacity remains
  held while the physical synchronous worker runs; no extra audit-wrapper hook
  was needed.
- Complete frontend: **1,088 tests / 224 files passed**. Focused UI/BFF selection:
  29 passed; frontend/API-contract types and OpenAPI consistency pass. Browser
  acceptance passed: explicit busy message, no automatic retry and exact body/key
  retained on manual retry, using isolated fixtures and installed Chrome.
- A broader Python selection passed 40 cases and exposed three stale fixture
  expectations: obsolete legacy-purpose handling and earlier typed cash/source
  proof additions. The fixture assertions were reconciled without removing
  financial/disclosure checks; all three pass on focused rerun. Final admission/
  strict-governance selection: **15 passed**, including noncanonical UUID paths.
- The optimized build passes. Coordination acquisition commits before domain
  work, retaining session locks without an idle transaction. Final code/document
  consistency/link/whitespace checks pass. Gitleaks detects its synthetic sentinel
  and finds no leaks in the ~17 MB publishable working tree. The non-owner runtime
  login passes the same shared admission check against the operating DB without
  financial writes. Pool initialization is serialized per controller and idle
  connections are disposed at app/fixture shutdown.
- A final five-case offline selection covers simultaneous first-use pool
  ownership and correctly timed cancellation. Type generation is checked against
  working-tree bytes: the repository's Git-diff freshness command reports the
  intentional uncommitted generated-contract changes, rather than a stale output.

No full Python suite, representative capacity certification, external data-rights
audit or production deployment is claimed. No commit/push was requested. Temporary
browser/build servers do not change the operating app's financial data.
