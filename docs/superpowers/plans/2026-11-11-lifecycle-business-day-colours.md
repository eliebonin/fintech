# Business-day date-colour implementation

- [x] Add failing pure timing and scoped batch/calendar tests, including weekend/holiday, half day, timezone, elapsed cutoff, completion and unknown coverage cases.
- [x] Implement bounded calendar-source batches and timing projection after worklist pagination; retain all financial/status/source logic. Export the additive API contract.
- [x] Render readable date badges/legend with non-colour labels and accessible contrast. Verify focused frontend/backend and existing browser journeys.
- [x] Document configured calendars versus explicit weekday estimates, exact tests and remaining limits; restart only the owned API and verify live reads.

[Approved scope and source rulings](../specs/2026-11-11-lifecycle-business-day-colours.md). Further authority/evidence query consolidation remains a separate pending task.

Outcome: [implementation, verification, calendar limitations and live activation](../../delivery/lifecycle-business-day-colours-20261111.md). No migration or operating financial/configuration changes; further permission-context consolidation stays pending.
