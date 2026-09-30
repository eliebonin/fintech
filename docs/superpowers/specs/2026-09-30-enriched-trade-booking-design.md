# Enriched cash-trade booking design

**Status:** Proposed written specification; conversational scope approved, awaiting document review.

**Date:** 2026-09-30

**Scope:** Enrich the existing manual, already-executed, listing-backed cash ticket.

**Baseline:** [Listed cash booking](2026-09-30-listed-cash-trade-booking-design.md),
[tenant workspace delivery](../../delivery/tenant-workspace-strategy-alpha.md),
and [trade history](../../delivery/trade-history-alpha.md).

## 1. Intent and boundaries

An authorised tenant operator must be able to book a cash execution with its
counterparty, broker, trader, classifications, tags, references and typed custom
properties; review it before submission; and read all those facts back from the
persisted trade. Properties are part of the booking, not transient form fields.

Counterparty and broker are standard party roles, not arbitrary custom text.
Trader is the commercial decision-maker; booking user is the authenticated actor.
Instrument economics remain on the instrument description. No ticket field
duplicates contractual strikes, maturities, underlying baskets or other terms.

Keep the dedicated menu entry `/trades/new` and its listing search. A preselected
listing URL remains supported, but do not restore booking links on instrument
details. Keep the existing tenant membership, `TRADING` and `TENANT_ADMIN` write
boundary. Expanding booking roles is a separate permission decision.

Exclude fees/net settlement, holiday-aware settlement, off-venue execution,
OTC/derivatives, subscriptions/redemptions, amendments/cancellations, allocation,
order routing, confirmation matching, settlement workflow and valuation/P&L
changes. This is not regulatory reporting or counterparty credit approval.

## 2. Existing implementation versus new work

| Capability | Current evidence | Enrichment |
| --- | --- | --- |
| Counterparty | `TradeBookingRequest.counterpartyOrganisationId` and `trd.trade_party_role`; no ticket control | Searchable selector and read-back |
| Broker | Generic party-role persistence exists; no booking command field | Add explicit `EXECUTING_BROKER` selection |
| Trader | `trd.trade.trader_person_id` exists | Eligible-person lookup, command validation and ticket field |
| Classification | Trade type/purpose/activity columns exist; booking fixes type/purpose to `INVESTMENT` | Controlled purpose and market activity; display fixed type |
| References | Existing external-reference rows; command accepts one source reference | Structured repeatable references with source/type |
| Tags/properties | Design notes mention tags, but current metadata has no trade-tag/custom-property tables | New tenant-scoped definitions and assignments |
| Fees | Existing fee rows and read views | Deferred; do not pretend booking captures them |

`list_organisations` currently returns active shared organisations, not a
tenant-approved counterparty list. The enriched alpha explicitly retains this
shared reference catalogue for organisation selection, labelled as such. Active
status is the alpha eligibility rule, not evidence of onboarding or credit
approval. A tenant allowlist/onboarding module is deferred rather than implied.
This written policy choice requires confirmation during document review.

## 3. Page structure

Use a sectioned single-page ticket followed by a read-only review state, not
separate editable tabs or a multi-stage wizard.

1. **Instrument and strategy:** searchable active listing; locked instrument,
   ticker, venue and currency; active tenant strategy.
2. **Execution:** side, positive quantity with displayed unit, positive unit
   price, offset-bearing trade time and editable settlement date.
3. **Parties and responsibility:** counterparty, executing broker, trader and
   read-only booking actor. Keep this section expanded and readily visible.
4. **Trade classification:** read-only `INVESTMENT` trade type; purpose choices
   `INVESTMENT`, `REBALANCING`, `HEDGING`, `OTHER`; market activity `PRIMARY` or
   `SECONDARY`, or unspecified. `OTHER` requires an explanatory comment.
5. **Additional properties and tags:** typed property controls and catalogue
   tag selection. Required properties keep the section expanded; otherwise it
   may collapse, showing how many values/tags have been entered.
6. **References and notes:** optional repeatable source/client/broker references
   and comment. Reference types are controlled; no arbitrary key names.
7. **Review booking:** all execution facts, parties, classifications, tags,
   populated properties, references, notes and unsigned gross consideration.
   Actions are `Back to edit` and `Confirm booking`.

Purpose defaults to `INVESTMENT`. Parties, trader and market activity start
unspecified; do not invent a counterparty or silently equate trader with booker.
Standard optional inputs are clearly labelled. Tenant-required custom properties
are required for new bookings only, not retroactively for historical trades.

Retain the current T+2 Monday-Friday settlement suggestion and warning that
holidays are not applied. Preserve manual overrides. This is a convenience,
not a claim that every market settles T+2. Display timestamps with their offset
and normalise to UTC in persistence; validate settlement against the calendar
date entered with that timestamp, consistently in browser and API.

Gross consideration uses decimal-safe quantity times price with explicit
currency, not binary floating-point as the authority. Show no net amount or
settlement cash projection until fees and cash-direction conventions are designed.

## 4. Trade-property and tag model

Standard fields and parties reuse `trd.trade` and `trd.trade_party_role`.
One counterparty and one executing broker are permitted; the same organisation
may hold both roles. Multiple organisations in the same role are out of scope.
The trader selector initially contains active people linked to active accounts
with currently effective active membership in this tenant. External traders
without that relationship are deferred, not selected from an unrestricted list.

Add a trade-specific tenant property registry, not a new universal metadata
framework. Each definition has an immutable meaning and an ID, tenant, stable code, label,
description, type, required flag, active status, display order and controlled
choices where applicable. Types are `TEXT`, `DECIMAL`, `DATE`, `BOOLEAN` and
single-choice `CHOICE`. Definitions and codes cannot impersonate standard
fields such as counterparty, trader, quantity or instrument terms.

Store one typed value per trade/definition, preserving the definition meaning
used at booking. Decimal values travel as decimal strings; booleans are actual
booleans; dates are valid ISO dates. Empty optional values are omitted, not
confused with zero or false. Reject unknown types, invalid choices, duplicate
property IDs, cross-tenant definitions and inactive definitions on new bookings.
Changing type, requiredness or choice meaning creates a replacement definition
rather than reinterpreting old values. Retirement prevents new use but preserves
historical display. Active status may change with audited retirement; meaning
does not. Retain audit actor/time for registry provisioning.

Tags have tenant-owned stable IDs/codes, labels and active status, with unique
trade/tag assignments. Tags classify trades; they do not mutate instrument
taxonomy. Reuse existing instrument-taxonomy concepts only where scope matches;
do not assign a trade to an instrument-only taxonomy table.

For the alpha, provide validated tenant-specific provisioning through an
administrator-only command/script and demonstrable seeded definitions/tags.
Full configuration authoring UI is a follow-on, not a prerequisite to using
properties on the ticket. No inline definition creation while booking.

## 5. Command, transaction and compatibility

Extend the existing booking request with optional trader, broker, controlled
purpose/activity, structured external references, tag IDs and typed property
values. Existing minimal callers remain valid when the tenant has no required
properties. Existing `counterpartyOrganisationId`, `externalReference` and
`comment` remain supported; reject simultaneous legacy/new reference inputs if
they would be ambiguous rather than silently duplicating them.

Use the same BFF-only authority boundary. Tenant and booking actor come from the
signed session. Lookups are bounded/server-backed; person, property and tag
lookups enforce tenant visibility. Selection is not authorisation: submission
rechecks membership, entitlement, active strategy/listing and every reference.
Existing parent-instrument, currency, venue and supported-product validation
must not be weakened by adding optional fields.

In one transaction persist trade, parties, references, property values, tag
assignments, initial lifecycle evidence and durable idempotency result. A failure
in any child must leave no partial booking. Add constraints for unique
assignments and tenant consistency, not browser-only checks.

Canonicalise the complete validated payload for idempotency, including every
property and party. Unordered tag/property sets must have deterministic ordering.
Same key/same payload returns the original trade; changed facts conflict. After
an uncertain network outcome, retain the exact submitted payload/key for retry;
never rotate the key and risk a second booking. Clearly distinguish editing a
not-yet-submitted draft from starting a genuinely new ticket.

Capture expected tenant context when opening the ticket; reject a submit after
context changes rather than booking silently into a different tenant. No
persistent local-storage drafts are introduced. Preserve in-memory form values
on validation/network failures and warn before knowingly discarding edits.

## 6. Read-back and errors

Trade details display the standard fields, named party roles, trader versus
booker, references, tags and each populated property with its label/type.
Historical retired definitions/tags remain readable. Older trades render empty
sections honestly, without inferred parties or synthetic property defaults.
The history table stays compact; counterparty/trader/tag filters can be added
without displaying every property as a column. Arbitrary-property reporting is
deferred; the detail view is the full read-back acceptance boundary.

Use inline errors plus a linked error summary and move focus to the summary or
first invalid field. Expand a section containing errors. Announce lookup loading,
submission state and success accessibly. If a selection becomes inactive while
the ticket is open, preserve the draft and explain the affected field. Never
silently omit unsupported values. Disable confirmation while a request is in
flight, not merely because a required field is currently empty.

## 7. Delivery and acceptance

Deliver in dependency order: registry/persistence and lookups; enriched atomic
command and contracts; ticket/review; detail read-back and documentation.
Split the UI into focused execution, party, property and review components;
keep the existing route and avoid unrelated repository refactoring.

Lightweight failing tests precede implementation. Add integration tests for
BUY/SELL with parties and properties, exact decimal/false/zero/date handling,
duplicate assignments, invalid/inactive/cross-tenant selections, required
properties, role distinction, rollback, same-payload replay, changed-property
conflict, and retiring definitions without breaking history. Test context
switches, stale choices, preserved draft errors and review/edit transitions.

Finish with complete Python and console suites, TypeScript, production build,
contract regeneration and a local browser booking-to-detail exercise. Do not
submit a real financial trade during automated UI checks. Update delivery docs
with commands, actual outcomes and limitations; do not claim implementation or
test success from this specification alone.

## 8. Research evidence and project decisions

Sources were opened/read during the 2026-09-30 research turn. Record their
applicability, not just links:

- [Cloudscape single-page creation](https://cloudscape.design/patterns/resource-management/create/single-page-create/),
  published 2020-09-10 and still available when reviewed: supports short primary
  forms, grouping related inputs and expandable optional settings. It does not
  prescribe a financial ticket's fields or universally forbid a wizard. Our
  sectioned page and prominent party fields are project choices.
- [W3C WCAG 2.2 error prevention](https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html):
  describes reversible, checked or confirmed safeguards for consequential
  submissions. We choose review/edit/confirm for immutable booking. Recording
  an already-executed trade is not the same as routing a securities order, and
  this source does not mandate a separate confirmation screen for every save.
- [W3C form notifications](https://www.w3.org/WAI/tutorials/forms/notifications/):
  supports clear inline feedback, linked summaries and accessible success/error
  notifications. It informs validation behaviour, not economic business rules.
- [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  supports deny-by-default and object-level checks on every request. Applied
  here to lookups, submission and read-back, not just menu visibility.

Typed tenant properties, their immutable definitions, party cardinality,
shared-organisation alpha eligibility, the restricted trader selection and the
delivery sequence are architectural decisions grounded in the current code,
not requirements prescribed by these UX/security sources. FIX pages could not
be opened successfully during research and are not cited as verified evidence.
