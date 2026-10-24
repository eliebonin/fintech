# FCAGF private reconciliation import — 23 October 2026

**Classification:** One-off external CSV reconciliation exercise, not product
functionality. Scripts and tests are isolated under
[optional tooling](../../tooling/reconciliation_csv/README.md). Retained data and
audit evidence are unchanged; this record does not establish a supported upload
format or processor.

**Status:** PARTIAL — all 78 investments, 38 dated RESET flows, 121 cash snapshots, 99 daily-interest inputs, 4,620 FX observations and all 884 market-price observations posted; reconciliation and valuation acceptance remain pending  
**Content type:** Delivery record and operator ledger  
**Owner:** Data operations  
**Last reviewed:** 2026-10-23

## Scope and authority

The owner asked to import a regenerated private export into a new tenant-one
strategy for real-world reconciliation. This is a local operator exercise, not
delivery of all twelve public file-import processors. No valuation is published,
permission granted, existing operating trade changed or production service used.
Original customer CSVs and runtime receipts stay in ignored private logs, not Git.

## Plan and progress

1. **Done:** validate and retain the ten files and manifest, create source-scoped
   strategy identity, add required SGD currency, retain confirmed company alias.
2. **Partial:** normalize instrument terms through existing typed proposals and
   approval services. Seven zero-coupon bonds and three researched conventional
   gilts materialized as private instruments. Original incomplete requests retained
   unchanged, rejected as superseded by separately reviewed requests. Thirteen
   swaps, thirteen performance indices, two rate identities, one SPX reference
   and one source-normalized option subsequently created. Native FCGMS AMC now created;
   retained forward prices are owner-confirmed GBP per USD; native quantity/pair mapping remains pending.
3. **Partial:** source identities, privately scoped party placeholders and normal
   fractional-convention approvals prepared; initial batch posted 43 investment
   trades. Nineteen further swaps hit derived-reference precision restrictions;
   correction and retry evidence recorded below. Remaining instrument adapters
   are distinct from the 193 RESET dated flows, not cumulative investments.
4. **Pending:** tenant-provided prices/FX, exact-date separate account balances,
   daily earned interest, rights/basis/timing review and reconciliation reports.
5. **Pending:** run supported valuation cases and compare independent expected
   numbers. Swap/option booking availability is not valuation support.

## Applied source rulings

- Strategy currency comes from source strategy metadata: GBP. Do not infer it from
  a trade, instrument or price.
- Exclude source trade `202610200000-J2508747` as explicitly requested. Its original
  file backup remains outside the repository. Do not classify every short forward
  as cash using a lifespan heuristic.
- RESET rows are date-specific flows, never cumulative position trades.
- Source instrument `1857` (FCGMS) is an AMC. Ignore its stray bond-terms row;
  do not approve it as a zero-coupon bond or silently treat AMC as a plain fund.
- DIVER OTC instruments represent delta-one swaps. Preserve funding, leverage,
  unit/notional and return-profile differences; the source label is not another
  native economic instrument class.
- Company `21` is owner-named Northern Trust. Retained as an operational reference,
  **not** a verified legal entity/LEI. The other source company IDs have no supported
  name mapping; do not fabricate bank names or LEIs.
- NT and IB/Misc are separate cash accounts/streams, not amounts to sum. IB/Misc
  includes Interactive Brokers or other venues, reported by Northern Trust; this
  does not prove the maintaining legal entity for every balance. NT derivatives
  wash-account balances also remain separate from ordinary USD balances.
- Source bond price `0.99809` means 99.809% of nominal, explicitly confirmed by
  the owner. Keep nominal quantity unchanged and multiply trade/market price by
  100 for percentage-of-par quotes. `percentage_price` preserves original text,
  discloses half-even rounding to native 12 decimal places and reports whether it
  changed precision. This conversion is tested but no financial price posted yet.
- Coupon rates such as 3.75% map to native fractional 0.0375. All ten source bonds
  are CLEAN quoted. Source `par_amt=0.01` is not assumed to be our contractual bond
  unit; at initial mapping `parAmount` remained absent rather than copying an
  unexplained denomination. The subsequent bond activation below resolves this
  with DMO-backed penny transfer-unit evidence and retained term versions.

## Active local records

- Strategy: `RECON_FCAGF`, **FCAGF — imported reconciliation**, tenant one; FUND,
  GBP, observed historical start 1 September 2023. Creation used the normal
  strategy service and live strategy permissions.
- Eleven private `ing.source_payload` receipts: ten CSVs and one manifest, status
  RECEIVED. Receipt is not a claim that the file's financial rows were applied.
- Bundle SHA-256:
  `3c1d05aa6ae7bb14760547e8a8ed596f7482148606403ce8d9759a41fb428023`.
- Source counts: 271 trade rows = 78 position bookings plus 193 RESET flows;
  46 source instruments; ten actual bond term rows after AMC exclusion; 13 swaps;
  884 prices; 6,358 FX rates; 121 account balance rows; 111 daily-interest rows.
- Approved bond source IDs: `20201`, `20268`, `20328`, `20484`, `20828`, `18277`,
  `18875`. Their normal proposal/approval evidence retains the original bond file.
  Their identifiers and source proposal IDs link to tenant-private canonical nodes.
- The initially pending bond source IDs `12591`, `8064`, `8501` are now approved
  through separate DMO-reviewed requests. Their unspecified source ACT/ACT was
  enriched using the mapping and evidence below, not overwritten in the CSV.
- `8064` had conflicting maturity: detailed bond file 7 March 2027,
  main instrument file 6 April 2027. Its main label implies zero coupon while
  detailed terms say 3.75% fixed. The DMO prospectus resolves the conflict.

## Subsequent instrument batch — existing model preserved

`--products` created all thirteen source delta-one swaps with normal swap
proposals/approvals, thirteen private performance indices and private SOFR/SONIA
rate identities. Source IDs `1396` and `1048` are rate references even though the
export classified them as INDEX. No benchmark rate observations were invented.
Source swap quantities/marks were not changed, and no incomplete-terms mode,
validation relaxation or swap-P&L extension was implemented.

Mockup completion is explicit in names, contract source references, decision
reasons and `RECONCILIATION_PRODUCTS_SEEDED` audit evidence, which retains both
original swap rows and an assumption map per source instrument:

- Seven supplied notionals and all supplied leverage values retained. Missing
  contractual notional estimated from the first observed absolute booking.
- Unit contracts use **mockup reference notional 100 per unit** and compatible
  contractual units; these are seed metadata, not reconciled economic exposure.
- Missing nonzero-spread USD funding references use disclosed mockup SOFR.
  Supplied SOFR/SONIA identities and spreads remain unchanged.
- RECEIVE direction, TERMINATE-at-maturity, overnight compounding and funding
  notional basis are disclosed mockups. Payment counts inform reset/payment
  frequency assumptions, without claiming a verified contractual schedule.
- Original TR/PR/ER descriptors remain in the retained source/audit. Native
  total-performance mapping of the selected index variant is a disclosed test
  convention where descriptor mapping is incomplete, not payoff equivalence.

`--additional` created source option `20265` and a private SPX reference. The
option uses a **source-normalized mockup contract** with premium/deliverable
multiplier 1, not an assertion that these are exchange-standard SPX contract
units. This preserves the exported quantity × premium economics. Strike/type/
expiry come from the source description; European exercise, cash settlement and
21:00 UTC expiry cutoff are labelled assumptions. Availability starts at the
first observed trade, 13 August 2026: the source effective-date field incorrectly
contained the expiry date, 18 December 2026.

**AMC classification correction:** source `1857` (FCGMS) is labelled
`ACTIVELY_MANAGED_CERTIFICATE` / AMC, not ETI, fund or bond. The earlier ETI request
was an import-mapping mistake, not a reason to add an ETI catalogue type. The
guarded operator rejects that pending request through its existing decision
service, preserving its payload and decision evidence, and retains the corrected
AMC classification in the pending import result and audit. It no longer submits
an ETP proposal for an AMC, even if an ETI catalogue entry exists. No unsecured,
open-ended or accumulating terms are inferred from the AMC label.

At that correction stage a governed AMC creation workflow was missing, so the
classified item remained pending. The subsequent [native AMC delivery](amc-onboarding-20261023.md)
implements that path, not an ETP substitute, and migration 97 is now applied.
FCGMS is materialized as `ACTIVELY_MANAGED_CERTIFICATE`, native ID
`01a16852-f45d-738d-9995-6d0d5a1a523d`. Source identity/USD unit quotes are retained;
unknown optional terms stay unknown. Its source-derived issuer name is not an
invented verified legal identity. No source trade or price is posted by this step.
Option and swap creation were independent of that gap. Previously decided requests
are never rewritten; an already approved wrong mapping would require explicit
remediation rather than silent retyping.

The retained forwards have source execution prices:

| Source instrument | Execution date | Source price |
| --- | --- | --- |
| `20764` | 2026-09-21 | `0.747406499446919` |
| `21105` | 2026-10-19 | `0.7486626078341135` |

Both export instrument currency GBP and trade currency USD. The owner confirmed
these prices mean **GBP paid per 1 USD**. Preserve that rate orientation and the
original quantities; native base/quote and quantity-basis mapping must agree
before approval. No inversion applied.

## Public-source resolution — 23 October follow-up

The owner directed public research rather than asking them to settle reference
facts. The [DMO original prospectus](https://www.dmo.gov.uk/media/5p2hfyex/prosp030124.pdf)
confirms `GB00BPSNB460` is 3.75%, matures 7 March 2027, accrues from 11 January
2024 and first paid interest on 7 September 2024. The
[DMO January–March 2025 register, page 7](https://dmo.gov.uk/media/44gmcfe2/jan-mar-2025.pdf)
also identifies the 4.25% 7 December 2027 and 4.375% 7 March 2028 gilts, with their
semiannual coupon cycles. These facts agree with the detailed source bond file.

The [DMO fourth-edition formulae, 18 December 2024](https://dmo.gov.uk/media/334d05fo/yldeqns_v4.pdf)
use actual days and quasi-coupon periods. Mapping that formula to our
`ACT_ACT_ICMA` catalogue entry is an **implementation inference**, explicitly
retained as `INFERRED_FROM_DMO_QUASI_COUPON_FORMULA`; it is not represented as a
variant present in the original CSV. No automatic daily accrued amount or coupon
entitlement is inferred from the mapping. Public sources checked on 23 October
2026; original source/receipt times remain unchanged.

`--review-dmo-gilts` appends new normal bond proposals, checks coupon/ISIN agreement,
approves reviewed definitions and rejects the old incomplete requests as
superseded in the same transaction. Audit binds public URLs, normalized facts,
review date, original receipt, old/new request IDs and final instrument ID.
Repeat execution returns the same reviewed proposals; it does not rewrite a
decided proposal or duplicate a canonical bond.

## Boundaries, weaknesses and questions

- Several unit swaps lack contractual notional. Their source terms also do not
  establish all funding/return/reset conventions required by native approval.
  The owner permits clearly identified inferred/mockup seed terms and explicitly
  rejected weakening existing contracts for this journey. Complete missing test
  terms in the seed adapter; preserve sourced values and disclose assumptions.
  See the supplied-mark discussion and the subsequent scope ruling below.
- The source universe is selected from final open instruments, not a complete
  period ledger. Historical fully closed instruments may be absent. There is no
  corporate-action export or independent expected P&L/NAV report in this bundle.
- Account/date/currency duplicates must be resolved to real separate account
  identities. One legacy SGD balance is not authority to carry it forward or
  synthesize zeroes on other dates.
- Source date is not publication/receipt time. File possession is not inferred
  third-party licence coverage; do not automatically promote provider data to
  official/valuation-eligible observations or rewrite existing policies.
- Present work does not claim complete financial reconciliation, browser
  acceptance or derivative valuation readiness.

## Implementation and verification

- [Pure bundle preflight and immutable retention](../../tooling/reconciliation_csv/reconciliation.py).
- [Local guarded operator](../../tooling/reconciliation_csv/seed_reconciliation_bundle.py): read-only
  unless `--apply`; local named DB only; current reference/strategy authority,
  transaction-owned audit and source-scoped replay checks. `--bonds stage` prepares
  proposals; `--bonds approve-ready` approves only unambiguous zero-coupon terms.
- [Bond adapter](../../tooling/reconciliation_csv/reconciliation_bonds.py): normal proposal/decision
  services, explicit source quote conversion, no direct trade/price table writer.
- [Product seed adapter](../../tooling/reconciliation_csv/reconciliation_products.py): existing
  index, swap, ETP and option services; disclosed mockup terms and independent
  pending requests; no production contract/validator modifications.
- [Preflight tests](../../tooling/reconciliation_csv/tests/test_reconciliation_bundle.py),
  [bond mapping tests](../../tooling/reconciliation_csv/tests/test_reconciliation_bonds.py),
  [mockup term tests](../../tooling/reconciliation_csv/tests/test_reconciliation_products.py),
  [disposable database tests](../../tooling/reconciliation_csv/tests/test_reconciliation_seed.py).

Latest focused run: **29 passed** in an owned migrated/seeded disposable
PostgreSQL database, including bundle rules, quote conversion, currency/type
conflict guards, proposal approval/replay, DMO enrichment/original-payload retention,
private reference/swap creation, mockup disclosure, option/AMC pending handling,
access denial and repository neutrality. This was the earlier run, before the AMC
mapping correction. The corrected tests require an AMC to remain AMC even with an
ETI catalogue fixture, and check rejection/replay of the mistaken request without
altering its original payload. No ETI catalogue entry is inserted in the app.
Earlier live readback confirmed seven
approved / three pending requests and unchanged trades; the follow-up applied
three reviewed approvals, retiring those pending requests. No full suite run or
operating-database tests.
Runtime logs under ignored `logs/reconciliation-*.log` retain live commands and
results. Do not confuse disposable tests with the separately authorized local
operator application.

The latest live replay/readback confirmed exactly **40 tenant-one private nodes**:
ten bonds, thirteen swaps, thirteen source performance indices, SOFR/SONIA rate
identities, one SPX reference and one option. The AMC request remains pending.
The new strategy still has zero trades and the app-wide trade count remains 46;
no market observations, balances, accruals, economic flows or valuations were
posted by these creation batches. Replaying both product stages returned the
same nodes. After documentation updates, the pure/scoped neutrality checks also
passed (**20 tests**); no whole-application acceptance is implied.

### AMC correction verification and activation

The subsequent focused disposable-database run passed **30 tests** (7.16 seconds
of test execution), including corrected AMC classification, no ETI substitution
even with an active ETI fixture, rejection of the legacy request with unchanged
payload, safe replay and no trade creation. The local operator then committed
the correction: pending item `FCGMS [AMC]`, type
`ACTIVELY_MANAGED_CERTIFICATE`, ISIN `DE000A4AHQW5`; superseded ETI proposal
`01a16826-4852-72ee-a7a9-324d9e8181d0` rejected. Its original evidence remains
retained. Option identity is unchanged; no AMC instrument, trade or price was
created. Logs: `logs/reconciliation-amc-correction-tests.log` and
`logs/reconciliation-amc-correction-apply.log`. No migration or restart required.

## Supplied-mark swaps — clarified implementation boundary

For price-based P&L, a unit swap needs booked signed units, execution/valuation
dates, execution price, compatible opening/closing marks, quote/unit factors,
trade-price currency, reporting FX and separately classified dated reset flows.
Provided marks may already include leverage and financing. Do not multiply by
leverage or accrue financing again merely because those terms exist in metadata.

A unit swap's contractual aggregate notional is not needed to multiply units by
a compatible per-unit mark. A nominal-quoted swap still needs its **booked nominal
quantity**; that is distinct from optional contractual aggregate notional. Funding
and reset schedules are needed to project/rebuild prices, generate cash flows or
compute relevant reference-notional/exposure measures, not simply to consume
compatible externally supplied marks. Missing terms should make only those
dependent capabilities unavailable, not become zeros or fabricated facts.

**Not implemented yet:** the current `GenericSwapTerms` requires contractual
notional and unit-reference notional; separate funding requires full conventions.
Creation therefore cannot currently retain these unknowns as approved terms.
The daily P&L ledger adapter explicitly excludes SWAP, and boundary marks require
positive prices, whereas whole-swap marks may be zero or negative. Removing one
validation check would not enable safe swap P&L.

The suggested versioned supplied-mark path was **not approved for this journey**.
No change to swap terms, booking validation or valuation capabilities was made.

### Latest owner ruling: fit the seed to the application

Keep the existing model and validations. Derive terms from the supplied dataset,
then use explicitly identified mockup values where contractual fields are missing.
Do not create an incomplete-terms mode or expand product P&L support just to make
this journey pass. A genuine unsupported capability remains a reported test gap.

Source inspection establishes thirteen swaps with effective/maturity dates,
currencies, performance references and leverage; seven have a source notional and
six do not. Source payment counts are 1, 4 or 12 per year. These can inform annual,
quarterly and monthly mockup reset conventions, but payment count does **not**
prove reset frequency: any such mapping must be marked inferred. The source
funding IDs `1396` and `1048` identify SOFR and SONIA respectively, despite their
generic INDEX export classification; retain their funding identities rather than
inventing replacements. Missing day-count/calculation details, directions and
contract sizes require separately disclosed mockup assumptions, not assertions
that they were present in the export or independently confirmed.

Keep supplied trade quantities, execution prices, dates, marks and RESET amounts
separate from invented contract metadata. The current source contains fractional
swap units, including values beyond native 12-decimal precision. Existing booking
increments and precision must be assessed explicitly before posting; do not round
or rescale actual trades silently, or change global validators to make them fit.

## Financial import progress and precision ruling

On 23 October the owner authorized keeping all native precision, truncating excess
digits when necessary. Import-only normalization uses Decimal ROUND_DOWN (toward
zero), not half-even rounding. Original CSVs remain byte-for-byte retained; each
successful booking's audit stores original row, exact converted value, stored
value and exact delta. Bond fraction-of-par ×100 remains a separate conversion.
No binary-float conversion, rate inversion or source-quantity rescaling is used.

[Precision adapter](../../tooling/reconciliation_csv/reconciliation_precision.py),
[native investment adapter](../../tooling/reconciliation_csv/reconciliation_postings.py),
[cash adapter](../../tooling/reconciliation_csv/reconciliation_cash.py),
[confirmed forward adapter](../../tooling/reconciliation_csv/reconciliation_forwards.py).
All use the guarded local operator; booking, access, proposal approval and cash
revision services remain authoritative. Unknown source-company IDs are explicitly
unverified operational placeholders, with no invented legal names or LEIs. Only
the owner-confirmed company21 is Northern Trust. Curated counterparty additions
preserve every existing selection. Fractional swap conventions are newly approved
versions; prior conventions and financial evidence stay unchanged.

The tenant's existing required ALLOCATION_WEIGHT receives an explicit operator
mapping of 1: every supplied trade is wholly assigned to this strategy. It is
retained as a reconciliation assumption, not represented as an exported field.
Other required properties would block unless mapped; none are made optional.

Initial operating batch: **43 booked, 35 unposted** (19 derived swap entry-value
precision refusals; 16 awaiting other booking adapters). The 19 refusals revealed
an overly restrictive shared helper: the derived swap reference value is decimal
text evidence, not a NUMERIC(30,12) cash/payment column. Exact terminating products
can retain additional digits without changing valid input quantities or prices;
nonterminating division, nonfinite values and the existing magnitude limit still
fail. No generic cash amount validator or stored financial evidence is changed.
[Python Decimal guidance](https://docs.python.org/3/library/decimal.html) supports
exact string construction, local precision contexts and explicit Inexact traps;
this storage-boundary distinction is the project's engineering decision.

Cash batch: **121 exact-date snapshots across 8 accounts**, via the native revision
writer. Source company, agent, instrument/currency and account-description identity
separate NT, IB/Misc, ordinary USD and derivatives-wash balances. No summing of
different accounts, generated zeros, carry-forward, trade or payment posting.
Reporting company21 does not prove the underlying venue legal identity. CUSTODY
account type is a disclosed source-reporting bucket assumption, not legal custody
verification. Original comments and source receipt references remain on snapshots.
Evidence: `logs/reconciliation-position-trades-apply.log`,
`logs/reconciliation-cash-apply.log`. Focused disposable run: **34 passed** in
34.31 seconds (`logs/reconciliation-cash-focused.log`).

The owner confirmed both retained forwards' quantities are **USD**, with **GBP per
USD** rates. The adapter maps USD as native base, GBP as native quote, preserves
sign/rate without inversion, and retains original misleading currency labels as
source evidence. Deliverable settlement is inferred from source forward/maturity
dates. No automatic maturity closure, cash movement or rights grant is implied.

At that checkpoint, separate work included the 13 bond investment bookings (approved sparse terms lacked
face denomination and require a governed enrichment path), source-normalized option
listing/booking, economic RESET flows, market observations/FX and position-level
daily-interest aggregation (subsequently completed below). These other data are
retained but not yet financially posted.
SWAP/OPTION daily P&L remains outside current product support; importing trades
does not itself make a full-strategy valuation valid. Follow-up counts below take
precedence over dated initial-batch numbers.

### Latest committed readback

The final batch posted the last AMC trade and safely replayed the earlier native
bookings. **64 investment trades are now booked: 16 AMC, 46 swap and 2 FX forward.**
At that checkpoint the 13 bond executions and one source-normalized option execution remained unposted.
The investment adapter's row report still shows 16 rows awaiting other adapters;
two of those are handled successfully by the separate forward adapter. Do not sum
that raw failure count without reconciling the separate forward result.

One AMC execution needed 11 price decimals, not 12, so its fractional quantity
could produce an exact native 12-place funded consideration. Source quantity
`-1200092.9` remains unchanged. Source quote `0.9936969999999999` becomes
`0.99369699999`, with original and exact delta retained. The adapter tries greatest
precision first, preserves quantity, and refuses a material change: additional
price truncation must be within both 1e-9 absolute and 1e-9 relative, otherwise
explicit source review is required. This conservative local-import guard is not
a currency-rounding or general booking rule; generic funded consideration checks
are unchanged. Derived swap reference values retain their full exact product.

**111 supplied daily-earned-interest rows aggregate to 99 native bond/date inputs**,
all GBP, through the existing accrual writer. Original contributing trade rows and
exact normalization are audited. No accumulated balance, opening balance, coupon
cash, missing-date zero or reporting FX is invented. Replaying the batch leaves
one revision per submitted date, rather than creating new earnings.

**121 cash snapshots remain in 8 accounts**, without duplicate balances/revisions.
No valuation calculated/published, operating trade corrected/cancelled, market-data
permission inferred, source file changed or public source observation overwritten.
The retained manifest's NOT_POSTED describes the initial receipt, not live state;
it is deliberately not rewritten. Current financial counts come from posting
results and scoped DB readback, not that immutable manifest.

Verification: **85** focused native/import regressions passed in 376.77 seconds;
an additional **11** tests cover daily-interest native replay and exact derived
swap-value API persistence/retry. Final source-focused verification: **23 passed**
in 12.66 seconds. One attempt lost a connection during disposable migration setup;
the healthy service was checked and the fresh disposable retry passed. No test
used the operating database. Logs: `logs/reconciliation-final-postings.log`,
`logs/reconciliation-last-focused.log`, `logs/reconciliation-source-final-retry.log`,
`logs/reconciliation-latest-apply.log`, `logs/reconciliation-interest-apply.log`.

At that batch boundary the 193 RESET flows remained unposted. The next scoped
flow batch below posts only known links: 84 have no linked source reference, and 71
other references are absent from the final-open-universe instrument export. There
are no native currency/cash instruments to adopt. Do not attach these flows to an
arbitrary live swap or manufacture cash movements to satisfy the canonical-link
requirement. At this checkpoint the 884 price rows and 6358 FX rows were retained-only and required
their source/quotation/timing/rights-aware ingestion path; no full portfolio
valuation acceptance is claimed. Remaining work is not a precision blocker.

### Linked RESET posting

[RESET adapter](../../tooling/reconciliation_csv/reconciliation_flows.py) posts **38** source
RESET rows whose explicit reference resolves to an imported private swap, using
the native economic-flow writer. They are dated RESET/INCOME facts, price one,
not cumulative investment positions, exposure closures, cash-account snapshots
or payment confirmations. Original source row, sign, currency, economic date,
reference and precision evidence remain audited. Source classification follows
the owner's dated-flow ruling, not an assumption that an actual payment settled.

**155 RESET rows remain unposted:** 84 lack any reference and 71 refer to an
instrument absent from the supplied open-universe export. No arbitrary reference
or cash instrument is created. Completing these requires the missing references
or an explicit decision on a strategy-level unlinked-flow workflow, not a bypass
of the current canonical-instrument requirement. Focused native flow/replay and
source adapter tests: **12 passed** in 12.48 seconds,
`logs/reconciliation-flows-final.log`; operating result:
`logs/reconciliation-reset-apply.log`. No new public upload processor is implied.

Final source ledger reconciliation: 78 supplied investment rows → 64 booked,
14 pending (13 bond, one option); 193 RESET rows → 38 booked, 155 pending.
Separate snapshot/input tables contain 121 cash rows and 99 daily-interest rows
from 111 source accrual components. At this checkpoint price/FX files remained retained-only. No full
strategy valuation or reference-data/financial reconciliation sign-off.

### Subsequent FX activation — 23 October

[Private FX import](reconciliation-fx-import-20261023.md) now stores **4,620**
of the 6,358 original source rows: 15 selected fiat currencies, 210 directed
non-identity pairs, 22 dates from 21 September through 20 October. The other
1,738 rows (identities and unselected ILS/XAU crosses) remain in original evidence.
All selected stored values match the CSV exactly; replay creates no duplicate
delivery. Dataset `01a168a5-da3a-71ea-a389-21103c718672` is tenant-one-private,
inspection-only and date-only, not a UK/US fixing or valuation-use grant.
The **884 price rows remain unposted**; the investment/RESET/cash/interest gaps
above are unchanged. No valuation was run or published by this FX import.

### Subsequent bond booking activation — 23 October

[Bond delivery and verification](reconciliation-bond-bookings-20261023.md) completes
the **13 bond executions across 10 private instruments** through native booking.
All are CLEAN execution quotes, converted from source fractions ×100, with signed
nominal quantities unchanged and settlement accrual held separately. Earlier
missing penny-nominal metadata and pre-issue definition applicability were resolved
with retained version/audit evidence; actual issue and settlement dates were not
fabricated or moved. Migration 98 enables guarded supersession without economic
edits to old approved definition contents. No booking validators were relaxed.

Reconciled source investment count: **78 = 77 booked + 1 option pending**.
The bond batch has 13 BOOKED, 0 failed; replay has 0 new, 13 replayed. Net bond
nominal is **GBP 11,000,000**. RESET remains 38 posted/155 pending; the earlier
snapshot, interest and FX totals are unchanged. The 884 market-price observations
remain unposted. No valuation, cash movement or coupon income was created.

### Subsequent standard SPX option booking — 23 October

The owner confirmed source option quantity embeds its multiplier. The
[standard-option delivery](reconciliation-spx-option-20261023.md) maps source
execution `20260813113427-260b02154d607d4707d3` from 2,000 source units to **20
contracts × multiplier 100**, preserving premium 23.8 points and gross
**USD 47,600**. A proper XCBO listing was approved. The previous source-normalized
multiplier-one mockup remains retained but inactive/untradable, with no bookings.
The new OPTION_BOOKED reconciliation audit is the current source mapping; the
historical additional-instrument creation audit must not override it.

**All 78 supplied investment executions are now booked**, with original source
rows, normalization evidence and native frozen booking economics. Option replay
returns the same trade without duplication. This is booking completion, not full
portfolio reconciliation or option valuation support. The 155 unresolved RESET
rows and 884 unposted price observations remain separate outstanding work. No
valuation, cash balance change, option exercise or payment confirmation was run.

### Subsequent market-price import — 23 October

[Private market-price delivery](reconciliation-market-prices-20261023.md) now stores
**all 884 source observations across 42 references**, dated 21 September–20 October.
All 211 bond marks are CLEAN percentage-of-par after ×100 conversion; swap signs,
index levels, percent rate inputs, forward direction and AMC unit prices remain
explicit. SPX premium-point marks target the corrected standard-contract node,
not the superseded multiplier-one mockup. Five precision truncations retain exact
original/converted/stored values and deltas. Full normalized-source readback and
duplicate-safe replay passed; tenant-one display works and other-tenant display
is denied.

Dataset `01a168e1-2420-7973-a9d4-55ad1e0de59e`, **FCAGF — imported daily market
prices**, is a private personal inspection dataset. No UK/US fixing times,
publication timestamps, official status, valuation-use rights or policy updates
were invented. Earlier retained-only price statements above are historical batch
checkpoints. All source investment executions and price rows are now imported;
155 RESET rows remain unresolved. Price validation, use/policy eligibility and
supported-product financial reconciliation remain separate work. No valuation
was run or published by this import.

### Subsequent swap P&L extension

[Supplied whole-swap mark support](swap-supplied-mark-pnl-20261023.md) now reads
the imported generic swaps from their retained approved booking evidence and
uses signed quantity/divisor × mark-and-FX changes. It does not multiply leverage
or reference notional again and does not generate funding or cash postings.
This is not a successful FCAGF portfolio run: option P&L remains unsupported,
and the private imported datasets still require legitimate valuation eligibility,
matching policy rules and governed calendars. No import evidence was rewritten
to bypass those remaining boundaries.

### Subsequent listed-option P&L extension

[Option premium support](option-premium-pnl-20261023.md) now uses the imported
SPX trade's **20 contracts × premium multiplier 100**, with its retained original
booking fingerprint verified rather than the current terms substituted. Supplied
premium marks feed the shared execution/FX bridge. This supersedes the option-P&L
exclusion above, but does not establish a successful FCAGF portfolio run. Dataset
valuation-use eligibility, matching policy/calendar setup and independent numeric
reconciliation remain separate; exercise/expiry processing is not inferred.

### Imported-data eligibility activated

[Personal valuation setup](reconciliation-valuation-eligibility-20261023.md) now
adds separately attributable non-display/valuation coverage, a new FCAGF
source-date EoD policy and two retained forward-label normalizations. Original
source rows, inspection declarations and existing policies remain unchanged.
The 19–20 October rollback preflight passed price/FX selection, then stopped at
missing daily accrued-interest coverage for **UKTB 0 03/01/27** on 20 October.
No placeholder income, staged result or publication was created. This supersedes
the earlier eligibility-pending notes, not the independent financial-sign-off gap.
