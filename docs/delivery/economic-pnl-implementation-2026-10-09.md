# Economic strategy P&L — implementation and activation boundary

**Status:** Implemented bounded alpha; local schema/app activated, browser and financial acceptance pending  
**Content type:** Delivery report  
**Owner:** Market-data and valuation team  
**Last reviewed:** 2026-10-12

## Delivered

Current capability/gap summary: [valuation and P&L records](../product/features/valuation-and-pnl.md). The activation/test statements below are dated evidence, not a claim that today's database/services were freshly inspected. Later Yahoo RAW evidence supersedes the earlier unqualified price-proof blocker; financial/browser sign-off remains separate.

The [agreed foundation](economic-pnl-agreed-foundation-2026-10-09.md) and
[implementation plan](../superpowers/plans/2026-10-09-economic-strategy-pnl.md)
extend the existing position engine, resolver and immutable review storage, not
the retired demo calculator. Method `economic-position-pnl-v3` retains readable
historical methods and legacy retry identities.

- Price inputs retain original selected values separately from normalized
  as-traded values. Split conversion needs immutable, complete, source-linked
  split-only proof; adjusted data is never simply relabelled RAW.
- FX converts trade-price currency to reporting/strategy currency. Direct pairs
  are governed by independent timing/freshness rules; reciprocal conversion needs
  explicit permission. No silent triangulation or currency fallback. Multi-day
  foreign results aggregate daily PRICE/FX/CROSS bridges, with each execution
  translated using its economic day's closing FX. Frozen evidence retains rates,
  orientation, economic/observation dates, rules and permissions.
- Fund listing positions resolve the canonical share class's NAV. Explicit fund
  calendar/lag and publication cutoffs govern NAV selection independently of FX.
  Native NAV quotations require factor/multiplier one; unproved listing unit
  normalization blocks. T+1 publication does not change the NAV's economic date.
- New bond BOOKED evidence freezes clean execution amounts and quotation terms.
  A dirty execution is normalized using its frozen clean/dirty/accrued settlement
  bridge. Clean market marks use nominal / 100 economics. Legacy unproved booking
  conventions and dirty market marks without per-nominal proof remain blocked.
- Append-only daily bond accrual inputs hold assessed eligible nominal, source,
  convention, opening/closing balance, daily earnings, balance movements and FX.
  Opening + earnings + movements must equal closing. Only daily earnings enter
  ACCRUAL; the accumulated balance is not income again. Local and reporting
  amounts are retained. Opening receivable FX is separately labelled CARRY.
  Coverage follows daily exposure, including weekends; one canonical input is
  allocated once, not once per listing. Missing is distinct from assessed zero.
- Typed dividend/reset/coupon/fee flows are actual ledger trades, not fabricated
  share executions. Explicit INCOME/PAYMENT_ONLY controls recognition. Coupon
  receipts are payment-only alongside earned-interest inputs. Cancellation is a
  retained lifecycle event. Operators still own correct economic classification;
  this is not an automatic corporate-action or reset reconciliation engine.
- Market, gross and net totals reconcile independently. Recorded economic
  inputs do not imply that every unbooked income or cost has been captured.

## Staging, amendment and publication

Calculation creates an immutable staged candidate. A component request specifies
a signed reporting-currency delta, exact base attribution, reason and source.
PENDING requests block publication. An independent approver creates a replacement
candidate and retained attribution version; requests are APPLIED, REJECTED or
STALE. Recalculation atomically marks the replaced candidate's pending requests
stale. PRICE/FX/ACCRUAL corrections use source correction and recalculation, not
manual changes to calculated market values.

Publication checks selected versions, totals, reporting currency, current source
permissions, known accrual revisions and the official population. Strategy-wide
input revision locks serialize accrual correction with approval/publication,
including corrections to earlier days in a multi-day period. Published financial
history is not overwritten. A corrected-input run can retain predecessor batch
and reason. Normal calculations remain available without a predecessor.

The UI shows authoritative component totals, original/used price and FX evidence,
daily versus accumulated interest in local/reporting currency, an assessed-input
register, request history, source correction/recalculation and independent review.
Read-only/published views have no mutation forms. The frontend does not calculate
financial totals. Existing readable operational failures and raw JSON are retained.

## API and migration changes

Authenticated `/v1/valuation` additions: accrual-input GET/POST, economic-flow POST
and cancellation, amendment request listing/creation and independent approval or
rejection. Existing calculation/publication endpoints retain their roles. Decimal
amounts travel as exact strings. Input/review administration requires the existing
tenant MARKET_DATA + VALUATION authority; flow booking also requires TRADING
booking authority. BFF routes use tenant context and an explicit route allowlist.
OpenAPI and generated TypeScript contracts were regenerated.

Additive revisions, tested on disposable databases only:

| Revision | Purpose |
| --- | --- |
| 77 | Economic price requirements and immutable conversion proof |
| 78 | Explicit inverse FX policy permission |
| 79 | Versioned daily accrual side inputs |
| 80 | Immutable amendment request/state records |
| 81 | Economic method compatibility in attribution scope guards |

No operating migrations, policies, booked trades or financial publications were
changed for this implementation. Before activation: back up the operating DB,
apply revisions through 81, restart API/UI, confirm source rights/calendar and
price-basis readiness, then run synthetic tenant acceptance. Do not manufacture
proof or relabel Yahoo data to make a real valuation pass. Rollback should favour
disabling new writes and restoring the prior app against retained evidence;
destructive downgrade is not a routine rollback once new financial data exists.

## Verification and remaining boundaries

Sequential lightweight tests preceded integration checks. The latest broader
relevant disposable run passed 58 tests across acceptance, FX, accruals, flows,
amendments, storage, API, source permissions, lineage and retry compatibility.
Focused UI coverage passed 30 tests; TypeScript typecheck passed. No full suite
was run. Additional acceptance and final verification are recorded in the
[execution ledger](economic-pnl-implementation-progress.md).

Acceptance includes dirty bond execution + clean mark + daily accrual + dividend,
independent staging/publication, canonical fund NAV with holiday lag and late
publication exclusion, stale requests, correction revisions and permission gates.
A test-fixture strategy lock initially stalled independent operational attempts;
the fixture now starts the operational attempt before taking the synthetic booking
lock. This was a fixture ordering issue, not an operating database change.

Real browser sign-off is incomplete: the desktop browser tool failed to initialize
twice. An isolated API/UI was started for verification, and the API detail returned
HTTP 200; this is not equivalent to browser walkthrough acceptance.

Explicitly not delivered: full fund NAV/accounting, cash balance stock valuation,
automated bond accrual computation, dirty market quote normalization without
assessed evidence, supported redemption/derivative final-mark handlers, automatic
split position replay, FX triangulation, complete unbooked income coverage or an
independent provider comparison. Mature bond holdings and unsupported option,
future, swap, structured or FX-forward economics remain blocked rather than
inventing a final price or settlement. Yahoo chart events alone were insufficient
at the initial checkpoint. The subsequent [anchored derived-RAW implementation](yahoo-market-data-alpha.md#derived-as-traded-raw-closes--2026-10-09)
retains full assessed split coverage, snapshot reference and source lineage under
an explicit provider-method assumption. This enables qualified as-traded marks;
it does not certify official exchange data or implement position quantity replay.
Usability still requires compatible policy, current rights and calendar evidence.

## Local activation — owner approved, 2026-10-09

After explicit approval, the local operating DB was backed up to
`logs/fortem-secm-before-economic-pnl-20261009-114809.dump` (71,856,281 bytes).
Alembic upgrade completed at `20261009_81 (head)`. The API and frontend were
restarted on ports 8000 and 3000. Fresh checks: API `/health` returned `ok`,
OpenAPI exposed accrual-input, economic-flow and amendment-approval endpoints,
and the unauthenticated frontend request returned HTTP 200 after its expected
tenant-selection redirect. Startup error logs showed no application errors.
This supersedes the earlier pending local activation status above. No valuation
was run or published; price-proof/policy readiness and browser sign-off remain
separate. API/UI logs: `logs/economic-pnl-*-20261009-114859.*.log`.

## Research traceability

Source-backed conventions and their limits remain in the
[foundation](economic-pnl-agreed-foundation-2026-10-09.md) and
[price-basis specification](../superpowers/specs/2026-10-09-valuation-price-basis.md).
This delivery makes no GIPS-compliance, licensed benchmark or production-readiness
claim. Financial source semantics and reproducible history take precedence over
forcing a successful calculation.

## Review authority corrections — 12 October 2026

The prior real-operator check searched supplemental access audit for the exact
reviewed resource ID. Amendment approval created a new batch ID, which could lose
the original operator association and permit publication after switching selected
users. The regression reproduced this before the fix.

New calculation attempts retain `realOperatorId` in their immutable STARTED event,
committed with the operational attempt before financial calculation. Amendment
requests retain their real operator in an AMENDMENT_REQUESTED event in the same
transaction as the request. Approved candidates retain the union of calculator
and amendment-requester operators in their STARTED event. Approval, rejection and
publication additionally retain reviewer and real-operator identifiers in immutable
valuation events. No new table or migration is required.

Amendment decisions reject their requesting real operator, and publication rejects
every contributing real operator inside the locked financial transaction. Changing
selected users does not remove these checks. Unchanged retries preserve their
existing request identity; a key cannot be borrowed by another real operator.
Legacy candidates use retained access audit and parent/request lineage without
rewriting historical records. If legacy operator evidence is incomplete, review
through an impersonated identity is blocked until recalculation. Direct trusted
actor calls retain the existing subject-independence check.

Frontend calculation and review controls now follow separate granted actions.
Economic-flow cancellation uses correction permission rather than booking
permission; see [the access correction record](tenant-access-administration.md#valuation-access-corrections--12-october-2026).

Verification: **78 focused backend tests passed** (nine existing dependency/seed
deprecation warnings) against disposable databases. The 164-file frontend suite passed **768 tests**, and frontend
TypeScript and deterministic OpenAPI freshness checks passed. Focused disposable
backend regressions cover operator switching, calculator/requester propagation,
immutable evidence, unchanged/foreign-operator retries, and flow cancellation
permissions at domain and HTTP boundaries. Successful HTTP acceptance covers
calculation/retry, amendment approval, changed-user denial on the replacement,
independent publication, and retained display-right revocation. Commands and
results are recorded in the execution ledger. Two older HTTP assertions were aligned with the existing
central permission boundary's 403 response; no authorization was relaxed.

Implementation and sequential self-review used the existing dirty checkout. No
operating data, migration, financial publication or service restart was performed.
Browser visual acceptance and the full Python suite were not run for this slice.
