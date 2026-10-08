# Valuation follow-up hardening — 7 October 2026

## Scope and changes

Corporate-action safety is unchanged. This work addresses the remaining findings
from the market-data/valuation review, without introducing settlement, accounting,
automatic position transformations or broader product valuation.

### Timestamp semantics

Both stored `SOURCE_DAILY_BAR` and Yahoo's `PROVIDER_DAILY_BAR_TIMESTAMP` designate
day buckets. They are excluded from EXPLICIT_TIME and NAMED_FIXING selection;
session-close selection remains permitted subject to completion/availability checks.
No historical observation or series dimension is rewritten. Missing timestamp
dimensions still retain legacy selection behaviour; complete governed instant
semantics across all vendors remain an onboarding requirement.

### Calendar history

Reference calendar creation, session recording and holiday recording times now
respect the information cutoff. Post-cutoff reference data cannot be borrowed
from a generated fallback schedule. Frozen evidence includes recording times,
calendar version and sealed status.

Valuation requires a **sealed reference version**, not an editable platform
schedule. Existing database triggers already prohibit parent and child edits,
deletion and additions once sealed. A platform administrator can publish a new
copy of explicit dated reference data, retaining source calendar and publication
reason; the source and existing policies/venue defaults remain unchanged.

Publication records NOW, not a fictional historical publication. To use it,
explicitly create/assign a policy pinned to the resulting UUID and choose an
information cutoff at or after publication. Calendar dates in the past do not
mean the system possessed that calendar in the past. No operating reference
calendar or policy was silently modified by this implementation.

Local administrator operation (select the correct DATABASE_URL first):

```powershell
.venv/Scripts/python.exe scripts/valuation_operations.py publish-reference-calendar --calendar <source-uuid> --actor <platform-admin-uuid> --reason "Reviewed exchange session schedule"
```

Mutable legacy reference calendars remain inspectable for reference/market-data
exploration, but cannot underpin a valuation. Their pre-existing edit history
cannot be reconstructed. Published tenant fund calendars retain their separate
versioned configuration and assignments.

### Evidence permissions

Every valuation detail/create response checks current dataset DISPLAY permission
and current effective tenant entitlement. Profiled sources require
INTERNAL_REPORTING entitlement; unprofiled legacy fixtures retain the same
entitlement convention as existing market-data display. Suspended/inactive or
expired datasets are denied. NON_DISPLAY calculation permission is not DISPLAY.

When display is denied, attempt status and safe operational events remain visible,
but batch items, source inputs, components and monetary totals are withheld. The
batch summary explicitly reports `evidenceAccess: DENIED`. No retained financial
evidence is rewritten. Review/explanation and publication are forbidden before
any mutation when required inputs cannot be inspected.

The UI explains this restriction and hides blank totals and review/publication
forms, while retaining the safe run status and operational log.

The alternate market-data-resolution snapshot read/retry/create and policy preview paths receive
the same current display checks and returns 403 rather than disclosing prices.
This conservatively withholds derived totals together with restricted inputs;
it does not claim that contracts universally require this treatment.

### Opening marks

Opening prices are required only for holdings present at the opening cutoff.
New period executions use their immutable execution price and explicit execution
FX as their opening economic basis, requiring only a closing market mark. No
empty opening resolution snapshot or invented opening price is persisted.
Existing holdings still fail closed if their opening mark is missing. Signed
sales and zero-net round trips retain the exact trading bridge.

Attribution version identity now includes source dataset/licence and frozen
pricing/calendar context. A different calendar version cannot reuse an
attribution carrying older reference evidence just because the price is equal.
Changing only the information-query time does not manufacture a new version.

### Operational safety

Financial calculation/staging uses REPEATABLE READ: all economic and market-data
queries share one database snapshot. Independent STARTED/FAILED diagnostics remain
durable outside the financial transaction. Existing idempotency and publication
guards are preserved.

Serialization conflicts retry at most three financial transactions using the
same attempt and key; only PostgreSQL SQLSTATE 40001 is retried. Other failures
are retained normally. Concurrent identical requests must converge on the same
completed attempt and financial batch, not manufacture duplicate results. A
duplicate while its worker owns the attempt lock returns 409
`valuation.in_progress` immediately. Inspect the retained attempt or retry the
UNCHANGED request with the SAME key after the worker completes. A duplicate
caller must not mark that worker's RUNNING attempt failed.

Lifecycle histories are loaded with one joined query; identical frozen
instrument conventions are cached within the run. The 1,002-lot regression
formerly issued 2,005 SELECTs in this loading step; its acceptance limit is now
four, with no new population cap or oversized IN-parameter list.

A stopped worker's stale RUNNING attempt can be recovered by an authorised
tenant valuation administrator. Minimum age: 15 minutes. Recovery requires an
explicit stopped-worker confirmation and explanation, refuses an active worker
advisory lock, and refuses any attempt already associated with a financial batch.
It retains FAILED/INTERRUPTED and an audit event with actor and reason. It does
not kill workers or cancel financial results. The operator must verify that the
worker has stopped, including a worker waiting to acquire its lock.

```powershell
.venv/Scripts/python.exe scripts/valuation_operations.py recover-attempt --tenant <uuid> --attempt <uuid> --actor <tenant-admin-uuid> --confirm-worker-stopped --reason "Worker stopped; no committed result; operational checks completed"
```

Retry the corrected calculation using a NEW idempotency key. Recovery is an
explicit local operational command, not an automatically triggered watchdog.

## Remaining scaling work

Background workers, position checkpoints, bulk market-data resolution and
paginated evidence remain separate work. Removing the arbitrary population cap
does not make synchronous requests or all evidence loads unboundedly scalable.
API transaction/request time budgets remain enabled; no full-suite run is
required for each individual edit.

## Verification

- 50 lightweight checks passed (Decimal economics, replay, corporate-action safety,
  timestamp semantics, source-evidence identity and denied evidence).
- 52 grouped disposable-database/API checks passed, 8 existing seeding deprecation
  warnings, 93.59 seconds. Includes simultaneous identical HTTP requests, later
  same-key result reuse, revocation/redaction, blocked review, snapshot denial,
  immutable calendar publication, late calendar records, stable concurrent input
  reads, stale recovery and active-worker protection. Runner exit 0; its owned
  test databases were removed. See `logs/valuation-follow-up-signoff.log`.
- The final strengthened Yahoo resolver control also passed: the same observation
  is selected before the daily-bar dimension is attached and rejected afterward
  (`logs/valuation-yahoo-timestamp-control.log`, 1 passed, 23.54 seconds, exit 0).
- A broader calendar/market-data run passed 94 checks but failed concurrency before
  the final fix. That specific failure is fixed and passed in signoff; the earlier
  run is NOT claimed as entirely green (`logs/valuation-follow-up-final.log`).
- Nine focused frontend checks passed across valuation page, component and BFF.
  An existing cold page-module import exceeded its initial five-second timeout;
  rerun with a 15-second timeout passed without weakening assertions or skipping
  tests. TypeScript checking separately exited 0.
- Sequential author self-review, not an independent review. No full Python suite
  rerun, no operating-data edits, no new migration, no automatic commit/push.

Important deployment consequence: an editable reference calendar is no longer
accepted by valuation. Publish and explicitly assign a sealed reference version
before calculating; this implementation does not secretly rewrite existing
calendar or policy configuration.
