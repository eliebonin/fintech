# Lifecycle business-day date colours

**11 November 2026 — implemented, verified and locally activated.**

## What Ops sees

The Lifecycle table's Event date cell retains the contractual date and adds a compact labelled proximity badge. Instrument/Event columns, workflow statuses, action buttons and the side panel remain separate. A collapsed **Timing guide** explains the palette and calendar/estimate distinction without colouring entire rows.

| Proximity | Appearance | Example label |
| --- | --- | --- |
| Today | Strong green | Today |
| Next 1–2 business days | Pale green | In 2 business days |
| Next 3–5 business days | Very pale green | In 5 business days |
| Beyond 5 business days | Neutral | More than 5 business days |
| Past deadline requiring action | Amber | Overdue / Deadline passed |
| Completed, past informational, missing or conflicting calendar evidence | Neutral | Completed / Date passed / Calendar coverage missing |

An elapsed timed cutoff can be amber on today's date. Date shading never means booked, independently approved, exercised, settled or paid. Existing status/attention fields remain authoritative and unchanged. Relative timing is assessed at the report's recording time, rather than against its From/To filters or the browser clock. Refresh the report for a fresh assessment.

## Calendar basis and explicit limitations

Calendar choice is for this read-only display, not contractual business-day adjustment:

1. An explicit calendar on the selected coupon's retained schedule.
2. A single unambiguous calendar shared by the instrument's visible listing venues.
3. An effective strategy **SETTLEMENT** calendar assignment.
4. If none is configured, a clearly labelled Monday–Friday estimate: **Est. 2 weekdays**. Holidays are not claimed to be assessed.

Conflicting visible venue calendars, an inaccessible/inactive/unsealed configured calendar, invalid timezone, or missing dated coverage produce a neutral result. A known but unusable calendar is never silently replaced with weekdays. Calendar names are exposed only for active, sealed, visible versions available at the recording cutoff. No currency-based calendar guess, valuation-calendar substitution, new calendar configuration or operating-data backfill was introduced.

Calendar-local dates define today when a calendar is available; estimates use the response UTC recording date. OPEN and HALF_DAY count as business days; CLOSED/holiday dates do not. Tenant calendars use their frozen composed day decisions. Platform calendars reuse the existing reference session/holiday conflict rule; contradictory or absent evidence stays unknown. Count the interval `(today,eventDate]`, never roll an event falling on a closed date, and label a future event before the next open day accordingly. Strategy assignment validity remains enforced across counted dates; future reassignment is not inferred.

Counting stops after 6 known open days establish the later band. Calendar day loading is bounded to 40 days beyond today, plus timezone-edge coverage. If six open days cannot be established in that horizon, timing stays neutral rather than assuming coverage. This limit affects colour only, never event discovery, counts or eligibility.

## Implementation and performance boundary

- [Pure timing classifier](../../lifecycle/date_timing.py) owns bands, labels, timezone/elapsed-cutoff behavior and honest unknown/weekday states.
- [Calendar source batch](../../lifecycle/date_timing_store.py) resolves only already-authorised, paginated rows. Queries are batched in 500-ID chunks: coupon calendar pointers where applicable, visible listing venues, scoped strategy assignments, visible calendar versions and public session/holiday rows. No per-event SQL, global cache or financial write.
- [Worklist](../../lifecycle/worklist.py) adds `dateTiming` after full-population filtering, status counts, sorting and pagination. The additive [response model](../../lifecycle/worklist_contracts.py) and generated frontend contracts carry tone, label, count, calendar basis/name/timezone, evaluated date and explanation. These hints are response projections, not persisted financial evidence.
- [Report](../../apps/ops-console/src/features/lifecycle-worklist/worklist-report.tsx) renders labelled date badges and a keyboard-operable guide. Individual source explanations are in the badge's accessible label and tooltip. No client-side date arithmetic is used.

The earlier55-call option measurement predates this feature; additional calendar projection calls are not a regression of the previous per-trade batching. Exact query-growth checks and final verification below distinguish these operations. Further authority-context/evidence consolidation remains [open](../../FIX.md#lifecycle-read-redundancy-003--fixed-option-worklist-overhead-remains-after-batching).

## Accessibility reference

Colour is supplemented by visible relative-date text and the Timing guide, following [W3C: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html). Dark green/amber text remains readable on light backgrounds; the three green levels are supplementary rather than the only distinction. Neutral fallbacks keep the report usable without intrusive alerts.

## Verification and activation

Verification is scoped to the changed projection, calendar sources, existing product discovery, frontend report and isolated desktop/mobile journeys. No full project regression, operating booking or valuation publication is part of this task. No database migration is required.

- [Timing/calendar cases](../../tests/test_lifecycle_date_timing.py): **18 passed**. Covers band boundaries, weekends/holidays, half days, published reference sessions, tenant-frozen days, source precedence, private calendar protection, timezone/elapsed-cutoff behavior, completion, explicit estimates and unknown coverage. A first integration run exposed missing required idempotency fields in the synthetic assignment fixture; the fixture was corrected and all18 cases rerun successfully without weakening product validation.
- **79 existing product-discovery cases passed** across bond/FX-oriented worklist behavior, option/future milestones, coupon notices and direct/swap structured inspection. These were run in the same initial95-case group as16 timing tests:93 passed,2 fixture failures; the final18-case timing rerun above resolved those failures and covered2 additional source cases. This is not reported as a fully green single95-case run.
- Existing distinct-contract/page query budgets: **6 passed**. Options58→58, futures56→56 and FX82→82 as the population grows from1 to13 contracts. These native helper counts include the added display projection; the former counts were56/54/80 respectively. The additional2 reads in these fixtures are bulk listing-calendar and strategy-assignment lookups. Configured calendars add bounded parent/day queries; no per-event SQL is introduced. The1-row versus30-row governed-calendar regression has the same query count.
- Frontend report/client: **6 passed**, plus TypeScript typecheck. Existing isolated structured browser journeys: **3 passed** in installed Edge, covering date badges/guide, direct and swap inspection, stale evidence, focus restoration and390px viewport containment. The initial browser assertion matched both the table and legend's Today label; scoping it to the table resolved that test ambiguity.
- Badge text contrast checked numerically: Today6.74:1, Soon7.74:1, Week8.42:1, Overdue7.14:1 and Neutral7.12:1. Every foreground/background pair exceeds4.5:1; visible labels remain the primary distinction.
- API schema export/check and maintained Markdown links/whitespace checked. No full project suite was run.

The verified project-owned API8000 was restarted and frontend3001 remained healthy. Schema115 and retained trade, assistance, subscription and audit counts were unchanged by restart. Authenticated live BFF reads returned200 with17 bond maturities,18 coupons,8 FX maturity events and270 structured events; date-timing metadata was present and structured inspection returned200. The8 prior FX BLOCKED states and all event counts remain unchanged. Single local HTTP samples were0.858s/0.570s/0.664s/2.201s respectively; these include BFF/authentication and are not controlled paired performance measurements. Temporary verification sessions were revoked. No operating booking, payment, grant or strategy-calendar assignment was created or changed; Toolhive was untouched.

Local machine-readable activation/HTTP evidence is in ignored `.superpowers/sdd/2026-11-11-lifecycle-readers/date-colours/`; test logs are in its parent. All owned disposable test databases for this task were checked for cleanup.
