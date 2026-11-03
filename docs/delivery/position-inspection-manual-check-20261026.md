# Position inspection: business inputs before technical proof

Naming follow-up: the later [shared instrument display policy](../architecture/security-master/instrument-display.md)
replaces the bond-only naming rule below. Earlier verification counts remain dated evidence.

**Status:** Implemented; verification below.  
**Content type:** Delivery record  
**Owner:** Valuation / Operations console  
**Last reviewed:** 2026-10-26

## Delivered workflow

**Inspect position** now leads with **Reproduce this P&L**, before components or
technical material:

- Side-by-side opening/closing signed quantities, valuation prices or contract
  rates, actual price dates, converted FX rates, actual FX dates and retained
  reporting-currency boundary values.
- Explicit FX direction: reporting-currency units per one price-currency unit.
  The price currency comes from frozen trade-price currency, not instrument currency.
- Frozen quantity unit, unit multiplier and quote divisor. Percentage bonds use
  clean prices per 100 nominal; option premium multipliers apply once. Whole-swap
  marks do not receive another reference-notional/leverage multiplier.
- The formula, retained signed execution value and recorded price/FX P&L. Dated
  trades show signed quantity, execution price actually used and the economic
  day's closing FX. Sales retain negative signs.
- Intermediate dated prices/FX for multi-day evidence and reviewed share-ratio
  quantity changes separately from trades. No invented trade-level P&L.

Sources, applied rules, IDs, original quantities/executions, ledger links, split
proof, exact storage rounding and full JSON remain under initially collapsed
**Sources, applied rules and technical proof**. Supplied interest and omission
notices stay visible below the worksheet. Existing inspector close/focus return,
type/search filters, pagination and report tabs are unchanged.

## Financial and security boundaries

This reads existing frozen fields; it is not another valuation engine or a browser
calculator. Exact decimals never pass through JavaScript floating point. Retained
storage rounding can explain tiny differences between hand-calculated unrounded
values and stored results.

For the funded-security bridge:

`boundary value = signed quantity × unit multiplier ÷ quote divisor × price × FX`

`price/FX P&L = closing value − opening value − signed execution value`

FX-forward boundary values instead use quantity times **contract rate minus frozen
agreed rate**, with FX. This is the existing undiscounted rate-difference basis,
not gross notional or model MTM. Maturity spot suggestions are not substituted
for contract or actual booked execution rates.

Zero exposure needs no mark: the price is shown as not needed, not zero. A new
holding uses the closing-FX convention and actual execution price, not an invented
opening market mark. Identity FX appears only when frozen currencies explicitly
match. Foreign FX uses the recorded converted rate, including inverse conversion,
not the provider's unconverted quote. Conflicting candidates are explicit.

Foreign multi-day runs sum daily bridges. The worksheet exposes dated inputs and
executions, not a fabricated final-rate reconstruction or invented daily quantity
states. Apply dated trades and share adjustments; do not translate every execution
at the last day's FX. Missing historical fields stay **Not recorded**, without
backfilling from current terms or market data.

Flow-only rows show dated local amounts, currency, FX and recognition role rather
than fictitious shares or marks. Payment-only flows create no new income. Interest,
resets and costs remain separate components; the main bridge checks price/FX P&L,
not complete fund NAV. DISPLAY denial still hides the financial inspector.

No API, schema, financial calculation, rights, authority, publication rule or frozen
result changed. No operating trades, inputs or valuations were written. This is a
frontend hot-reload change; no migration or backend restart is required.

## Readability follow-up

Quantities (including nominal amounts), period executions and reviewed before/after
quantities use comma thousands grouping through the existing exact decimal-string
formatter. Retained boundary/execution/P&L and explicit flow amounts use the same
grouping; signs, fractional digits and trailing zeros are preserved without Number
conversion. Prices, FX, multipliers and quote divisors retain their original text.
Frozen JSON remains unchanged and grouped worksheet values retain raw-value titles.

The text close button is replaced with a discreet 32px pastel-red × button. Its
accessible name/title remains **Close position details**; the decorative glyph is
hidden from screen readers. Hover/focus states remain clear, keyboard activation
still closes the inspector and focus returns to the originating Inspect action.
This follow-up passed 25 focused tests, TypeScript, all 1,042 frontend tests and
13 isolated Edge report journeys. Browser assertions cover comma-grouped large
quantities, unchanged prices/FX, pastel styling and keyboard close/focus return;
the updated inspector screenshot was visually reviewed. Stored data is unchanged.

### Bond business identifiers

Bond labels now prefer a currently valid governed ISIN over a listing ticker or
internal import code. The listing's own ISIN is preferred; otherwise its canonical
parent supplies it. Within each reference, primary then latest-valid-from then
identifier value gives deterministic display selection. Expired/future assignments
are excluded using the shared UTC governance date. Missing ISIN keeps the existing
ticker/internal-code fallback; equities keep their existing ticker display.

Identifiers are loaded in bulk only for already-visible bond references/parents;
there is no per-position query or import-code pattern in product logic. This is
current accessible naming metadata, not rewritten frozen economic evidence.
Read-only diagnosis confirmed the affected bond already had ISIN GB00BSGRV302;
its current label is **UKTB 0 04/05/27 · GB00BSGRV302**. No identifier was invented
or added to the operating database.

27 focused disposable-PostgreSQL presentation/history tests passed, including
validity/primary preference, parent-listing resolution, ticker/fallback preservation,
private-parent visibility and unchanged financial evidence. The runner reported
one existing Starlette/httpx deprecation warning. API 8001 was restarted and
`/health` returned `status: ok`; the actual label was checked in a read-only
transaction. Refresh the selected result; no valuation recalculation is needed.

## Verification

- Initial tests reproduced the missing business-input section.
- 27 focused component/financial-presentation tests and TypeScript passed.
- 1,040 frontend tests in 211 files passed.
- 13 isolated Edge report journeys passed, including exact worksheet inputs,
  default-collapsed proof, keyboard access, responsive layout, console guards,
  existing Ops review/publication and DISPLAY restrictions. A captured desktop
  inspector was visually reviewed. A small numeric-column alignment follow-up
  also passed the focused inspector browser journey, including explicit alignment
  assertions for both boundary columns.
- No full Python suite, operating financial reconciliation or full NAV sign-off
  is implied. No stored result was recalculated or published.

Implementation: [worksheet](../../apps/ops-console/src/features/valuation/position-calculation.tsx),
[inspector](../../apps/ops-console/src/features/valuation/result-workspace.tsx),
[styles](../../apps/ops-console/src/app/valuation-workspace.css).
Tests: [input rendering](../../apps/ops-console/src/features/valuation/position-calculation.test.tsx),
[report](../../apps/ops-console/src/features/valuation/result-workspace.test.tsx),
[isolated browser journeys](../../apps/ops-console/browser-tests/pnl-ops.spec.ts).
Methodology: [common bridge and product boundaries](../architecture/market-data-and-valuation/valuation-methodology.md).
