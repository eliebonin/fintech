# Daily valuation recognition implementation plan

> Use superpowers:executing-plans sequentially; no subagents or full-suite reruns per user instruction. Continue approved feature checkout to preserve uncommitted prerequisites. Delivery ledger records author review and verification; no automatic commits or operating activation.

**Goal:** Govern trade recognition dates and remove timestamp entry from daily P&L.
**Architecture:** Shared booking metadata and additive indexed storage; date-aware projection consumes frozen evidence. Daily transport resolves dates to explicit UTC end-of-day boundaries while existing policy resolves market targets independently.
**Tech stack:** Pydantic, SQLAlchemy/PostgreSQL, React/Next.js, pytest/Vitest.
**Spec:** ../specs/2026-10-08-daily-valuation-recognition.md

## Tasks

1. [x] Add shared `valuationRecognition` validation/default/freeze helper and optional booking fields inherited by every product; add revision 72 and trade views. RED tests cover omitted defaults, timezone offsets crossing UTC midnight, later-date reason, earlier dates and immutable metadata. GREEN pure checks first.
2. [x] Adapt repository/projection to daily recognition and preserve actual execution evidence/action safety. RED tests cover deferred buy/sell, closed round trips, legacy date defaults, late booking, correction before delayed recognition, and corrupted snapshot/row mismatch. Verify hand-derived quantities and P&L; isolated DB adapter checks after pure GREEN.
3. [x] Add date-based valuation contract and resolve daily requests before attempt execution; retain timestamp API compatibility and deterministic request identity. RED contract tests cover dates, mixed input forms, 31-day bound, future/information ordering and duplicate keys. Verify API in owned disposable DB.
4. [x] Add shared valuation fields/review to every booking ticket; date inputs and actionable field errors on valuation UI. RED component/model tests cover default preview, overrides/reasons, frozen retries, daily payload and request editing. Generate OpenAPI/TS, run focused frontend tests and typecheck.
5. [x] Author review, scoped integration/migration/correction regression, delivery report with research references and activation status. No full project test suite; no operating financial writes.

## Review focus

- Midnight timezone boundaries must default to UTC business date, not input-string date.
- Cancel/rebook and idempotency must retain immutable recognition identity.
- Deferred trades must not bypass corporate-action history safety or instrument effective dates.
- Daily execution effects and quantities must move together; timestamp runs must not ignore overrides.
- Date-only errors must be field-specific and rejected requests editable without losing uncertain-run retries.

Completion evidence and explicit verification exclusions are recorded in ../../delivery/daily-valuation-recognition-progress.md. Task descriptions express the intended verification scope; the delivery ledger is authoritative for checks actually run. Operating activation of revision 72 and service restart completed on the subsequent explicit user request.
