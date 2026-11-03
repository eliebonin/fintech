# P&L valuation: achieved versus intended

**Status:** Completed scoped review; implementation gaps remain open  
**Content type:** Review  
**Owner:** Valuation and operations engineering  
**Last reviewed:** 2026-10-27

## Conclusion and confidence

The platform now has a governed, multi-currency **economic P&L alpha**, rather than
the original market-only demonstration. It reconstructs positions, selects governed
marks, separates economic components, retains calculation evidence and supports
reviewed publication. The frontend, services and database form a connected workflow.
The latest accrued-stock work closes an important missing interest-FX component.

It is not complete for every bookable instrument, full fund NAV, accounting or
independently signed-off production P&L. Most remaining work is coverage consistency,
source-change assessment and representative acceptance, alongside explicit product
extensions. A new calculation foundation is not indicated by this review.

Reviewed the working checkout on `codex/pnl-ops-review`, HEAD `1b9142d`, including
substantial uncommitted work. Traceability covers the core paths named below and
representative numerical/integration/UI assertions, not every repository line or
every possible portfolio. No operating database inspection, external data ingestion,
financial run, publication, schema change or source-code fix was performed here.
Local activation through migration 101 is evidence from the preceding delivery,
not a new database verification by this review.

## Original intent and delivery

| Intended outcome | Current delivery | Remaining boundary |
| --- | --- | --- |
| Relevant positions and their trades | Tenant/strategy reconstruction with signed quantities, compatible economic buckets, historical corrections and no 1,000-trade cap | Full histories still materialize; no tax/FIFO or cross-listing netting |
| T/T−1 marks and appropriate FX | Frozen policy/version, selected observation dates, information availability, calendar evidence and trade-price-currency to reporting-currency FX | Direct or explicitly permitted inverse pairs; no silent triangulation or interchangeable fixings |
| New trades and closed positions contribute correctly | Signed execution bridge preserves T P&L on closure and execution-to-close P&L on new trades; zero boundaries need no market mark | Later-effective cancellation is not a substitute for economic termination |
| Fund NAV availability is respected | Canonical NAV identity, actual NAV date, source availability and explicit date/freshness rules | No invented T NAV before it is available; requires properly configured sources/calendars |
| Price, FX and economic P&L remain distinguishable | PRICE, FX and interaction components; daily interest, accrued-stock FX, explicit dividends/resets/costs and cash FX | Recorded components do not prove every economic event due was supplied |
| Cash snapshots are separate from trades | Exact-date account/currency snapshots, no daily unwind or generated countercash; opening balance × daily FX movement | No intraday movement-time attribution or cash-stock NAV; missing snapshots remain omitted, not zero |
| Bond daily interest and accrued stocks are separate | Typed daily earnings; reconstructed/anchored stocks; actual receipts reduce stock, not earned income; unpaid receivable can survive sale | No accrual generator, automatic entitlement or bank reconciliation; reporting-stock presentation incomplete |
| Full bond schedule | Versioned typed coupon/principal rows and separate actual coupon-payment history | Explicit sourced dates; no general schedule generator, automatic principal payment confirmation or DCF engine |
| Lifecycle closes exposure while payment stays separate | Plain bond redemption and deliverable-forward maturity produce retained closure trades with T economics | Broader option/futures/swap lifecycle and notification dashboard remain incomplete |
| Staging, amendment, publication | Immutable versions, controlled component amendments, independent review, governed self-publication exception and supersession | New source calculations do not automatically reapply old manual adjustments |
| Ops can understand and rerun a calculation manually | Input/Results/History; report subtabs, readable instruments/types, source coverage, position filters/pagination, collapsible exact-input inspector and logs | Some new warnings are not routed into Attention; complete/partial signals are not fully unified |
| Reproducible evidence and controlled release | Retained ledger/input/selection evidence, exact decimals, current strategy and dataset-display controls | Source-health CURRENT has a bounded meaning; broader source revision fan-out remains open |

The [methodology matrix](../../architecture/market-data-and-valuation/valuation-methodology.md)
owns formulas and product boundaries. [F36–F40](../../product/features/valuation-and-pnl.md)
remain ALPHA/PARTIAL; booking readiness and position-measure previews are separate capabilities.

## Backend: economics actually supported

The live entry is [service.calculate_position](../../../valuation/service.py),
using [position reconstruction](../../../positions/reconstruction.py) and
[attribute_projection](../../../valuation/position_calculation.py). The central
bridge is closing value minus opening value minus signed execution value. It
separates price, opening-exposure FX and interaction, using frozen multiplier and
quote divisor once. Foreign multi-day requests sum daily bridges so each trade
uses its own economic day's end FX.

| Product | Live daily P&L | Important qualification |
| --- | --- | --- |
| Equities / ETFs | Yes, compatible as-traded marks and reviewed basic share ratios | No general merger, spinoff, rights or entitlement engine |
| Funds | Yes, native canonical NAV | Availability/date rules are explicit; not every fund convention is inferred |
| AMCs | Yes, supplied unit/percentage quotations | Native AMC remains distinct from FUND; no automatic funding/fee model |
| Plain bonds | Yes, clean marks, normalized executions, supplied interest and available accrued-stock FX | Dirty market marks still require supported normalization and are currently blocked in this P&L path; the monetary preview has a different dirty-first rule |
| Deliverable FX forwards | Yes, outright-rate differences and booked maturity closure | Undiscounted rate-based attribution, not a general discounted contract-pricing model |
| Generic swaps | Yes, supplied whole-swap marks, including zero/negative marks | Do not apply leverage again; funding/reset model and automatic reset reconciliation absent |
| Listed vanilla options | Yes, supplied contract premium and frozen multiplier | No model price, Greeks or automatic exercise/expiry posting |
| Futures / structured notes | No live daily P&L support | Their booking or monetary-preview support must not imply this coverage |

See [capability guards](../../../valuation/product_inputs.py),
[flows](../../../valuation/flows.py), [cash inputs](../../../valuation/cash_fx_inputs.py)
and [interest inputs](../../../valuation/accruals.py).

Missing data behavior is intentionally differentiated. Default absent interest,
accrued stocks and cash snapshots produce disclosed omissions, not zeros. Explicit
strict daily-interest mode still exists. Required nonzero investment marks/FX,
invalid supplied economics, unsupported lifecycle states and access failures can
still block the whole run. “Missing data does not block” is therefore not a
universal engine guarantee. This preserves the existing policy for required market
inputs while making optional interest components non-blocking.

## Database: what is retained

| Responsibility | Main tables |
| --- | --- |
| Attempts, independent operational diagnostics | `nav.valuation_attempt`, `nav.valuation_run_event` |
| Exact attribution versions and selected population | `nav.pnl_attribution`, `nav.pnl_review_batch`, `nav.pnl_review_item`, `nav.pnl_attribution_lineage` |
| Review and amendment evidence | `nav.pnl_review_event`, `nav.pnl_amendment_request`, tenant self-publication policy and strategy revision/change records |
| Daily earned interest input | `nav.daily_accrual_input`: tenant/strategy/bond/date, typed earned amount/currency, source payload and immutable revisions |
| Derived accrued stock | `nav.accrued_interest_balance`: attempt/bond/currency/date, native opening/closing stocks, earnings, movements, actual coupon amount, FX, reporting CARRY and evidence |
| Separate dated cash stocks | `trd.cash_account`, `trd.cash_balance` |
| Expected bond cashflows and actual coupon receipt | `secm.bond_cashflow_schedule`, `secm.bond_cashflow`, `trd.bond_coupon_payment` |

Core attribution totals are typed NUMERIC; variable components and frozen proofs
remain JSONB with exact decimal strings. This is a purposeful distinction, not
financial arithmetic performed with binary floats. Attribution storage uses
explicit 12-place rounding with retained adjustments; the new derived-stock
NUMERIC columns preserve exact intermediate amounts.

Scope/FK/trigger guards, immutable records, retry identities and serialized
publication protect the supported workflow. Reviewed publication selects versions;
it does not rewrite original trades or prior financial amounts. Source revisions
lead to explicit successor calculations. The [stock-FX reference](../../architecture/market-data-and-valuation/accrued-balance-fx.md)
explains why derived output rows are not silently reused as future source inputs.

Remaining data-model boundaries are substantive: no complete cash/security/receivable/
liability NAV bridge, universal income-entitlement record or full accounting ledger.
Derived stocks expose native balances plus reporting FX/CARRY, not separate
reporting-currency opening/closing stock fields. Rich assessed inputs retain those
base amounts, so the older richer-input path and new derived path are not yet
equally convenient for dual-currency reporting.

## Frontend: Ops review is substantially delivered

[Result workspace](../../../apps/ops-console/src/features/valuation/result-workspace.tsx)
provides Breakdown, Positions & cash, Review and Logs. Source coverage discloses
recorded, missing and unassessed components. Position pages default to 25 with
50/100/all, instrument-type and Attention filters. The detail panel starts closed,
can be dismissed and presents quantity, price, FX and arithmetic inputs before
technical proofs. Current human labels are display metadata, not historical repricing.

History and result selection are filtered/count-paginated server-side across the
authorized history. Results offer readable strategies independently of calculate
rights. Per-run detail, however, still transfers complete attributions/evidence
before client-side position pagination; 25 visible rows is not a bounded payload.

The workflow distinguishes calculation completion from STAGED/PUBLISHED selection,
retains pending amendments and revalidates authority/source state on publication.
Independent review accounts for the real operator, not merely switching selected
demo identities. The small-team self-publication exception is explicit, scoped
and audited, rather than an implicit administrator bypass.

## Findings and next order

1. **Finish consistent review signals — FIX-VAL-005, P2.** Cash-only omissions do
   not set the same `pnlCompleteness=PARTIAL` flag as interest omissions. Attention
   recognizes missing daily interest and stale marks, but not missing interest FX,
   accrued-stock FX or anchor reconciliation differences. Global notices and the
   detailed stock inspector do disclose them; the missing piece is consistent
   routing, rather than missing financial proof or demonstrated wrong arithmetic.
2. **Close the known lifecycle reliability investigation — FIX-VAL-004, P2.**
   The previously reproduced intermittent bond maturity cancel/rebook rejection
   remains recorded. Static retracing confirms final verification still reuses
   the candidate's information cutoff. The timestamp explanation remains suspected;
   this review did not reproduce a new failing run or prove a wrong posted value.
3. **Broaden source-change assessment — FIX-VAL-002, P2.** Ledger, window-bounded
   cash, interest and coupon revisions are covered. A corrected market observation,
   calendar, policy or corporate-action source does not have general affected-run
   fan-out. Frozen results remain reproducible; CURRENT does not certify those
   sources are universally unchanged. Add targeted dependencies, not automatic
   rewriting or publication.
4. **Complete dual-currency stock reporting — FIX-VAL-006, P3.** Native stock/FX
   evidence is present; separately readable reporting-currency stocks remain a
   gap against the user's stated reporting requirement. A read projection from
   frozen values may suffice; duplicating all source data is not automatically needed.
5. **Retain one complete acceptance portfolio — FIX-VAL-003.** Include price/FX,
   new/closed trades, split, available fund NAV, paid/unpaid coupon, bought/sold
   accrued, cash movement, reset, amendment, publication and corrected successor.
   Independently specify expected numbers and component completeness. Then measure
   representative history/window size and concurrent review load. Daily ledger
   replay, historical accrual scans and full proof payloads remain scale risks;
   no new trade cap or loss of evidence is recommended.

Automatic accrual generation, broader derivatives/lifecycle, income entitlement,
NAV and accounting are product extensions, not fixes to pretend are already done.
The original small-team/local workflow remains intentional. Production identity
is separately gated by BACKEND-001; this review does not change that deployment boundary.

## Verification and limits

Fresh command in this review:

```powershell
./.venv/Scripts/python.exe -B -m pytest tests/test_position_reconstruction.py tests/test_valuation_methodology_matrix.py tests/test_accrued_balance_replay.py tests/test_optional_interest_fx.py tests/test_cash_fx.py tests/test_valuation_presentation.py -q -p no:cacheprovider --tb=short
```

**73 passed in 2.75 seconds.** These are offline checks, not current disposable-DB
or operating portfolio acceptance. Additional offline probes reproduced empty
Attention for new interest-FX/stock warnings and `RECORDED_COMPONENTS` despite
cash-only partial coverage, and confirmed an assessed anchor discrepancy is
retained as a warning while its value remains authoritative. No files containing
production financial data or new product tests were created for those probes.

Reviewed prior evidence separately: the [stock-FX delivery](../accrued-balance-fx-20261027.md)
records 74 scoped backend checks, 1,055 frontend checks and two isolated browser
journeys. Their retained logs confirm those counts; they were not rerun here.
Earlier reported near-agreement with the external rounded export is encouraging
but excluded accrued interest/cash FX and is not full independent reconciliation.
No full Python/frontend suite, browser walkthrough, load test or fresh database
migration/constraint execution was performed in this review.

Documentation reconciliation corrects outdated statements about accrued-stock
derivation and coupon receipts in the current methodology/register. Historical
delivery reports retain their original scope. Code findings remain open in
[FIX.md](../../../FIX.md); documentation edits do not resolve them.

## Primary guidance checked

- [GIPS Handbook for Firms, provisions 2.A.10 and 2.B.3](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/),
  accessed 27 October 2026: fixed-income earned income belongs in performance,
  accrued income belongs in portfolio values, and double counting must be avoided.
  This supports separating earned accrual from receipt; our partial economic report
  is not claimed to meet complete GIPS performance/NAV requirements.
- [NZ IAS 21, January 2025 text, paragraphs 23 and 28](https://standards.xrb.govt.nz/standards-navigator/nz-ias-21/),
  accessed 27 October 2026: monetary items use closing-rate translation and exchange
  differences generally enter profit or loss, subject to the standard's exceptions.
  This supports assessing foreign-currency accrued receivables. Our opening-stock/
  closing-movement attribution convention is a project choice, not a prescribed
  universal accounting decomposition.
- [SEC rule 2a-5 compliance guide, 26 February 2021](https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/good-faith-determinations-fair-value-small-entity-compliance-guide),
  accessed 27 October 2026: valuation methodology testing, pricing-service oversight
  and retained records are useful engineering benchmarks. Its US registered-fund
  scope is not automatically a legal obligation for this personal project. It
  supports prioritizing independent numerical acceptance over additional UI polish.

The implementation-specific priorities above are reviewer conclusions from source
and tests, not claims that these sources mandate this schema or software design.
