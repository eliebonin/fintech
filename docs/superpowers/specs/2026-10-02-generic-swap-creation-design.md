# Generic swap creation and booking

Date: 2026-10-02. Status: approved in chat on 2026-10-02; implementation and isolated creation/booking alpha acceptance completed on 2026-10-05. Whole-feature review findings were corrected and checked directly after the user switched to sequential execution; full suites passed. This is design intent, not production/valuation sign-off; see [delivery evidence](../../delivery/generic-swap-creation-and-booking.md).

## Intended outcome

A tenant can create an OTC performance swap referencing an existing instrument, submit it for review, approve it through Operations, and book trades against its approved terms. Creation comes first; booking then consumes those same terms. The page must remain usable for a simple swap without requiring an autocall or a funding leg.

The user-approved core is: reference instrument, optional funding reference, funding spread, contractual notional, total/excess return, leverage, and reset frequencies. Contractual notional and booked notional may differ. Instrument terms describe the contract; a trade records an execution against it.

This extends the existing swap alpha, not an interest-rate/cross-currency/credit swap engine. Valuation and lifecycle processing remain separate work.

## Approach

Recommended: reuse canonical instruments, proposal approval, swap legs, booking conventions, and the existing trade ticket. Add a strictly validated, versioned generic swap definition associated with an instrument definition version. It holds the economics that existing swap tables cannot express.

Alternatives considered:

- A form that only writes the existing two-leg tables is smaller but cannot faithfully represent optional funding, contractual notional, leverage, or separate reset conventions.
- A complete cashflow/lifecycle engine would represent more products but exceeds the requested creation/booking scope.

Do not use an unvalidated metadata blob as the economic contract. The new payload has an explicit schema version, typed enums/decimals/dates, reference identifiers, and server-side validation. It is immutable once approved. Existing approved swaps and historical trade snapshots retain their legacy interpretation.

## Creation terms

### Core

- Display name and optional tenant identifier; no mandatory ISIN or listing.
- Reference instrument: approved/current, active, and visible to the tenant. Also support active governed indices through their reference records. Do not restrict this to autocalls. Exclude swap-on-swap references in this alpha to avoid recursive economics.
- Contractual notional: positive decimal, with currency.
- Effective date and maturity date: effective must precede maturity.
- Performance direction: receive or pay, from the contract-holder perspective. The optional funding leg has the opposite direction.
- Return basis: total or excess. Use existing governed return profiles where they express the selected basis, rather than creating a second competing catalogue.
- Leverage: positive decimal, default 1, explicitly shown on review.
- Quote currency and positive quote divisor, using the existing `SWAP_VALUE_PER_NOTIONAL` convention. Currency must match the notional currency in this single-currency alpha.
- Source/confirmation evidence describing the agreed economics and quote convention.

### Funding

Funding is optional. With no funding reference, no funding leg, spread, funding schedule, or funding-notional basis is fabricated.

For the first executable alpha, the funding selector uses the existing governed rate-index references. This is a proposed scope restriction: an arbitrary instrument price is not automatically a funding rate. Supporting other rate-bearing instruments requires an explicit rate-source convention and can be added subsequently without changing the optional-reference model.

When funding is present, require:

- Funding reference and spread. Display spread in basis points; store a decimal rate (`150 bp = 0.015`). Negative spreads are permitted.
- Funding-notional basis: booked nominal or leveraged nominal. For a trade of 1 million at 2x leverage, these mean funding on 1 million or 2 million respectively.
- Day-count basis and interest calculation method, plus confirmation-derived observation details when applicable. Selecting SONIA does not itself specify compounding, observation lag, or payment rules.
- Funding reset/observation frequency and funding payment frequency, captured separately.

Prevent accidental double funding. Record explicitly whether financing is embedded in the reference return or represented by a separate swap funding leg. An excess-return reference normally already subtracts financing; adding a separate funding leg requires an explicit confirmation-backed acknowledgement of the additional charge. Neither the form nor booking silently adds or subtracts financing.

### Resets and reference termination

Record performance reset frequency independently from funding resets and payment frequency. Supported labels: at maturity, monthly, quarterly, semiannual, annual, and custom. Custom arrangements require a source-backed schedule description. Frequencies describe terms; they do not claim that event dates or cashflows have been generated.

Record the reference-redemption treatment:

- Terminate economic exposure when the reference matures/autocalls: suggested selection, requiring confirmation against the source.
- Continue under an explicitly described replacement, reinvestment, or proceeds rule: require that rule and source evidence.

A final payment may occur after exposure terminates. These terms do not implement termination events, reinvestment, or settlement. The UI must not imply automatic processing.

## Storage and approval

Add an additive migration after the existing swap alpha migrations. The versioned swap definition references the canonical instrument definition version and stores the strict economics payload; its references are checked against canonical reference records. Keep contractual notional here, never infer it from trade quantities.

At approval, atomically materialize:

1. Tenant-scoped canonical SWAP instrument and approved instrument definition.
2. Typed generic swap definition, dates, and approved booking convention.
3. Performance leg and, only when configured, a funding leg linked to the same canonical swap.

No placeholder active schedules are created from frequency labels alone. Existing schedule tables do not contain the complete accrual/observation conventions; those remain in the versioned typed definition until a later schedule engine consumes them.

Use the established proposal workflow with a new `CREATE_SWAP` type. Add it to instrument-creation request filtering and Operations queue handling. Revalidate tenant visibility, reference eligibility, dates, and conventions at approval, not only when submitting the proposal. Failed approval leaves no partially materialized instrument.

Preserve existing workspace permissions and tenant-admin approval requirements. Proposed references must not reveal another tenant's instruments or private names. A rejected proposal stays auditable.

## Frontend

Add Swap to the existing instrument creation picker, linking to `/instruments/swaps/new`. Keep the form in four meaningful groups: reference and contract, return and leverage, optional funding, and lifecycle/quote conventions.

Reuse existing instrument search and currency/reference lookups. Selecting no funding hides dependent controls without silently retaining stale submitted values. Explain contractual notional versus booked notional beside the field. Show conditional source requirements and inline validation.

Include a review step showing reference, directions, notionals, currencies, leverage, return/funding treatment, quote divisor, reset/payment conventions, and redemption rule. Users can return to edit without losing input. Submission explicitly says it creates a pending request, not an approved instrument or trade.

Approved instrument details display the same terms and funding catalogue/reference links. Approval and instrument navigation follow existing Operations patterns; no new standalone administration subsystem.

## Booking integration

Generic approved swaps use a new typed context loader; legacy swaps retain their existing eligibility rules. Do not turn every previously unsupported SWAP into an eligible product merely because the new page exists.

The dedicated booking page remains the entry point. It displays the approved terms and prefills booked notional from contractual notional, with an editable positive quantity. There is no full-contract-only switch or aggregate contractual-capacity enforcement. Separate trades referencing an instrument are not automatically slices of one legal agreement.

Preserve strategy, execution time, side, trader/counterparty/custom properties, idempotency, and stale-terms checking. Execution must fall within the effective/maturity window. No automatic upfront cash trade is created. Users may independently book an appropriately labelled cash trade under the already agreed policy.

The quote is the whole swap's value per booked nominal, including its contractual leverage and funding effects. Zero and negative quotes remain valid. Apply side once:

`entry reference value = signed booked notional × execution quote ÷ quote divisor`

Do not multiply this value by contractual notional or leverage. A separate reference-exposure measure may use booked notional × leverage; that is not a second multiplier for a whole-swap quote. This release does not implement valuation/exposure calculations.

The immutable trade snapshot includes the approved definition/version, contractual and booked notionals, reference identities, optional funding terms, return treatment, leverage, date/frequency/redemption rules, quote convention, and source evidence. Lock/revalidate all relevant economic rows and references before booking; changed terms require a refreshed ticket. Existing booked snapshots and idempotent replays remain compatible.

## Verification and delivery

Start with lightweight contract/service tests before product code. Cover strict conditional funding fields, spread conversion, total/excess funding treatment, reference permissions, versioned terms, creation/approval atomicity, and notional/quote arithmetic.

Then add integration and browser coverage:

- Create, inspect pending request, approve, inspect canonical terms, and find it in booking.
- Book a no-funding swap and a rate-funded swap; edit prefilled notional and retain both amounts in the snapshot.
- Exercise 2x leverage with a whole-swap quote, zero quote, negative quote, BUY/SELL, and custom trade properties.
- Reject hidden/retired/unapproved references, stale terms, invalid date windows, inconsistent funding inputs, and duplicate proposal approval.
- Verify legacy alpha booking and historic snapshots remain unchanged, plus existing product creation/booking regressions.

Run focused tests first, then the full Python suite, frontend tests, type checking, build, and generated-contract checks. Use an isolated test database for migrations and browser evidence. Do not claim the running app is activated without explicitly migrating/restarting and verifying it.

Update the delivery documentation with implemented scope, test results, activation status, and remaining restrictions. This spec alone does not establish completion.

## Research and how it influenced the design

Reviewed 2026-10-02:

- [FINOS CDM product model](https://cdm.finos.org/docs/product-model/): separates product economics from execution price/quantity and distinguishes performance payouts, financing conventions, resets, and payments. This supports versioned terms and separate booked notional; our smaller schema is not a claim of CDM conformance.
- [GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/): supports logically grouped questions, optional controls, and reusing previously entered information. Applied to the conditional funding section and reference selection.
- [GOV.UK check answers](https://design-system.service.gov.uk/patterns/check-answers/): supports reviewing answers and editing without losing input. Applied before proposal submission, with pending versus approved status made explicit.
- [Bank of England SONIA features and policies](https://www.bankofengland.co.uk/markets/sonia-benchmark/sonia-key-features-and-policies): distinguishes the overnight benchmark from compounded-index information. Applied by requiring contractual funding conventions rather than inferring them from the benchmark name.

Our whole-swap quote rule, editable booked notional, and no automatic cash trade are project decisions agreed with the user, not universal market conventions. FpML pages were inaccessible during the preceding research; no FpML compliance assertion is made.

## Spec self-review

Checked for placeholders, contradictory notional/leverage formulas, optional-funding assumptions, legacy compatibility, tenant boundaries, and inadvertent valuation scope. No implementation status is implied. The rate-index-only funding selector is explicitly proposed for review, rather than silently narrowing the user's generic model.
