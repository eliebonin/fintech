# Expanded position measures — 3 November 2026

Status: implemented and locally activated; bounded alpha acceptance complete. Priority 6 from the instrument-family review.

[Implementation plan](../superpowers/plans/2026-11-03-expanded-position-measures.md).

## Research and decisions

- [CESR final UCITS risk guidelines, 28 July 2010, CESR/10-788](https://www.esma.europa.eu/sites/default/files/library/2015/11/10_788.pdf): derivative commitment conversion uses equivalent underlying positions, including option delta. We use the distinction to avoid mislabelling premium or funded principal as underlying risk. This preview is not a UCITS commitment implementation or regulatory certification.
- [Cboe SPX specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications): explicit product multiplier and expiry/trading conventions. Product examples never become hard-coded universal factors. Option strike notional is a labelled project reference convention, not delta-adjusted market exposure.
- [CME Bitcoin contract-value example](https://www.cmegroup.com/education/courses/introduction-to-bitcoin/what-are-bitcoin-futures): price per bitcoin and contract size produce contract notional. Reuse the sourced multiplier for cash/physical linear contracts; delivery method does not turn notional into clearing MTM. The educational page's trading schedule is not used to seed calendars.

All amounts retain local currency and separate governed strategy conversion. No NAV weights, synthetic Greeks, payoff pricing, accounting or operating financial writes are part of this work.

## Implemented measure definitions

| Family | Reference notional | Market value | Economic exposure |
| --- | --- | --- | --- |
| Spot crypto | Current signed listing value | Same | Same monetary value, without token look-through |
| Dated linear index/crypto futures | Contracts × exact-expiry mark × saved monetary multiplier / factor | Unavailable: clearing/reset boundary deferred | Same current monetary notional |
| Listed vanilla options | Contracts × strike × deliverable units, in strike currency; labelled Strike notional | Contracts × canonical premium × premium multiplier / factor, in premium currency | Unavailable pending governed delta/underlying risk inputs |
| Fully funded notes | Signed face for percentage quotes; labelled current funded-value reference for monetary unit quotes | Whole-note dirty value, or clean quoted value plus assessed exact-date note stock | Unavailable pending payoff sensitivities/look-through |
| Generic performance and rate-exchange swaps | Booked nominal, or units × saved reference notional/unit | Booked quantity × supplied whole-swap mark / factor | Existing compatible unit-index exposure; other underlying/reset/rate-risk cases unavailable |

The user explicitly agreed to keep unmodelled option/note risk exposure unavailable. Strike notional is an exercise-reference convention: long puts do not acquire a positive delta merely because this reference is positive. These values are not UCITS commitment, credit exposure, risk weights, NAV weights or a portfolio NAV total.

## Sources and safeguards

The quantity reader now recovers OPTION identity and unit-note denomination from original BOOKED terms. Native option/note/futures/swap validators recheck the original fingerprint, historical identities and execution economics; current definitions never replace original factors. Scoped trade reads batch SQL parameters without capping retained history. Selected price and reporting FX retain policy, actual date and current DISPLAY rights. Missing FX preserves native values; missing price preserves an independently known reference.

Note CLEAN/DIRTY/NONE, price basis and quote divisor must match their whole-note source semantics. DIRTY has precedence where the chosen policy allows it, with no second accrued addition. Conditional notes deliberately stay outside bond coupon reconstruction. CLEAN-note stocks reuse the existing assessed-note input bridge, with exact date, one compatible canonical position, matching currency/nominal, reconciled source amounts and original source hash. Daily earnings alone are not the accumulated stock. CLEAN unit-price notes additionally need explicit nominal mapping (saved denomination); missing mapping leaves market value unavailable. There is no new note balance-maintenance UI or conditional coupon engine in this slice.

Whole-swap values no longer depend on the availability of an underlying risk model or an interim-reset model. Supplied whole marks already include financing, orientation and leverage; those are not multiplied again. Two-leg rate exchanges remain one separately marked contract, without summing the same whole mark once per leg. This does not infer principal movements, payments, sensitivities or reset reference levels.

Risk-only explanations are available in Inspect instead of repeating long deferred-model warnings in every row. Visible basis labels distinguish strike reference, note face/funded reference and whole-mark values. Technical evidence remains available.

## Remaining boundaries

- No Greeks, structured-payoff repricing, look-through, duration/DV01, inferred reset prices, netted cross-currency swap risk or automatic expiry/delivery.
- No clearing/variation-margin MTM, discounted forward MTM, cash movements or settlement/accounting.
- Adjusted option deliverables and lifecycle changes require explicit compatible retained contract evidence; no automatic underlying split is inferred for the derivative.
- Preview position keys can change when the original OPTION classification or note multiplier is recovered. Stored trades, persisted P&L and audit evidence are unchanged.
- This remains a paged, read-only, unpersisted preview. It does not sum a full portfolio, stage/publish measures or certify scaling. Native historical identity validation can require additional reads; MEASURES-005 remains a scale/performance limitation.

## Verification

- The affected regression run passed **174 Python tests** in an owned disposable database, including monetary measures, original-source evidence, strategy holdings/API, permission boundaries and native option/futures/swap P&L. An earlier 126-check run and lightweight 36-check run also passed; these counts overlap and are not summed.
- Live acceptance then reproduced an unhandled policy-permitted MissingPriceInput. A focused red test reproduced WARN; the fix converts only that specific price gap into per-measure unavailability. **46 price/permission checks passed** afterward. DISPLAY and unexpected failures retain their existing behavior.
- The strike-currency separation exposed a forward reference-currency regression in the live page. Existing contractual-leg tests reproduced it. Base reference currency/conversion was restored and **42 forward/product checks passed**. Reference and base-leg currency/conversion agree; no stored valuation was changed by the read-only bug.
- Frontend rendering/formatting passed **21 tests**; TypeScript and OpenAPI parity passed. Secret scan, changed-source syntax, UTF-8/whitespace and local documentation-link checks passed. The full Python suite was not run.

## Local activation and acceptance

API port 8000 and frontend port 3001 were restarted. Each API restart checked zero RUNNING valuation attempts first. No migration, permission grant, trade booking/cancellation, price upload, balance amendment or operating P&L calculation/publication was performed.

Read-only browser acceptance used tenant one's existing FCPGF strategy and imported EoD v3 policy on **2026-10-20**. The report displayed 125 positions/exceptions across pages. Inspected pages showed supported bond/fund values, preserved missing inputs, forward contractual legs, the listed SPX put and additional performance/rate-exchange swaps. The existing option's premium value and separately labelled strike reference were checked against its displayed contract inputs. Risk exposure remained unavailable. Selected prices, FX, actual dates and frozen multipliers were readable in Inspect; operating amounts are not copied into this delivery document. An invented unit-test example is short two contracts at premium 28 and multiplier 100: market value −5,600; strike 5,800 and deliverable units 100 give strike reference −1,160,000. Each is in its own contractual currency.

The corrected EUR forward reference and its GBP conversion matched the base leg. No console errors/warnings were captured in the walkthrough. Spot/linear crypto and direct-note quotation/stock cases were verified in disposable native-product tests, not operating financial writes. This is not an independent whole-portfolio reconciliation or production sign-off.

Observed development-server reads ranged from approximately 5 to 15 seconds for the inspected 25-row pages, including a cold load after API restart. These are observations, not a controlled benchmark; broader latency/concurrency certification remains open under MEASURES-005.
