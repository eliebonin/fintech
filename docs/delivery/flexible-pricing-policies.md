# Flexible and strict pricing policies

Implemented 2026-10-08. Configuration is available at
`http://localhost:3000/market-data/policies` under Pricing policies.

## Behaviour

- **STRICT:** match explicit rules only. No matching rule blocks input selection.
- **FLEXIBLE:** match explicit rules first; if none match, use a configured default.
  Defaults are visible immutable rules with real rule identifiers, not hidden
  heuristics. A more specific default never outranks a matching explicit rule.
- Once a rule matches, missing or ineligible data does **not** fall through to
  another rule. A London FX fixing cannot silently become another fixing or a
  daily bar. Source priority can choose a different permitted dataset only after
  that same rule's series, basis, convention and timing tests pass.
- Within explicit rules, and separately within defaults, precedence remains exact
  series → exact subject → venue + instrument type → venue → type → broad rule;
  rule sequence breaks ties. All sequences are unique across both groups.

Existing policies retain STRICT semantics. Broad catch-all rules already present
in legacy policies remain **explicit** rules; they are not reclassified as defaults.
To use a default, remove/restrict any broad explicit rule that would match first.

## Configuration walkthrough

1. Inspect a saved version or create a new policy. New drafts start in FLEXIBLE
   mode, labelled **Latest available EoD + overrides**, with one default and no
   competing broad explicit rule. Saved policies are loaded unchanged.
2. FLEXIBLE adds a suggested LISTING / CLOSE / AS_TRADED session-close default.
   It follows each selected listing's exchange/calendar, with SAME_DAY, zero stale
   sessions and FAIL. Edit the default's filters, series/basis, dataset and calendar
   if appropriate. Add explicit rules for required exceptions such as London FX.
   Native RAW prices are eligible; split-adjusted prices require complete evidenced
   conversion back to traded units. This is not acceptance of arbitrary adjustments.
3. An unspecified dataset follows the eligible source priority. A pinned dataset
   remains required and cannot override source exclusions or licensing controls.
4. Save creates a new immutable version; it does not update old versions or select
   the new version automatically for previous valuation requests. Preview uses
   the saved version, not unsaved edits. Readers can inspect mode and both groups.

The former **Default policy cut** field is now labelled **Policy valuation context**.
The request must match this identifier, but it does not impose a universal closing
hour. SESSION_CLOSE follows the listing's exchange calendar; EXPLICIT_TIME and
NAMED_FIXING require a separate rule pricing cut. No timestamp/calendar validation
has been removed to simplify the editor.

For example, one shared listed-close default can use UK 16:30 London, French
17:30 Paris and US 16:00 New York sessions. An explicit FX rule can independently
require London 16:00. Early closes and known closed days come from the relevant
calendar. Fund NAVs, FX and other non-listing subjects do not borrow this default.

Tenant configuration still requires TENANT_ADMIN + MARKET_DATA. No data rights are
granted by policy creation. Neither existing operating policies nor provider grants
were edited as acceptance tests.

## Freshness and “latest available”

Flexibility is about **rule coverage**, not stale-price permission. Defaults require
a composite convention and a finite session allowance. The EoD label means the
eligible close for the expected session, available by the information cutoff; it
does not mean the latest intraday tick or any older observation. Carry-forward is the
explicit **PRIOR_AVAILABLE** date rule within that convention, bounded by the
configured maximum staleness. It is not a generic cross-convention last-price
fallback. Zero allowance is the initial default. An unsupported instrument/series
does not become supported merely because the policy is flexible.

A known closed valuation day targets the previous expected pricing session and
can be CURRENT with zero staleness. A missing expected-session price requires an
explicit allowance; freshness is counted using governed expected sessions, not
calendar days. Unknown calendar coverage remains blocking.

Valuation accepts WITHIN_TOLERANCE only for PRIOR_AVAILABLE/FIXED_LAG rules with a
finite allowance covering the selected mark. Uncapped legacy configuration is
still inspectable but does not permit carrying stale marks into valuation.
As-traded price compatibility and assessed calendars remain required. Exchange-official
designation is a separate optional requirement. Economic P&L now has governed FX
conversion; see the newer economic implementation record for supported products.

## EoD editor clarification — 2026-10-09

- New policy drafts use the existing flexible resolver; no new resolver or schema
  migration is introduced. Existing policy versions, prices and rights are unchanged.
- Mode changes preserve explicit overrides; repeated flexible selection preserves
  customised defaults. Switching a default-only draft to strict creates an explicit
  starter rule rather than an invalid empty configuration.
- Regression covers one shared default across UK, French and US sessions, an
  independent London FX rule and an information cutoff before the US close.
- Frontend: 21 focused tests passed; TypeScript check passed. Backend: 31 focused
  resolver, flexible-policy and policy-API tests passed in an isolated disposable
  database, not operating valuations. The full suite was not run.
- Updated the older fingerprint regression to exclude newly added absent economic/FX
  controls, matching the retained historical retry contract. Production fingerprint
  code was not changed for this task.
- Local policy-page HTTP check returned 200 (unauthenticated selection route);
  this is availability evidence, not an authenticated browser walkthrough.
- The UI change itself did not alter operating policies. Following explicit owner
  approval, FLEXIBLE_EOD v2 and the scoped October 6–7 EUR/GBP setup were activated;
  see [the activation evidence](yahoo-eurgbp-valuation-setup-2026-10-09.md).

## Evidence and compatibility

Resolver v5 freezes policyMode and ruleOrigin (EXPLICIT/DEFAULT) in successful and
failed outcomes alongside existing provider priority, calendar, target and dates.
Failed matches retain the chosen rule ID. Historical snapshots are not rewritten.

Attribution review now displays opening/closing market marks, exact decimal prices,
requested and actual market dates, source dataset, rule and freshness. Actual period
executions retain their booked price, signed quantity and booking factors separately.
No prior-day mark is fabricated for a newly entered position, and no unsupported
per-trade P&L allocation is implied: market marks remain position-shared and trades
remain linked original ledger evidence. Flat opening/closing positions still require
no unnecessary market marks. Cancelled facts do not manufacture execution inputs.

New position evidence has priceEvidenceVersion=1. First recalculation can create a
new retained attribution version solely to capture the enriched evidence; old
results remain intact. Execution inputs are grouped once by position key, rather
than rescanning every execution for every position. Existing evidence display and
independent-review permissions apply to the new readable section too.

Migration **75** adds selection_mode (STRICT by default) and is_default (false by
default), with a mode check constraint. Existing immutable-version guards cover
the new fields. The downgrade is forward-only to preserve authority evidence.
Legacy STRICT creation fingerprints retain their original shape for idempotent
replay. OpenAPI and generated TypeScript contracts include both groups and mode.

## Acceptance record

- Migration 75 applied locally; Alembic reports head75. API restarted on port 8000;
  existing Next dev UI on port 3000 picked up the frontend changes.
- Read-only HTTP checks: signed-session selection, policy page and policy-detail
  BFF return 200. Rendered page contains mode selection and missing-rule safeguard;
  inspected existing policy remains STRICT with two explicit rules and no defaults.
- Initial focused backend regression: 62 passed. Frontend: 16 passed. Typecheck and
  OpenAPI check passed; regenerated TypeScript output is byte-identical.
- Expanded regression initially had 84 passes and one pre-existing timing-sensitive
  source-priority test failure. Read-only clock inspection measured PostgreSQL about
  0.46 seconds behind the host. The test now uses the saved database timestamp ± an
  explicit interval instead of comparing two system clocks. Production cutoff
  semantics were not relaxed. Final expanded regression: **85 passed**, with 41
  existing SQLAlchemy seed-loader / Starlette deprecation warnings.
- No full suite was run, per user preference. No browser click-through signoff is
  claimed; this acceptance used real HTTP/BFF and server rendering.
- Sequential author self-review checked immutable creation/replay, cross-tenant
  reference checks, explicit-before-default precedence, finite freshness and
  restricted-evidence rendering. No outstanding critical/important findings were
  identified. This is weaker assurance than an independent review.

Execution choices: retain the approved dirty feature checkout (no commit/push),
focused tests instead of a full suite, no subagents, latest-date selection only
within declared conventions, linear execution-evidence grouping, and a new
attribution evidence version instead of altering historical results. These trade
off broad/independent assurance and unrestricted fallback for continuity, clear
economic semantics and retained history. The clock-related change is test-only.

## Still separate

Observation price-validation workflows, broader instrument/FX valuation, unrestricted
latest-timestamp conventions and licensing proof workflows remain separate work.
The operating Yahoo personal dataset lacks an active VALUATION purpose entitlement;
this implementation does not bypass that boundary. A flexible policy therefore does
not by itself make an otherwise unlicensed valuation run succeed.

Plan and rulings: [implementation plan](../superpowers/plans/2026-10-08-flexible-pricing-policy.md).
