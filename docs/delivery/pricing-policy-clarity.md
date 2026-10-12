# Pricing policy clarity and compatibility

Yahoo follow-up: [Personal valuation permissions](yahoo-personal-valuation-permissions.md)
records the explicit local activation and remaining economic prerequisites.

## Readable valuation failures (2026-10-09)

Failed run evidence now has a plain-language explanation above the operational
log, with the affected instrument and price date when recorded, policy requirements
and available price types when present, and links to pricing policies or data-source
permissions. Permission failure, missing policy coverage and ineligible prices are
distinct explanations. Unknown or older failures preserve the recorded reason
without inventing a diagnosis. Original event JSON remains expandable under
`Technical details (JSON)`; stored evidence and backend permission gates are unchanged.

This works for existing failed attempts; no new calculation is needed. Refresh the
valuation page and open the failed run. Focused rendering tests cover the supplied
TTE permission failure, policy/price failures, unknown reasons, escaped markup,
missing legacy reasons and latest-failure selection.

## Valuation policy selector correction (2026-10-09)

Valuation choices now display `Display name · POLICY_CODE · vN`, rather than
the display name alone. Versions sharing a name are distinguishable; within
each policy they are ordered newest-first. The choice still submits the exact
immutable policy-version ID and its associated cut. No version is automatically
selected or substituted, and no stored policies, pricing rules, rights or
valuation economics are changed. Reload the valuation page to fetch new labels.

A focused API regression creates two active versions sharing a display name and
checks that each returned label identifies its own version and retains its cut.
This selector fix does not implement adjusted-price normalization or FX conversion.

Follow-up: [Closing-price consolidation](closing-price-consolidation.md) supersedes
the separate `OFFICIAL_CLOSE` price-family choice described in this earlier record.
The current editor uses `CLOSE` with an optional official-close requirement and
separate closing-method metadata; historical policy rows and evidence are retained.

## Design and research (2026-10-08)

The goal is to configure pricing policies without needing to understand storage
codes, and to identify incompatible recorded data before a valuation run. This is
an improvement to existing policy configuration, not a new pricing or licensing
system. Existing policies, observations, rights and trade recognition remain intact.

Authoritative guidance checked online:

- [GOV.UK error messages](https://design-system.service.gov.uk/components/error-message/):
  explain the problem and remedy, retain entered values, and distinguish permission
  or service restrictions from invalid user input. Applied to compatibility notices
  and instrument-specific failure diagnostics, not misleading field-validation errors.
- [W3C form notifications](https://www.w3.org/WAI/tutorials/forms/notifications/):
  understandable feedback, accessible status/error messages and field associations.
  Applied to linked hints, live compatibility results and actionable error summaries.
- [GOV.UK select](https://design-system.service.gov.uk/components/select/): clear
  labelled options and associated explanatory text; public-facing services should
  consider simpler questions/radios before selects. This is an existing expert
  settings editor, so we retain controlled selects rather than add a wizard.
  Technical/custom settings remain available under advanced details.
- [Alpha Vantage daily data documentation](https://www.alphavantage.co/documentation/#daily):
  vendor daily closing data and adjusted data are distinct products. This corroborates
  keeping timing, price adjustments and provenance separate; it does not certify
  Yahoo values or grant permissions for them.

Our inference: exchange-close timing must not require an OFFICIAL_CLOSE storage
label. The valuation alpha can accept CLOSE or OFFICIAL_CLOSE only with RAW price
basis and the same existing governed-session, currency and permissions safeguards.
Yahoo SPLIT_ADJUSTED data must not be relabelled RAW just to satisfy the engine.

## Implementation scope

1. Controlled plain-language price families and adjustments, close-by hints and a
   glossary separating timing, price representation, provider and permitted use.
   Advanced settings preserve existing/custom technical codes.
2. A read-only tenant-scoped metadata catalogue and unsaved-policy compatibility
   check, using actual stored series/bases and current scoped purpose/activity rights.
   Show known matching sources and incompatible sources separately. No prices,
   confidential licensing evidence, observations, policies or valuations are written.
3. Check before saving. Incompatibility is clearly acknowledged before saving a
   configuration intended for future data; never claim the policy is valuation-ready.
   Compatibility is not proof that all instruments/dates have eligible observations.
4. Instrument/date/rule-specific failed-input messages and preserve current financial
   safeguards. Accepting a CLOSE label is not accepting adjusted data, cross-currency
   valuation, unknown calendars or unlicensed sources.
5. Focused RED→GREEN tests, contracts/typecheck, local restart and read-only acceptance.
   Sequential execution, existing feature checkout, no full suite, no automatic grants.

## Delivered (2026-10-08)

- The pricing-policy page separates price timing, price family, adjustments and
  permitted use. Provider closing prices are not described as official exchange
  prices merely because the timing is exchange close.
- Available source definitions show recorded purposes, automated-calculation
  activity permission and per-series valuation coverage separately. Source-wide
  matching/incompatible definitions are shown next to each rule; these do not
  assert that a particular instrument/date is covered.
- `GET /v1/market-data/policy-data-options` and
  `POST /v1/market-data/policy-compatibility` are read-only, tenant/module scoped.
  Inventory uses exact series/package entitlement checks, not dataset-level
  permission shortcuts. It selects no observation values or confidential evidence.
  Historical observations are collapsed to distinct series/source/basis profiles
  before correlated entitlement checks.
- Saving first checks the unsaved configuration. Notices prevent an ordinary save;
  an administrator may explicitly acknowledge saving a future-data configuration.
  Acknowledgement is tied to the exact draft, not reused after edits. Creation
  still uses its existing immutable versions, authority and idempotency checks.
- Missing valuation-input messages now identify the instrument, date, expected
  definition, visible stored definitions and permission shortfall where applicable.
  New failed attempts receive this context; historical operational logs are unchanged.
- Valuation accepts RAW `CLOSE` as well as RAW `OFFICIAL_CLOSE`. This removes a
  storage-label-only restriction, not adjustment, calendar, currency, timestamp,
  corporate-action or permissions safeguards. Existing policies are not migrated.
  The new flexible template uses LISTING / CLOSE / RAW.

## Verification and local acceptance

- 50 focused backend tests passed across policy compatibility, flexible policies,
  valuation service, package-scoped rights and composite policy HTTP handling.
- A further 27 focused backend tests passed for valuation API/storage, evidence
  access and source priority (77 total). OpenAPI export check passed; regenerating
  TypeScript contracts produced an identical SHA-256 hash.
- 13 frontend tests passed for terminology, source-definition matching, accessible
  compatibility notices and policy helpers/editor rendering. Typecheck passed.
- API restarted; signed-session BFF requests to the new endpoints returned 200.
  Policy page returned 200 with the new labels and compatibility control. Metadata
  catalogue responses measured approximately 271–308 ms locally after warm-up.
- A read-only check narrowed to the real TTE Paris listing and real personal Yahoo
  dataset correctly reported zero eligible matches, adjusted-price mismatch,
  missing valuation-use coverage and missing governed-calendar signoff. No policy,
  permission, observation, trade or valuation was created by this acceptance check.
- No migration is required. No full regression suite was run. Browser click-through
  remains unverified because browser automation was unavailable; HTTP/SSR checks
  do not replace that interaction acceptance.

## How to use it / remaining boundaries

Open `/market-data/policies`, expand **Available source definitions**, then select
or configure a policy and use **Check data compatibility**. To diagnose one source
or instrument, narrow the source dataset and subject reference filters. A broad
rule may find compatible synthetic sources even when a real holding has no match.
The compatibility response explicitly checks configuration metadata, not portfolio
coverage, specific pricing dates or successful valuation. Use the saved-version
preview for instrument/date selection evidence.

The real Yahoo history still records CLOSE/SPLIT_ADJUSTED and
ADJUSTED_CLOSE/VENDOR_ADJUSTED, INTERNAL_REPORTING only, and no automated-calculation
permission. It has not been relabelled RAW or granted access. Governed exchange
calendar coverage and cross-currency FX valuation remain separate prerequisites.
This work clarifies those blockers; it does not claim the failing P&L now succeeds.
