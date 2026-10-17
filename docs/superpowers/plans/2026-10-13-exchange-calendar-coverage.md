# Exchange calendar coverage and valuation unblock

**Goal:** Retain sourced, sealed major-market schedules, connect supported existing
equity venues, and make the user's October 7–8 valuation calculate safely.
**Execution:** Sequential, current feature checkout; preserve unrelated changes.
**Constraints:** Research-grade library data is not exchange-certified. No generic
CME calendar; no missing-price fills, overwritten policies or self-publication of P&L.

1. Research primary exchange sources and inspect installed calendar schedules.
   Record a practical twenty-market source registry, not an exact market-cap ranking.
2. Extend the importer with explicit library snapshot/review-required states and
   source-quality provenance. Test immutability, idempotence, unsupported activation,
   normal/half sessions, and review disagreement before implementation.
3. Preview and publish schedules; activate only existing, supported equity venues.
   Known schedule uncertainties stay sealed REVIEW_REQUIRED, excluded by resolver.
4. Refresh bounded Yahoo FX samples. Explicitly review the existing personal FX
   classification, append new scoped coverage/calendar/policy versions and retain
   old evidence. Test old-policy preservation, wrong-tenant refusal and source precision.
5. Run focused isolated regressions, activate, restart API, and calculate the user's
   latest period in a rollback diagnostic. Report any genuine remaining input blocker.
   Update maintained capability evidence and sources, without production certification.

## Execution result

All five steps completed sequentially. Published 21 sealed versions, 16 ACTIVE
and five REVIEW_REQUIRED; connected seven existing equity venues. Bounded FX
refresh and reviewed configuration produced FLEXIBLE_EOD v3. The October 7–8
calculation passed in a rolled-back diagnostic. API health is 200; 55 focused
isolated tests passed, no full suite. Sources, limitations and evidence are in
[delivery record](../../delivery/major-exchange-calendars-20261013.md).
