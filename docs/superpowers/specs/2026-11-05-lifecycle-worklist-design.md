# Shared lifecycle operations worklist

**Date:** 5 November 2026. **Status:** Implemented; [delivery and verification](../../delivery/lifecycle-worklist-20261105.md). **Scope:** F51/F24, first detector bond maturity.

## Intent and approaches

Give Ops a menu-accessible chronological worklist of upcoming/due/overdue events and their retained preparation/booking states, with strategy/date/type and actionable/information filters. Reuse the accepted tier, permission, profile-allocation and native redemption boundaries.

Chosen implementation: derive current events on request from governed reference dates, immutable ledger evidence and existing native proposal/posting history. Compared with a persisted task catalogue, this avoids refresh workers, stale duplicated status and another financial authority. It trades a current-ledger query for each refresh; no acknowledgement/dismissal/email delivery is promised. A decorative calendar/timeline alone was rejected because Ops needs filtering/comparison/actions.

## Discovery and scope

Only BOND_MATURITY discovery is delivered here. General typed rows/navigation admit later detectors; existing FX closure/coupon pages remain available. Require tenant membership, LIFECYCLE_READ on the exact strategy, current positive lifecycle ceiling and selected event tier>=1. No implicit notification upgrade from ordinary trading or ceiling3. Selected tier above ceiling is retained and visibly blocked; it is not clamped. Subscription0 returns a clear unavailable state with no event population. Configuration/history remain independently accessible.

Resolve tenant/strategy permission in SQL before candidate discovery, counts and pagination. Candidate instruments come from scoped booked securities and canonical/listing parents, not an unscoped security-master scan. Include current open allocation buckets, even when opposing classifications have net0. Do not manufacture positions for absent or malformed evidence: retain a blocked/unassessed event with a reason. Reuse immutable ledger removal/recognition, exact Decimal amounts and allocation reconstruction. Current reference maturity is disclosed; missing/conflicting booked dates/terms require review. No price, quantity or zero is guessed.

Default date window today-30 through today+30 UTC; an explicit Include earlier overdue checkbox includes open overdue items before From. Historical native completed events outside the requested range are not added by that checkbox. Current-time evaluation is labelled; this is not historical point-in-time reconstruction or settlement/accounting.

Stable event key hashes tenant/strategy/canonical instrument/event type/maturity. Current labels/identifiers are human-facing; UUIDs remain behind context links. A flat ordinary position without native history is omitted. Native posted history may remain as information; cancellation/reopened exposure must not remain labelled completed. Zero net with opposing nonzero allocations remains actionable. Summaries and filtering cover the full scoped population before25/50/100-row pagination.

## State and execution

Show Upcoming, Due, Overdue, Prepared/Awaiting approval, Booked, Reassessment required or Blocked, with textual reasons. Future/complete events are informational; open due events are operationally actionable regardless of whether this individual user can post. Separate group permissions, assistance selection, native independent review and source readiness.

Prepared policy/assistance mismatches require reassessment. Source readiness is advisory until authoritative preview; never label a browser row a posting guarantee. Display exact remaining quantities by currency/unit and nonzero allocation-entry count rather than netting incompatible scopes.

Each row opens event context/details and a clear appropriate link: manual handling for selected1, preparation for2, eligible native DIRECT one-click booking for3, independent review when REVIEW requires it. Links preserve exact strategy/instrument context in the existing maturity workspace. No financial effects occur on discovery, filtering, row selection or navigation. No duplicate posting implementation. Existing native preview/preparation/posting/cancel/retry/audit remains authoritative. Booked means exposure-closure evidence, never payment.

## UI

Menu entry Lifecycle opens /lifecycle; existing /trades/lifecycle remains the native operation workspace. One concise guidance widget, labelled filter ribbon, summary counts, chronological table and optional closable detail panel. Text statuses accompany color. Use semantic headers/captions, row-specific action labels, keyboard focus and a contained horizontal scroll for narrow tables. Avoid repeated warning banners and exposed UUID columns. Default rows25;50/100 optional. Errors retain applied filter intent and a clear retry path.

## Acceptance and limits

Lightweight state/query tests first; disposable DB coverage for two tenants/scopes, tier0/1/2/3, buy/sell/cancel, zero-net opposing allocations, upcoming/overdue, closed/native-posted/cancelled histories, source-policy change and whole-population filtering beyond25. Thin GET routes, exact BFF query forwarding and generated DTOs; no new migration unless implementation reveals a real storage need. Mounted browser tests cover filters, pagination, context handoff, read-only/blocked states, mobile/keyboard and console errors; use own in-app browser for local read-only verification. No operating grants, bookings, valuations or production sign-off. Persisted notifications/assignment/acknowledgement, email, other instrument discovery and settlement remain follow-up work.

## Research applied

Checked 5 November 2026: [W3C WAI tables](https://www.w3.org/WAI/tutorials/tables/) supports semantic headers/captions; [GOV.UK tables](https://design-system.service.gov.uk/components/table/) supports comparable scan-friendly rows. [Notification banners](https://design-system.service.gov.uk/components/notification-banner/) recommends keeping directly relevant information in main content and sparing use of banners. Applied as row-level explanations, labelled filters and a table; the lifecycle rules and derived-store choice are project decisions, not external financial standards.
