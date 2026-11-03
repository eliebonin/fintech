# Account-owned cash FX P&L

**Status:** Implemented and activated locally; broader financial acceptance remains separate
**Content type:** Delivery, methodology and assurance record  
**Owner:** Valuation / Operations engineering  
**Last reviewed:** 2026-10-25

**Current rule:** cash is always assessed, with no exclusion control or API flag.
Missing cash snapshots are displayed as not supplied and do not by themselves
prevent publication. This supersedes the original opt-in choice. Supplied
nonzero foreign balances still need valid FX and all review/source controls.

Extends [F40](../product/features/valuation-and-pnl.md#f40-full-nav-and-cash-balances)
and the [source coverage report](pnl-source-coverage-20261024.md). The user approved
the [design](../superpowers/specs/2026-10-24-cash-fx-pnl-design.md); execution is
tracked in the [plan](../superpowers/plans/2026-10-24-cash-fx-pnl.md).

## Calculation and scope

For each account, native currency and daily value date:

`cash FX P&L = signed opening native cash × (closing FX − opening FX)`

FX means reporting-currency units per native-cash unit. USD 100,000 with GBP/USD
0.75 → 0.76 earns GBP 1,000; a USD 100,000 borrowing loses GBP 1,000. This is the
approved **opening-balance / end-of-day movement convention**, not an assertion
about actual intraday movement times. A later balance of USD 120,000 does not
make the first day's FX earnings GBP 1,200. For another day, use that day's own
opening balance. Multi-day calculations sum those daily contributions.

Same reporting currency uses 1. Explicit zero opening cash earns zero without
requiring irrelevant FX prices; newly received cash is not income. Deposits,
withdrawals, trade settlements and coupon/reset payments are not inferred from
balance changes and do not automatically enter P&L again. No cash trades or
cash movements are generated. Intraday FX timing/spreads, movement reconciliation
and full fund NAV remain outside this slice.

## Inputs and omissions

- Cash assessment is part of every calculation. There is no `includeCashBalances`
  option in the UI, API, domain request, source-health checks or recalculation.
  Removed request flags are rejected, not accepted as an exclusion override.
  Standard UI requests use daily dates; supplied EoD pairs require EoD boundaries.
- Only native `TENANT_EOD` ledger snapshots are admitted. Every included daily
  account/currency pair needs exact opening and closing dates, including explicit
  zero. No silent carry-forward, aggregation across accounts or invented opening
  balance for a newly appearing currency scope.
- Scope discovery uses only snapshots between the opening and closing valuation
  dates, inclusive. Old account/currency history and never-uploaded accounts do
  not create an expected balance or warning today. For each day, neither boundary
  supplied means no supplied daily scope, not two missing snapshots. One supplied
  boundary without its counterpart remains a disclosed omission, not confirmed
  zero. This is not independently reconciled bank/custody inventory completeness.
- Nonzero foreign opening cash requires both governed FX selections under the
  selected policy and information cutoff. Required missing/ineligible FX blocks
  the calculation; no new inversion/triangulation/fixing shortcut is introduced.
  Inactive currencies and malformed admitted snapshot ownership/conventions block.
- Multiple accounts with the same maintaining company stay separate. Native and
  reporting currencies, exact amounts, source references, notes, snapshot IDs and
  revisions are retained. Source receipt time determines what was known.

## Storage, review and current access

Migration **20261024_99** adds nullable typed `cash_account_id` and
`cash_currency_id` links to attribution/review items, exclusive of trade/position
ownership. Cash-account/strategy ownership, selected review owner and component
totals are checked by database constraints/triggers. No fake instrument or
trade subject is created; no historical financial rows are backfilled.

`CASH_FX` contributes to gross/net once, **not** to investment MARKET components
or the securities opening/closing/execution bridge. Twelve-decimal half-even
storage rounding retains exact inputs/deltas. Approved component adjustments
retain the cash owner; cash FX itself must be corrected upstream/recalculated,
not disguised as a manual override.

Cash writers and publication serialize on the strategy. The database trigger
covers direct native snapshot inserts as well as existing API writers. New or
corrected relevant snapshots invalidate staged publication and amendment approval.
Published figures/evidence remain unchanged and show reassessment required.
The affected-results queue filters cash changes before count/pagination. Only
changes dated within the frozen opening/closing valuation window can flag cash
reassessment or invalidate its source hash. Earlier/future snapshots and unused
account creation do not. Within-window detection remains conservative: a newly
received revision can flag a result even when financial impact is nil. There is
no automatic recalculation or publication.

Existing tenant/strategy authority, current dataset DISPLAY/use rights, real
operator checks, independent amendments/publication and explicitly governed
self-publication remain. Native identity/zero cash can disclose without provider
observations only with validated frozen ownership and zero/identity proof;
missing foreign FX cannot use that exception. Financial acceptance is not inferred
from a source-health badge or an arithmetically reconciled total.

## Ops report

Results shows a separate **Cash FX attribution** account/currency report, not
unnamed securities. Its inspector shows exact daily opening/closing balances,
FX rates, earnings and frozen source/revision evidence. Primary labels are scoped
company/account/currency names; UUIDs/JSON remain in technical disclosures.
Source coverage separates investment FX from cash FX and distinguishes included,
partial, missing and unassessed. Source inspection moves focus to
the correct report. Investment search controls do not filter cash accounts.
Current DISPLAY denial suppresses the financial report and its labels/evidence.
Complete cash coverage has no explanatory/warning banner; its recorded amount
and inclusion state remain in the source table. Missing/partial or unavailable
cash proof still displays the corresponding notice. No financial logic changes.
This display-only removal passed **80 focused UI tests, TypeScript and one
isolated cash-review/publication browser journey**. The included-state banner
regression failed before the change. No backend restart or new valuation is
needed; refresh the frontend to see it on an existing result.

Missing cash is shown with a dash, missing-date/account details and a non-blocking
publication explanation. It is not presented as confirmed zero. Incompatible
historical results have no compatibility opt-out path and need a new calculation
before publication; no financial values are backfilled or silently rewritten.
Request identity includes `economic-pnl-standard-cash-v2` so old retry keys cannot
return a former cash-excluded or history-inferred coverage result under today's
contract. Frozen historical results are not edited; recalculate for new coverage.

## Verification and activation

Initial exact-arithmetic, storage and governance tests were developed RED → GREEN.
An additional RED → GREEN pass reproduced/fixed missing cash reassessment-queue
selection, direct-insert/publication serialization and inactive zero-cash currency
admission. A browser RED → GREEN pass exercised the separate focusable inspector.
Final counts, operational activation and author review are recorded below.
Tests use owned disposable PostgreSQL and synthetic browser servers;
no operating balances/trades/results are created for acceptance.

### Final focused verification

- Owned disposable PostgreSQL + pure tests: **170 passed, 1 pre-existing failure**
  across the selected 18 files. The failure is
  `SchemaMetadataTests.test_every_schema_column_has_documentation`: 94 old column
  comments are missing, also reproduced standalone and against committed model
  code. New cash-owner columns are documented; [SCHEMA-DOC-001](../../FIX.md#schema-doc-001--missing-python-column-comments-minor-open)
  records the unrelated finding. Cash financial/governance tests passed.
- Valuation UI/request tests: **96 passed in 17 files**. Isolated Edge/Playwright
  journeys: **5 passed**, including opt-in cash, source-report focus, exact daily
  inputs, narrow viewport, required review and publication.
- TypeScript check passed after regenerating ignored stale acceptance route types
  with the installed Next `typegen`; normal imports/configuration restored.
- OpenAPI export matches app; regenerated TypeScript is byte-identical on repeat.
  `contract:generate:check` compares against Git HEAD and therefore reports the
  intended uncommitted `includeCashBalances` addition, not generation instability.
- Author self-review (sequential, as requested), not an independent code audit:
  reviewed typed owners, exact signs/daily sums, native zero/identity exceptions,
  cross-strategy labels, missing inputs, existing retry identity, rounding bridge,
  amendments, cash-source queue and publication/write serialization. No unresolved
  important cash-slice finding; the existing comment failure remains deferred.
- No full Python suite, independent custodian reconciliation or operating cash
  financial acceptance is claimed. Existing Starlette/httpx deprecation and
  browser environment colour warnings were not hidden.

### Initial local activation — 25 October (before standard inclusion)

The user explicitly approved migration 99 and API 8001 restart. Preflight verified
the configured local database at `20261023_98`; Alembic applied only target
`20261024_99`. Read-back confirmed the new head and four cash-owner columns across
attribution/review items. API **8001** restarted successfully, `/health` returned
200, and live OpenAPI exposes `includeCashBalances` default false. Frontend
**3001** returned 200. No other app ports were stopped or restarted.

A read-only before/after comparison of retained FCAGF attempt
`01a16978-0f5b-7214-8926-5d8a08b20e46` confirmed its financial summary is identical.
No operating balance uploads, trade bookings/cancellations, permission changes,
valuation calculations or publications were performed. A post-migration shell
quoting error affected only the first verification command; the migration was
already applied and was independently read back before API restart.

### Standard inclusion follow-up — 25 October

The user explicitly rejected opt-out/compatibility branches. The
[follow-up plan](../superpowers/plans/2026-10-25-standard-cash-pnl.md) removes the
switch at every boundary rather than just checking it by default. Missing cash
source proof on an obsolete result still requires recalculation; missing balance
entries on a newly assessed result do **not** block publication. Newly supplied or
corrected cash after staging still makes that staging stale. These are distinct
conditions, not a missing-data publication veto.

No physical history purge is needed: immutable old rows can remain as retained
evidence without an opt-out adapter or permission bypass. No new migration is
required. Focused final verification and API restart are recorded in the plan.

Follow-up verification: **149 focused Python tests, 97 valuation UI tests and six
isolated browser journeys passed**. TypeScript, OpenAPI and generated-contract
checks passed. The obsolete retry test was RED → GREEN; missing-cash publication
passes for both no supplied balances and partially supplied dates. Final UI smoke:
18 passed. The known unrelated schema-comment test is documented separately; no
full-suite claim is made.

API 8001 is restarted and healthy; live OpenAPI has no cash exclusion property.
UI 3001 returns 200. No new migration or operating balance/trade/valuation write,
publication, permission change or history purge was performed. Earlier activation
and verification paragraphs above describe the initial opt-in stage, not today's
contract. Review was by the author, not an independent financial sign-off.

The focused run also exposed two test issues: presentation legitimately adds
display-only fields, and deleting all observations on a date can violate retained
synthetic evidence. Assertions now compare unchanged financial/evidence fields;
the missing-calendar test asks beyond its own calendar instead of deleting shared
history. No product calculation or financial guard was relaxed.

## Coverage correction verification — 25 October

The user rejected historical account/currency presence as a continuing upload
expectation. Four native regressions and the obsolete account-inventory UI text
failed before correction. **43 focused database tests and 78 UI tests passed**;
TypeScript and whitespace checks passed. Actual one-sided date gaps and opening
snapshot corrections still retain their existing disclosure/publication controls.
No full suite or new browser journey was run for this bounded follow-up.

API 8001 restarted healthy; UI 3001 returned 200. Read-only selection for FCAGF's
19–20 October window confirms five supplied scopes, ten snapshots and no incomplete
pairs. No operating financial calculation/write, migration or historical evidence
rewrite was performed. New calculations use corrected coverage; previous results
retain their frozen evidence.

## Research and applicability

Checked 24 October: [IBKR cash reporting](https://www.interactivebrokers.co.uk/en/?f=38845)
distinguishes cash movements, balances and translation effects. Its historical
settlement examples are not current settlement guidance. [IAS 21 overview](https://www.ifrs.org/issued-standards/list-of-standards/ias-21-the-effects-of-changes-in-foreign-exchange-rates/)
provides the currency-translation context, not a prescription for this internal
daily convention or a compliance certification. The opening/EoD convention is
the user's product choice. Existing [UI/financial presentation research](pnl-source-coverage-20261024.md#research-and-applicability)
continues to inform semantic tables, progressive evidence disclosure, exact decimal
inspection and explicit missing/zero states; browser financial arithmetic is absent.

## Remaining boundaries

Full cash stocks/NAV publication, intraday movement attribution, account closure,
independent inventory coverage, statement reconciliation, allocation to funds/share
classes and broad financial/custodian acceptance remain separate work. Accounts
and currencies are not instruments; this is not a generic polymorphic owner API.

## 25 October UI correction — calculation options

A screenshot exposed two layout defects, especially on corrected-input tickets:
the calculation form's `width:100%` input selector overrode native checkbox sizing
(reproduced as a 401px checkbox box), and option descriptions were independent
three-column grid items. Text consequently wrapped outside its column and collided.

The width rule now excludes checkboxes/radios. Each option groups its compact
checkbox, wrapping label and screen-reader-associated help; groups occupy a full
form row. Replacement context/predecessor and recalculation reason share a separate
responsive row. Values, defaults, validation, request fields and authority are
unchanged. This is presentation-only, with no backend migration/restart needed.

The new browser regression failed on oversized checkbox geometry before the fix.
It now passes on new and corrected tickets at 1400, 900 and 480px, checking label
and help bounds, no page overflow and usable toggles. The test waits for the
existing asynchronous strategy validation before requesting results. Final checks:
**96 UI tests, 6 browser journeys and TypeScript passed**. Corrected/new screenshots
were inspected; normal Next imports/configuration restored after synthetic tests.
No operating calculation, publication or financial write was performed.
