# Position monetary measures

Status: local alpha, read-only preview. Scope approved in discussion on 15 October
2026: monetary measures first; **no weights, NAV division or P&L changes**. Legacy
legacy_core code informed business intent only; no implementation was copied.

## Workflow and authority

Strategy → **Measures** → choose date, executed/valuation-recognised date basis
and an explicit versioned pricing policy → Preview measures. The API is
`GET /v1/strategies/{strategy_id}/measures`. The strategy's base currency is the
conversion target. Quantities use full retained history, reviewed share ratios
and correction state; type/name ordering precedes 25-row pagination. Only the
requested page is priced; it is not a portfolio total or coverage certification.

Backend requires same-strategy STRATEGY_READ, TRADE_READ, VALUATION_READ and
VALUATION_RUN, plus MARKET_DATA_READ. Existing module gates remain. A user able
to read published valuations does not thereby gain calculation authority.
Every displayed market input also needs current DISPLAY/reporting rights,
independently of the VALUATION-use grant used for selection. Tenant and scoped
policy checks precede calculation. No group grants or entitlements are provisioned.

This is `PREVIEW_NOT_PUBLISHED`, not a staged/official valuation. There are no
new tables, migrations, publication actions or operating financial writes. The
response retains references to existing immutable bookings, observations, policy
and accrual revisions, plus selection evidence, dates, FX, formula version and an
evidence hash. The preview itself is not persisted as an immutable financial run;
save/stage/publication for monetary measures is separate future scope. Request
information cutoffs constrain evidence; current reference/access governance is
still evaluated. This is not a certified historical-access replay.

## Measures and formulas

All computations use Decimal and exact quotation arithmetic, never browser
floating point. Native amounts and strategy-currency equivalents are separate.
Each result is AVAILABLE, LOCAL_ONLY (FX unavailable) or UNAVAILABLE. A real zero
or negative swap mark is not confused with missing data. No trade-price fallback,
silent latest-date carry, FX fixing substitution or missing-accrual zero is used.

### Equities, ETFs and funds

As a deliberate reporting convention, reference notional, economic exposure and
market value all equal:

`signed quantity × instrument price/NAV × unit multiplier ÷ quote factor`.

This is not a leveraged ETF/fund look-through measure or contractual principal.
Funds use the canonical share-class NAV with policy-selected availability/dates;
fund listing unit normalization beyond native factors of one remains blocked.
Actual observation date, requested date and information cutoff remain separate.

### Plain bonds

Reference notional and face exposure equal signed outstanding face amount. A
unit-booked bond requires explicit saved denomination; non-per-100 quotes are not
supported. Full market value prefers an eligible **DIRTY** price under the selected
policy. Otherwise it uses eligible **CLEAN** value plus assessed accrued balance.
`BOND_PRICE_TYPE` dimensions constrain candidates before resolution; provider
priority, rights, timing and pinned-series rules are never bypassed to find dirty
data. A policy pinned to clean does not gain access to a different dirty series.

- Dirty value = face × dirty quote ÷ quote factor. No second accrual addition.
- Clean value = face × clean quote ÷ quote factor.
- Full dirty value = clean value + signed position accrued-interest balance.

Fallback requires the exact-date latest eligible accrual revision, matching
currency, an assessed eligible nominal matching the position, and a valid balance
bridge. Daily earned interest and trade-date bought/sold accrual are **not** the
current balance. A single canonical position is supported for that balance;
multiple listings/currencies require an explicit allocation design rather than
duplicating a canonical accrued stock. Clean-only value remains in evidence when
full dirty value is unavailable. This does not change daily P&L's clean-price/
daily-earned-interest treatment or existing P&L dirty-mark restrictions.

Hand checks: 100,000 face at clean 98 plus 1,200 balance gives 99,200. A dirty quote
99.2 gives 99,200 directly, even if the separate balance also exists.

### Bounded delta-one index swaps

Uses one compatible frozen generic contract and native canonical index units.
One booked unit is one currency-per-index-point unit; no additional multiplier
is inferred. Other underlying unit/corporate-action conventions, autocalls and
interim-reset/payment swaps are not enabled. Missing native currency or mixed
saved terms blocks the contract instead of guessing. Leverage and receive/pay
orientation come from approved terms; signed ledger quantity reflects BUY/SELL.

- Reference notional = signed units × contractual notional per unit, before leverage.
- Underlying-equivalent exposure = signed units × current index level × leverage
  × performance orientation (+1 receive, −1 pay).
- MTM = signed units × **whole-swap** quote ÷ quote factor. Funding, orientation and
  leverage are already in that quote and are not applied again.

NOMINAL contracts can produce reference notional and MTM; underlying exposure is
explicitly unavailable without equivalent units/reset reference inputs. Whole-swap
source definitions must identify `SWAP_PRICE_BASIS=WHOLE_SWAP_MTM_PER_UNIT` or
`WHOLE_SWAP_MTM_PER_NOTIONAL` plus an equal numeric `QUOTE_FACTOR`. Native index
levels require governed `INDEX_LEVEL` series/value/measure/basis semantics (or a
compatible ordinary price series), not a swap mark reused as an index level.

The selected policy must explicitly cover canonical swaps/indices with eligible
timed marks and sealed calendars. A listing SESSION_CLOSE rule cannot price a
canonical OTC contract by assumption. Policies requesting AS_TRADED share-price
normalization are not suitable for negative whole-swap MTM; use explicit native
RAW whole-swap semantics instead. Reporting FX is resolved for each measure's
actual currency; no currency label is changed after choosing FX.

Hand check: 25,000 units, 8,250 reference/unit, index 9,000, leverage 1.5 and mark
20/unit gives reference 206.25m, exposure 337.5m and MTM 0.5m. A −20 mark gives
−0.5m MTM. These are not model Greeks, counterparty exposure or regulatory risk.

## Local activation and verification

- API restarted with the additive endpoint; existing P&L/publication untouched.
- Focused backend run: 49 passed across measures, holdings/action scopes, existing
  valuation selection and resolver regressions. Existing Starlette/httpx and
  SQLAlchemy deprecation warnings remain; full suite not run.
- Focused UI/read-deadline tests: 15 passed; TypeScript and OpenAPI freshness passed.
  Only explicit measure reads have a 60-second maximum; ordinary reads retain
  their existing deadline. Loading text makes the calculation wait visible.
- Live read of Strat Testing for **2026-10-07**, FLEXIBLE_EOD v4
  `01a13ec5-72e8-7a80-b62e-0346389dae1b`: all three amounts available for nine
  equities, with EUR→GBP conversion. The two mock index swaps show reference
  notional but missing swap/index policy coverage; SPX also lacks matching USD→GBP
  FX policy coverage. Those gaps were not hidden by changing policies/licences.
- The swap integration fixture uses normal creation materialization and booking
  on its owned test transaction, then real governed series/selection. It verifies
  leverage once, native index levels, negative MTM and quote-factor mismatch.
- The bond integration fixture verifies clean+balance, dirty preference and no
  duplicate accrual. Missing price/FX tests prove unavailable/local-only states.
- Authenticated live-page HTTP smoke returned 200 with the Measures heading,
  preview warning, equity results and unavailable-input states rendered. The
  temporary test session was revoked successfully; browser context was untouched.
  This verifies server rendering, not visual-browser layout acceptance.

Current limitations: no weights, totals/full NAV, stored monetary-measure review
batches, interim reset engine, autocall/option/forward measures, futures contract
MTM, bond balance
allocation across listings or broad large-book performance sign-off. No manual
visual browser acceptance or independent financial reconciliation is claimed.

Subsequent approved [futures exposure slice](future-position-measures-20261015.md)
adds current notional/exposure for linear cash-settled index futures. It deliberately
does not assign full notional or an assumed zero to the contract-MTM column.
Original pre-extension findings and acceptance figures below remain historical.

## Pre-extension readiness check

Reviewed again on 15 October before futures, FX-forward and option measures.
This was a diagnostic review, not authorization to change operating policies or
licensing grants. No production calculation code, running service configuration,
operating financial records or entitlement was changed.

Two open defects prevent a clean monetary-preview sign-off:

1. **MEASURES-001 — share-unit/price compatibility.** Reviewed split quantities
   are replayed, but the adapter omits P&L's `assert_native_mark_units` check.
   An explicitly permitted stale pre-action RAW price can therefore multiply
   post-action quantity. Require compatible post-action prices or withhold the
   measure with an explanation; freshness alone is not sufficient evidence.
2. **MEASURES-002 — fund-share-class recognition.** Frozen `FUND_SHARE_CLASS`
   bookings are not normalized to `FUND` by the holdings adapter, unlike the P&L
   adapter. They do not reach canonical NAV selection. Claimed fund preview support
   above is the intended branch, not complete acceptance for normal share classes.
   Validate both canonical and listed share classes when fixing this mapping.

See [open findings](../../FIX.md) and
[focused reproductions](../../tests/test_position_measures_assurance.py).
Known defects are strict expected failures, not passing checks. Their tests should
be made ordinary passing regressions as part of remediation.
An additional two-case `--runxfail` diagnostic exposed the precise assertions:
the split case returns quantity 20 valued at 200 using the pre-action 2026-09-29
price, and the fund case reports `FUND_SHARE_CLASS` rather than `FUND`. Both fail
as expected; these are confirmed application defects, not fixture setup errors.

Fresh isolated run: **50 passed, 2 expected failures**, with one pre-existing
framework deprecation warning. Coverage includes direct GBP→USD for all three
measures, native/reporting signs for shorts, calculation-versus-display rights,
blocking duplicated canonical accrued balance across listings, existing dirty /
clean-plus-balance cases, index-swap leverage/negative MTM/factor semantics,
scoped API reads, share replay, FX bridge and bond maturity/correction regressions.
Focused presentation/navigation/read-timeout checks: **15 passed**. No full suite,
new visual-browser acceptance or independent financial sign-off is claimed.
The fund NAV/late-revision expectations in the new end-to-end fund preview test
remain pending behind its failing classification assertion.

Read-only live check reconfirmed Strat Testing on 2026-10-07 / FLEXIBLE_EOD v4:
nine equities return equal native measures and GBP equivalents. Both mock swaps
still lack matching swap-mark and INDEX_LEVEL policy rules; visible underlying
index data also lacks valuation-use coverage, and SPX lacks matching USD→GBP FX
policy coverage. These are setup/rights gaps, separate from the two code defects.
No grant is fabricated or relaxed to obtain a result.

Recommended order: repair native-unit safety, normalize/accept fund share classes,
then configure explicitly permitted mock-swap marks, index and FX selection and
reconcile the live SPX/UKX amounts before introducing more product formulas.
Interim resets, multiple-listing bond accrual allocation and persisted official
measure runs remain the earlier declared boundaries, not newly solved features.

## Remediation and local acceptance

The user authorized fixing all three readiness findings after best-practice and
md-document review. The diagnostic results above are historical; the following
records the subsequent implementation, not a rewrite of that evidence.

### Code fixes

- Measure selection now invokes the existing native-mark/unit guard. A permitted
  pre-split RAW mark cannot multiply reviewed post-split quantity. The row explains
  why its amounts are unavailable; a compatible same/post-action price succeeds.
- The holdings adapter maps frozen FUND_SHARE_CLASS to FUND. Fund NAV selection
  requires a unique canonical ID from frozen BOOKED evidence, not a current
  listing or an optional trade reference column. Canonical and listed share-class
  cases pass, including prior NAV date and exclusion of a later-received revision.
- These do not weaken source DISPLAY/VALUATION checks, scoped strategy actions,
  sealed calendars or explicit freshness. They do not change P&L/publication.

### Mock-only data and policy

[Guarded preparation](../../scripts/prepare_mock_swap_measures.py) is local-only,
checks exact strategy/mock IDs and artifact hash, authorizes the actor, and uses
an atomic transaction. Default execution rehearses and rolls back. `--apply`
commits only additive setup after all 11 preview positions pass and both swaps
reconcile independently to the retained fixture's quantities, levels, marks and
selected FX observations. It is not a general provider or production pricer.

- Added the retained **invented** SPX/UKX index paths as two INDEX_LEVEL streams
  under existing tenant-owned mock dataset rights, with the original source hash
  and actual new recording/publication time. No public index grant was invented.
- Created **MOCK ONLY — Strat Testing measures (synthetic swaps)**,
  `MOCK_STRAT_TEST_MEASURES_20261015` **v1**, policy UUID
  `01a13fb0-4428-7e71-b5a8-dab2eb0856a3`, scoped to Strat Testing.
  It copies base equity/EUR-FX semantics and pins exact mock mark/index streams
  plus the existing Yahoo USD→GBP UK-cutoff series. Each mock uses its explicit
  US/London close cut and a sealed 2026 calendar. No silent prior-day allowance.
- Policy validity **2026-10-08 through 2026-12-31** follows existing USD→GBP
  coverage and the selected calendar year. Historical USD→GBP samples for
  October 7 are not valuation-entitled by this change. Original FLEXIBLE_EOD v4,
  third-party grants, trades, cash and staged/published valuations are unchanged.
- The retained synthetic history ends October 14; this setup does not invent
  observations after that date. Earlier calendars are not extended by creating
  an index stream. Inputs must independently cover every requested date.

### Verification and use

Use Strategy → **Measures**, **Strat Testing**, date **2026-10-08**, and the
MOCK ONLY policy above. The API was restarted and live readback returned
`PREVIEW_NOT_PUBLISHED`, **11 positions, all measures AVAILABLE**, in native and
GBP currency. No NAV/P&L result was calculated or published.

Independent checks on October 8:

- SPX: reference USD 580,000,000; underlying exposure USD 525,040,974.669;
  MTM USD −87,540,652.737. Reporting FX is 0.756049990654 GBP per USD; each
  measure's GBP equivalent was checked against the selected stored observation.
- UKX: reference GBP 206,250,000; leveraged exposure GBP 334,903,156.969875;
  MTM GBP 17,598,371.39775. Identity GBP conversion requires no FX observation.

Both ordinary defect regressions failed before their fixes. Final affected
disposable-DB run: **111 passed, no expected failures**, with nine pre-existing
framework/SQLAlchemy deprecation warnings. It covers measures, holdings, scoped
API, split replay, FX, bond redemption and existing resolver/P&L selection. Mock
setup validation/policy tests are included. A post-apply rollback rehearsal reused
the same policy and index series and produced the same amounts.
**15 frontend checks**, TypeScript and API contract freshness passed. The full
suite was deliberately not run; independent custodian reconciliation and manual
visual-browser acceptance are not claimed. No migration or permission grant.
Authenticated live-page HTTP acceptance returned 200 with the Measures heading,
preview warning, new MOCK ONLY policy, equity rows and swap monetary amounts.
The temporary test session was revoked; the user's browser context was untouched.

### Best-practice check informing the fixes

Online primary sources reviewed 15 October 2026:

- [SEC Investor.gov stock-split glossary](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock-split)
  illustrates the corresponding change in share count and per-share price.
  Our engineering application is to check the actual price's unit/date basis
  after quantity replay, rather than treating freshness as compatibility proof.
- [SEC fund/ETF bulletin, 29 April 2025](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/characteristics-mutual-funds-exchange-traded-funds)
  distinguishes share classes and NAV from ETF market pricing. Canonical
  share-class identity and explicit publication availability are our implementation
  choices; this US educational source does not prescribe our database taxonomy
  or a universal fund lag.
- [CME market-data policy education](https://www.cmegroup.com/market-data/license-data/market-data-policy-education-center.html)
  distinguishes display/non-display activities and entitlement management.
  We retain activity/source scope instead of expanding third-party permission to
  make a test pass. CME guidance is illustrative, not Yahoo permission or legal
  clearance. Existing owned mock rights cover only our invented values.

md-document reconciled [AGENTS](../../AGENTS.md), [KNOWLEDGE](../../KNOWLEDGE.md)
and [FIX](../../FIX.md); resolved finding IDs and original reproductions remain
readable. These are scoped alpha fixes, not an exhaustive repository sign-off.

## Sources and implementation

The [FINOS CDM product model](https://cdm.finos.org/docs/product-model/) informed
distinct quantity/notional/price units; its [event model](https://cdm.finos.org/docs/event-model/)
separates reset state from cash transfers. [BIS, December 2025](https://www.bis.org/publications/qr-202512/international-finance-through-lens-bis-statistics-derivatives-markets)
distinguishes derivative notional and replacement market value.
[CESR/ESMA 10-788](https://www.esma.europa.eu/sites/default/files/library/2015/11/10_788.pdf)
uses underlying market value for basic TRS commitment conversion; this preview
does not claim to implement the complete regulatory method. Reviewed online on
2026-10-15; these sources do not certify the alpha or dictate our cash-security
equal-measure convention.

- [Arithmetic](../../valuation/position_measures.py), [governed adapter](../../valuation/measure_inputs.py).
- [Strategy endpoint](../../apps/reference_api/strategy_workspace.py), [UI](../../apps/ops-console/src/components/strategy-measures.tsx).
- [Numerical tests](../../tests/test_position_measures.py), [input integration](../../tests/test_measure_inputs.py), [HTTP scopes](../../tests/test_strategy_holdings_api.py).
- [Implementation plan and ledger](../superpowers/plans/2026-10-15-position-measures.md).
