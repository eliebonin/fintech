# Market-data ingestion hardening

Status: implemented, locally activated and verified for the personal-project alpha on 7 October 2026. Not commercial deployment, authoritative calendar or issuer-history signoff.

## Changes and operational meaning

The existing provider-neutral ingestion boundary remains. The Yahoo CLI selects a serial runner; generic outcomes, operational evidence, historical reviews and read-only quality audit live in focused market_data modules. No scheduler, new service, frontend, live-data feed, valuation or P&L is introduced.

- Consistent delivery outcomes: COMPLETE, PARTIAL, FAILED, BLOCKED and ABORTED. Exit 0 is COMPLETE; exit 3 is PARTIAL; exit 1 is failure/access block/interruption; argument errors remain 2. Existing automation that assumed all nonzero codes meant no imported data must handle 3.
- Jobs and attempts persist separately from immutable source deliveries. An attempt is committed before download; publication and successful finalization share a transaction. A failed publication rolls back prices but can finalize its already-recorded attempt. Backoff events are persisted before the wait. Terminal evidence cannot be rewritten/deleted. Forced termination leaves RUNNING evidence, requiring explicit operator recovery after verifying the process stopped.
- Exact-window resume preserves partial status. --retry-gaps selects only dated missing-price rejections in the original window. After retries, a current-data assessment checks whether the original explicit missing points exist; the old report remains immutable. Failed identities, unsupported fields and omitted sessions are not automatically guessed/retried.
- Read-only --audit-only compares current accepted observations with versioned exchange schedules, separating missing internal/trailing sessions, unexpected dates, unavailable leading history, duplicate current dates and unreviewed historical continuity. Unknown calendars are NOT_ASSESSED. The package is not an authoritative market-calendar feed and leading history is not proof of listing inception.
- Historical mapping reviews require an active tenant MARKET_DATA administrator, inclusive dates, an APPROVED/REJECTED decision and evidence. Approved intervals cannot overlap. Explicit same-period superseding reviews preserve old evidence. Rejected intervals block new publication; old observations are not rewritten or retroactively removed. Audits surface rejected/unreviewed histories.
- Shared normalized-point guards enforce positive finite prices for this existing daily-equity PRICE flow, timezone-aware timestamps, inclusive date bounds and storage precision. Adjustment basis, source field and timestamp dimensions cannot silently change within an existing series. This is not a universal derivative-price contract; future adapters allowing negative prices need an explicit contract change.
- Current identity is series/dataset/market-date, not ticker alias/date. An approved alias change can produce a linked correction or duplicate, not two unrelated current prices for one series/date. Source keys remain recorded. The single legacy acquisition licence is selected deterministically; the full conjunctive rights proof is always the retained delivery's rights_evidence.

## Operator commands

```powershell
# Read-only full-universe audit: DISPLAY required, no Yahoo request or onboarding.
.venv/Scripts/python.exe -m apps.market_data_ingestor.yahoo --audit-only --declaration "Local research coverage audit" --start 2021-10-07 --through 2026-10-06 --limit 543

# Retry only explicit missing prices from that exact retained history request.
.venv/Scripts/python.exe -m apps.market_data_ingestor.yahoo --apply --acknowledge-personal-access --declaration "Owner-approved local research gap retry" --start 2021-10-07 --through 2026-10-06 --symbols FISV --limit 1 --retry-gaps

# Only after verifying the recorded process stopped; does not kill a process or publish prices.
.venv/Scripts/python.exe -m apps.market_data_ingestor.yahoo --apply --abort-job <JOB_UUID> --declaration "Operator verified process stopped; recovery evidence"
```

Historical-review operator API: market_data.history.review_history(connection, mapping_id, tenant_id, actor_id, start, end, decision, evidence, supersedes=None). Caller owns commit/rollback. No browser management page or automatic source-based approval is claimed. Do not use a current ticker match as historical continuity evidence.

The explicit --abort-job command returns 0 to acknowledge successful recovery, while the recorded job becomes ABORTED. This command acknowledgement is separate from the ingestion runner's outcome exit codes. COMPLETE means the selected delivery work succeeded, not that calendar coverage or issuer continuity has been certified.

## Best-practice evidence

Sources opened 7 October 2026; conclusions are alpha-specific applications, not mandatory deployment architecture.

| Source | Application and limitation |
| --- | --- |
| [OpenLineage run cycle, 1.53.0 documentation](https://openlineage.io/docs/spec/run-cycle/) | Persist lifecycle and terminal outcomes. PARTIAL/BLOCKED are local extensions; no OpenLineage integration/conformance claim. |
| [AWS Builders' Library: safe idempotent retries](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | Exact request identities, equivalent resume outcomes and targeted retry windows; no AWS service dependency. |
| [pandas-market-calendars documentation](https://pandas-market-calendars.readthedocs.io/en/stable/), [5.5.0 released 5 October 2026](https://pypi.org/project/pandas-market-calendars/) | Exchange-session comparison rather than weekday counts; record installed version and do not claim live/authoritative schedules. |
| [PostgreSQL 18 locking](https://www.postgresql.org/docs/18/explicit-locking.html) | Short operational/publication transactions, never locks across HTTP/backoff; dataset serialization retained for correctness. |

## Verification and remaining limits

Expanded focused verification passed 122 tests in 70.13 seconds. The additional real-CLI database-driver failure test and operator regressions passed 4 tests in 48.20 seconds: publication rolled back all prices, while the pre-recorded attempt finalized FAILED with a safe error category and no delivery link. Final full Python verification passed **1,073 tests, zero failures**, with 488 warnings, in 797.71 seconds (13:17), against a fresh disposable database. Evidence: logs/md-hardening-full-python-final.log.

The first full run completed with 1,071 passed and one failure: the mandatory descriptions for the 30 new columns were missing. Descriptions were added to model metadata and the database through migration 65, preserving the applied migration 64. The schema/migration/operator follow-up passed 34 tests in 49.29 seconds, including a new database/model description parity check; the final whole-suite result above verifies the completed fix. Warning debt remains, including SQLAlchemy deprecations and Pydantic field-attribute warnings elsewhere in the suite; no warning-free claim is made.

Migrations 20261007_64 (operational tables) and 20261007_65 (column descriptions) are applied to the local personal-project database. Migration 64 was preserved after activation; the later documentation correction is additive. Read-only reconciliation of 543 listings / 1,086 series for 2021-10-07 through 2026-10-06 found:

| Finding | Series | Listings / meaning |
| --- | ---: | --- |
| MATCHES_CALENDAR | 1,056 | 528 listings, matching the versioned comparison schedules |
| SHORT_HISTORY | 26 | 13 listings, unavailable leading sessions kept separate from internal gaps |
| GAPS | 2 | FISV CLOSE and ADJUSTED_CLOSE both missing 2025-11-12 |
| NOT_ASSESSED | 2 | CBOE / BATS; no supported calendar substituted or completeness certified |

All 1,086 series retain REVIEW_REQUIRED historical continuity. No ambiguous current dates or unexpected dates were found. This is calendar comparison evidence, not issuer-history or exchange-calendar certification. Detailed results are retained in logs/md-hardening-universe-audit.json; no network acquisition was performed.

Operating counts remain unchanged: 9 trades, 9 trade lifecycle events, 50 strategies, no cash accounts/balances, 1,358,477 total observations and 1,346,008 Yahoo observations. Existing prices and financial records were not edited by this delivery.

Permission checks still allow PERSONAL ACQUIRE/STORE/DISPLAY and deny NON_DISPLAY, REDISTRIBUTE and COMMERCIAL ACQUIRE. Compilation, dependency consistency, hashed-lock dry-run and whitespace checks passed. No dependency upgrade outside the calendar's required transitive additions was requested.

Sequential author review checked the implementation against the acceptance criteria, focusing on exact request-to-delivery lineage, revoked rights on resume, transaction rollback, append-only review correction, terminal immutability and current-date identity. This is not independent reviewer sign-off. The operator test harness uses savepoints so its CLI commits cannot leak synthetic permission changes into other tests; production transaction boundaries remain real commits.

Deliberate limits: dataset publication is still serialized; jobs are visible through emitted IDs and retained SQL evidence, not a new frontend dashboard. Forced termination or loss of the database during finalization can leave RUNNING evidence for explicit recovery. Historical issuer/ticker continuity requires real evidence, and BATS coverage needs a supported calendar before certification can be considered. These are surfaced limits, not silently claimed fixes.

The new operational ledger records new executions. Existing backfill delivery evidence is retained as originally recorded, not retroactively converted into invented jobs or attempt timestamps.

No historical review evidence has been fabricated. Existing source gaps and shorter histories remain as data-quality findings, not repaired prices. Raw payload storage remains in PostgreSQL with the existing 4 MiB per-delivery limit; archive/retention tiering and concurrent-worker scaling are future operational work, not requirements for this alpha batch.

See [design](../superpowers/specs/2026-10-07-md-ingestion-hardening.md), [plan/ledger](../superpowers/plans/2026-10-07-md-ingestion-hardening.md), and [original backfill results](yahoo-five-year-backfill.md).
