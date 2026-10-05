# Generic swap creation and booking

Date: 2026-10-05. Status: implemented; final acceptance and whole-branch review in progress. Operating activation has not occurred. This extends the [legacy autocall-reference booking alpha](swap-booking-alpha.md); it does not make arbitrary legacy SWAP records eligible.

## Creation and approval

The instrument picker offers Swap at `/instruments/swaps/new`. Four form groups capture reference and contract, return/leverage, optional funding, and lifecycle/quote conventions. Review and back-to-edit retain entered values. Submission creates a pending `CREATE_SWAP` request in Creation Requests and Operations. Existing tenant/module/role permissions apply; tenant-admin approval revalidates visible active references under locks and atomically creates the canonical SWAP, approved definition/version, typed generic economics, dates, booking convention and contractual legs.

Performance references may be approved current active instruments or active governed indices; swap-on-swap is excluded. The instrument must agree with its approved definition. Source-index financing is independently validated so an excess-return reference cannot be declared unfinanced. Contractual notional, single currency, dates, holder direction, total/excess return profile, positive leverage, independent performance resets, sourced reference-redemption treatment and whole-swap quote divisor are explicit. Optional tenant identifiers remain typed record-keeping metadata.

Funding is optional. Turning it off clears dependent fields; no funding leg, spread or schedule is invented. The executable selector accepts governed rate indices only. Funding requires spread, booked/leveraged nominal basis, day count, calculation method, and separate reset/observation and payment frequencies. `150 bp = 0.015` decimal rate; negative spreads are allowed. Excess return embeds financing; additional separate funding requires an explicit acknowledgement and source evidence. A benchmark name does not infer compounding or observation rules.

Custom frequencies and continued reference exposure require source-backed descriptions. Frequency labels and redemption terms record an agreement; they do not generate schedules or process events. No confirmation interpretation is substituted for the operator's sourced terms.

## Booking and immutable evidence

Book trade → Swap consumes the exact approved version. Contractual notional prefills an editable positive booked nominal; there is no full-contract-only rule or aggregate capacity enforcement. Strategy, timestamp, BUY/SELL, parties, trader and governed custom properties reuse the existing ticket. Execution must lie inside the effective/maturity window; stale economic/reference facts require a refreshed ticket. Locks, idempotency and transactional rollback preserve one booking and historical replay.

The quote represents the whole swap including its contractual leverage and funding effects:

`entry reference value = signed booked nominal × execution quote ÷ quote divisor`

For contractual nominal 1,000,000, booked nominal 400,000, leverage 2, quote 2 and divisor 100, BUY records 8,000. Leverage and contractual nominal are not multiplied again. SELL changes nominal sign once; zero and negative quotes are valid. This entry reference value is not an upfront payment or independently verified valuation.

One immutable BOOKED snapshot retains both nominal amounts, approved version, reference identities/facts, optional funding conventions, return financing treatment, dates/frequencies/redemption rules, quote convention and sources. Ticket review and trade history/details display saved facts. Existing legacy eligibility and snapshots retain their original interpretation.

## Storage, verification and activation

Revision `20261002_60` adds version-owned JSONB economics with FK/unique ownership and schema shape checks. Additive revision `20261005_61` closes PostgreSQL CHECK's JSON-null version hole; revision 60 remains unchanged. Both are forward-only. Service contracts validate the complete economics; database shape checks are not a full JSON-schema enforcement layer. Approval immutability is enforced by the service boundary; no generic amendment endpoint is delivered.

Final verification and real-browser evidence are recorded in the [execution log](generic-swap-execution-log.md). The form's native required constraints, funding off/on/off clearing, review/back-edit, exact funded conversion, pending Requests/Operations and tenant switching were exercised in a new isolated database and production UI. Automatic approval review currently blocks synthetic approval; approved-detail, booking and history browser proof therefore remain outstanding. Automated backend coverage is distinct from that browser proof.

No operating database was migrated, no operating service was restarted, and no operating trade was created. Activation requires an authorized migration through revision 61 and deployment/restart of matching API/UI code, followed by operating health/tenant checks. This record does not claim activation or production/valuation sign-off.

## Boundaries and design sources

No automatic cash trade, fee, settlement obligation, valuation/exposure calculation, funding accrual, dividend/reset/termination/reinvestment engine or generated schedule is delivered. A separately entered cash trade remains an independent operator workflow. Non-rate funding instruments, multicurrency/interest-rate/cross-currency/credit swaps, generic terms amendments and capacity aggregation are outside this alpha.

Primary research was reviewed for the [approved design](../superpowers/specs/2026-10-02-generic-swap-creation-design.md) on 2026-10-02: [FINOS CDM product model](https://cdm.finos.org/docs/product-model/) informed separation of contract and execution; [GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/) informed grouped conditional controls; [GOV.UK check answers](https://design-system.service.gov.uk/patterns/check-answers/) informed review/edit retention; [Bank of England SONIA features and policies](https://www.bankofengland.co.uk/markets/sonia-benchmark/sonia-key-features-and-policies) informed explicit funding conventions. Whole-swap quote arithmetic, editable booked nominal and no automatic cash are project decisions, not universal market rules. No CDM/FpML conformance is claimed.
