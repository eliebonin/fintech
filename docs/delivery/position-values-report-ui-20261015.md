# Position values & exposure — strategy report

**Status:** Implemented; focused tests and local browser walkthrough passed  
**Content type:** Delivery reference  
**Owner:** Valuation/operations engineering  
**Last reviewed:** 2026-10-15

## Entry point and scope

Open **Strategies → a strategy → Position values & exposure**. The existing
`view=measures` route and import surface remain compatible. This improves the
monetary-stock preview, not P&L calculation/results or published valuation.
Futures/forward market value and settlement tracking remain deliberately deferred.

The report uses date, explicit version-labelled policy and local/strategy/both
display modes. Date-basis controls are under Advanced options. Display mode changes
presentation only: strategy currency still comes from the strategy, not an arbitrary
browser-supplied currency. Existing calculation/read/trade/data authority is unchanged.

## Report and input inspection

- Compact, right-aligned monetary table grouped by instrument type. It retains
  the server's complete-population alphabetical ordering, separate listings and
  contracts, and opaque IDs only in links/technical evidence.
- Reference notional, exposure/currency legs and market value stay separate. FX
  contractual legs are not silently netted. Same-currency values are not repeated.
- Text-labelled availability: Available, Partial, Local amount only, Missing input
  or Review required. Individual unavailable amounts distinguish Not supported yet
  from Missing required input. Genuine zero remains zero.
- Important issues and maturity warnings remain visible. Inspect expands formulas,
  factors, actual price/FX dates, applied currencies, source identifiers, relevant
  frozen swap/forward conventions, accrued balance and contributing trade/movement
  links. Exact local/strategy monetary amounts and technical JSON/hash are retained
  in separate disclosures. Scan amounts use two decimal places; quantities remain exact.
- The toolbar and pagination preserve supported query context; paging/movement
  links retain the information cutoff. A new form submission intentionally requests
  a fresh preview and resets paging. Position counts describe the loaded range,
  never imply page-only amounts are full-book totals.

`reasonCode` is additive backend presentation metadata on unavailable/local-only
measures. It is derived from product support and calculation outcome, not string
matching of error prose. Available scalar response shapes remain unchanged. Human
currency codes are attached only to already-authorized selected price/FX evidence;
selection, calculation, use/display rights and source facts are not relaxed.

## Files and verification

[Report component](../../apps/ops-console/src/components/position-measures-report.tsx),
[readable inspector](../../apps/ops-console/src/components/strategy-measure-details.tsx),
[compatible import](../../apps/ops-console/src/components/strategy-measures.tsx),
[strategy route](../../apps/ops-console/src/app/strategies/%5BstrategyId%5D/page.tsx),
[metadata adapter](../../valuation/measure_inputs.py),
[component tests](../../apps/ops-console/src/components/strategy-measures.test.tsx)
and [offline status checks](../../tests/test_measure_presentation.py).

Final focused component/workspace/transport selection: **23 UI tests passed**.
Offline monetary/status selection: **37 Python tests passed**. After recovering
Docker and starting only the existing PostgreSQL container, **52 focused disposable-
database tests passed**, with one existing Starlette/httpx deprecation warning:

```powershell
.venv/Scripts/python.exe -B scripts/run_isolated_python_tests.py tests/test_measure_presentation.py tests/test_measure_inputs.py tests/test_position_measures_assurance.py tests/test_future_measure_inputs.py tests/test_fx_forward_measure_inputs.py tests/test_strategy_holdings_api.py -q -p no:cacheprovider
pnpm --filter ops-console test src/components/strategy-measures.test.tsx src/components/strategy-workspace.test.tsx src/lib/server/api-read.test.ts
pnpm typecheck:ops-console
pnpm contract:check
```

TypeScript and API-export contract checks passed. The first DB attempts timed out
before test execution because Docker/the project container were stopped; that was
environment readiness, not a waived test failure. Local API/frontend were started
on ports 8000/3000 without changing their schema or source grants. API health: 200.
The existing context guard rejects an inappropriate numeric-loopback origin; the
browser walkthrough uses canonical `http://localhost:3000` without weakening it.
No full suite, migration, operating trade/price/policy/permission write or financial
sign-off is implied. Existing calculations and Decimal amounts are unchanged.

### Local browser acceptance

Using the existing Platform Demo Tenant operations context, inspected Strat Testing
on 2026-10-08 with its explicitly synthetic, version-labelled measures policy.
The report returned eleven positions, grouped as equities and swaps. Verified
local/strategy amounts, then submitted Strategy currency mode and confirmed GBP
amounts rather than relabelled native amounts. Expanded Air Liquide's inspector:
quantity 110, unit multiplier and divisor 1, EUR price 167.940002441406,
EUR-to-GBP rate 0.847429990768, actual price/FX date 2026-10-08, source identifier,
and retained-cutoff contributing-movement link were visible.

The live portfolio has no futures or forward positions: their deferred market
value and two-leg presentation are covered by the focused tests, not claimed as
live browser acceptance. The initial exact-decimal scan view required excessive
wrapping; the populated-data follow-up below replaces that display. A preview of eleven positions took about fifty
seconds locally, including unchanged governed price/FX selection. Performance
optimization remains a follow-up; currency-mode submission currently requests a
fresh preview rather than reusing a stored result.

### Populated-data display review and fixes

Reviewed the actual eleven-position report, rather than only empty-state fixtures.
Found three presentation defects: 20-plus-digit monetary values broke across lines,
Inspect was clipped off the normal desktop scan surface, and opening its cell
expanded the entire table horizontally. Fixed these without backend changes:

- Display-only two-decimal formatting uses decimal strings and BigInt, never a
  floating-point monetary conversion. Half-away-from-zero rounding is a **project
  display convention**, not an accounting change or currency minor-unit assertion.
  Non-zero magnitudes below 0.01 show `<0.01` / `−<0.01`, not a false zero.
- Exact values remain in accessible Inspect content and hover titles. Quantities,
  selected price/rate evidence, stored values and hashes are not rounded/rewritten.
- A small client disclosure controls a full-width row immediately below each
  position. Its button exposes expanded/control state; server-rendered financial
  content is passed as React children, not recalculated in the browser. Keyboard
  Enter closes it. Opening exact evidence does not widen the table.
- Scoped padding/header wrapping makes all seven columns fit the default desktop
  content area. Small screens retain a focusable horizontally scrollable table,
  stacked controls and constrained inspection content; no columns or issues vanish.

Final follow-up verification: **33 focused UI/display tests passed**, including
large integers beyond IEEE-754 precision, signed rounding, carry, genuine zero,
tiny non-zero amounts and retained exact evidence. TypeScript passed. Existing
currency-mode tests now assert the visible scan row separately from the hidden
exact inspector, which intentionally retains both currencies. No database suite
was repeated for these presentation-only changes.

Live browser: 1280-wide desktop (1265 CSS content viewport), table 906 pixels
inside a 907-pixel scroll region; all columns visible. Expanded Air Liquide shows
exact EUR/GBP amounts, selected price/FX date and source with unchanged table width.
Both strategy-only and combined native/strategy modes were checked. At a 390-wide
override, controls stack, the table retains its own horizontal scroll region and
the expanded evidence content is constrained to 300 pixels. Restored the normal
viewport afterward. The small disclosure requires client hydration; it is not a
new valuation calculation or authority path. Browser walkthrough and final screenshot
supplement, not replace, focused tests. Existing forty-to-fifty-second preview
latency is not addressed by display changes.

Implementation additions: [exact-string display formatter](../../apps/ops-console/src/lib/measure-display.ts),
[formatter tests](../../apps/ops-console/src/lib/measure-display.test.ts),
[row disclosure](../../apps/ops-console/src/components/measure-row-disclosure.tsx).
Rechecked the primary table/details sources below for this follow-up. The UI
guidance supports scanning and optional disclosure, not our particular rounding rule.

## Tenant-one ready-to-use data setup

At the owner's follow-up request, reran the guarded
[mock input setup](../../scripts/prepare_mock_swap_measures.py), first in a
rollback rehearsal and then with `--apply`. Both completed successfully; seven
focused fixture/policy checks passed. Existing synthetic series and policy were
reused, not duplicated or overwritten. The committed setup records its normal
audit event; it does not book trades, grant user permissions or publish valuations.

Use tenant **Platform Demo Tenant**, strategy **Strat Testing**, date **2026-10-08**,
policy **MOCK ONLY — Strat Testing measures (synthetic swaps)**,
`MOCK_STRAT_TEST_MEASURES_20261015 · v1`
(`01a13fb0-4428-7e71-b5a8-dab2eb0856a3`). All eleven positions returned all three
measures AVAILABLE, including native/GBP amounts. Swap marks and index levels are
invented; equity prices and EUR/USD-to-GBP inputs reuse existing governed coverage.
This is not an all-synthetic equity feed or P&L publication acceptance.

## Source-backed UI decisions

Searched and opened primary guidance on 2026-10-15:

- [GOV.UK tables](https://design-system.service.gov.uk/components/table/): comparable
  rows/columns, captions, scoped headers and right-aligned numbers. Applied to the
  compact grouped monetary report; no claim of government-system certification.
- [GOV.UK details](https://design-system.service.gov.uk/components/details/):
  supplementary information can be disclosed on demand; important information
  should not be hidden. Applied to formulas/JSON while keeping missing-input and
  lifecycle warnings visible.
- [GOV.UK tags](https://design-system.service.gov.uk/components/tag/), including its
  February 2026 update: status labels should not look like actions. Our subdued,
  noninteractive tags retain text meaning, not colour alone.
- [GOV.UK error summary](https://design-system.service.gov.uk/components/error-summary/):
  checked for form-error presentation. This report uses browser-required date/policy
  controls and a readable API alert; it does not invent field-specific error links
  for a general service/authority error.

Product grouping, the four reason codes, native/strategy display modes and no
aggregate NAV total are project choices. No weights, new pricing engine, status
filter, client-side partial-page search or settlement accounting was added.
