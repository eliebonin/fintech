# Futures creation and contract conventions alpha

**Status:** Cash-settled index-futures booking and multiplier-inspection UX verified; crypto/physical creation only  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-02

This increment improves family and expiry creation, reuses the existing crypto-currency catalogue, and adds governed delivery cycles, symbol previews and dimensionally explicit contract sizes. The user approved a creation-only extension for crypto and physical-delivery futures. These contracts can be defined and listed, but their trade booking and delivery processing remain excluded. Existing cash-settled index booking remains supported.

## Completion boundary — 2026-10-02

The bounded **cash-settled index-futures booking alpha** is implemented and verified, not a complete futures lifecycle or valuation platform. Delivered: governed family underlying and source evidence; approved delivery cycles and year/month codes; contextual canonical expiry creation and approval; separate venue listing creation and approval; integer-contract outright booking with tick/cutoff validation; OPEN/CLOSE intent; tenant permissions, custom annotations, immutable booking economics and replay safeguards. Existing history/detail views retain those booking facts. OPEN/CLOSE is intent only, not a holdings check or automatic settlement.

The underlying is chosen in the family form's identity/underlying section from existing governed references. A canonical expiry inherits it, and a listing references that expiry. The underlying is not entered independently on each listing. The local real-product seed and isolated browser acceptance below exercise the family → expiry → listing chain.

The multiplier-inspection follow-up is now implemented. Canonical detail, booking review and history show the governed underlying, **Contract multiplier: 50 USD/point** for ES and its 0.25-point tick worth 12.5 USD per contract. The listing table is labelled **Contracts per listed unit**, displaying 1 separately. Stored economic values have not changed. Missing convention data produces an explicit unavailable message, not an inferred multiplier.

Deferred: position aggregation and close-availability checks; expiry/settlement lifecycle events and automatic position removal; cash postings and variation/initial margin; market-data policy resolution for futures; daily exposure, contract MTM, valuation and P&L; physical/crypto trade booking and delivery/custody processing; non-index commodity, inverse/quanto and multi-leg products. Cash-only P&L must not imply support for these futures. The creation-only exclusion for crypto/physical contracts is intentional and remains in force even after listing approval.

## Operator workflow

Use **Instruments → Create → Futures family**. Create and browse are separate views, so the family creation form is no longer mixed with the complete catalogue. Related questions are grouped into identity and underlying, symbol display and delivery cycle, economics and settlement, and source evidence. Review before submission; Back to edit retains entered values. Operations approval creates the non-tradable family only.

In the approved-family browser, select a family and follow **Create an expiry from this family**. This link preserves family context. Expiry creation inherits its approved underlying, quote currency, settlement method, size and price rules. The operator supplies the full year and a month-letter selection restricted to approved delivery months, exact timezone-aware trading cutoff, effective date, final settlement date and, for physical contracts, the delivery window. The explicit year/month controls avoid a native month-input inconsistency observed during browser acceptance. Review and submit for separate Operations approval. Then add and approve the canonical expiry's venue listing. No listing or trading symbol is silently created by a preview.

Inputs have visible labels and hints; input helpers associate hints as accessible descriptions. Forms use semantic fieldsets, responsive layouts and read-only summaries. The UI does not infer exchange calendars or delivery dates from the month letter.

## Identity and month conventions

Family specifications carry a display symbol root, one- or two-digit year suffix and explicit allowed delivery months. Monthly means all twelve months; quarterly uses March, June, September and December; custom cycles select their actual months. The source must justify the selected cycle. Expiry submission and approval reject months outside that family specification.

Standard month codes are F, G, H, J, K, M, N, Q, U, V, X and Z from January through December. A March 2027 contract can preview as `BTCH7` or `BTCH27`, depending on the chosen rule. The canonical record stores `2027-03-01`; short symbols cannot establish the full year and are not unique canonical identities. Actual venue/vendor symbols remain listing data. A family's display rule is a preview convention, not a claim that every platform uses the same representation.

The alpha still requires final settlement within the stated contract month and allows one canonical expiry per family/month. Daily, weekly or multiple intra-month series need a richer expiry key; they are not covered by a month selector. Physical delivery must begin on or after the cutoff date, end on or after its start, and end on final settlement. Contracts with different notice/delivery timing must be assessed before widening those rules.

## Contract size and quotation dimensions

A trade quantity counts futures contracts. For a linear crypto contract, the contract size is underlying asset units per contract, such as 0.1 BTC. Its quote currency can be USD even when physical BTC is delivered. A quote of USD 60,000 per BTC and two 0.1 BTC contracts represents 0.2 BTC and USD 12,000 reference value before any quotation divisor. This example illustrates dimensions, not a payment, valuation or supported crypto booking.

For these linear underlying-unit quotes, the price multiplier equals the approved asset quantity per contract. It is applied once; an independent extra multiplier would double-count exposure. Index contracts instead specify currency per index point per contract. An index is not a physically deliverable quantity. The price tick is in quoted units, distinct from monetary value per contract. Inverse, quanto, mixed-currency and commodity-unit formulas are outside this slice.

New family specifications govern these economics. Expiry approval checks the inherited values rather than permitting accidental drift. Legacy families retain null specifications and their previous explicit per-expiry cash-settled index convention workflow; no unverified defaults are backfilled. Family-rule amendment/versioning screens are deferred. A materially different specification needs a separately approved family identity for now.

### Listing conversion versus monetary multiplier

The user inspected instrument `01a0fba5-c696-70a4-b218-64773dbbe2ec`, listing `ESZ6`. Read-only database verification found listing `unit_multiplier = 1`, `quote_factor = 1`, and approved convention `monetaryMultiplier = 50`. Those values describe different dimensions, not conflicting contract sizes:

- Listing unit multiplier: canonical contracts represented by one listed unit. ESZ6 is one-to-one.
- Monetary multiplier: USD per index point per canonical contract. ES is 50; MES is 5; MNQ is 2.
- Quote factor: divisor converting the supplied quotation to the convention's price units; the seeded futures use 1.

For future **linear index-futures notional exposure**, the intended dimensional formula is:

`signed exposure in price currency = signed net listed units × listing unit multiplier × latest futures price ÷ quote factor × monetary multiplier`

If position quantity is already in canonical contracts, omit the listing conversion: it has already been applied. Never multiply a contract size and a monetary multiplier that represent the same conversion twice. Use the price of the exact dated future, not an unqualified underlying-index or continuous-series quote. Convert the resulting price-currency exposure separately to the strategy reporting currency using the chosen FX/market-data policy. This is a design clarification for later exposure work, not a newly implemented calculation.

Example: 2 ESZ6 contracts at 6,000 points give `2 × 1 × 6,000 ÷ 1 × 50 = USD 600,000` long notional exposure. A short net position gives negative signed exposure; gross and net aggregation need their own policy. Notional exposure is not contract MTM, a purchase payment, cash balance or margin requirement.

Current booking uses `execution_amount` in `security_master_schema/product_booking.py`: contract quantity × execution price × monetary multiplier ÷ quote factor. The ticket's quantity is already CONTRACTS, and this function does not apply listing `unit_multiplier`. Its positive reference contract value is snapshotted at booking; BUY/SELL supplies the signed trade quantity separately. This is not an implemented daily position/exposure service and does not establish support for arbitrary non-one-to-one futures listing conversions. The seed deliberately uses one-to-one listings.

[CME's contract-notional explanation](https://www.cmegroup.com/education/courses/introduction-to-futures/about-contract-notional-value) was read on 2026-10-02 and supports multiplying contract unit by futures price. The existing [CME Micro E-mini FAQ](https://www.cmegroup.com/articles/faqs/micro-e-mini-equity-index-futures-frequently-asked-questions.html) distinguishes ES/MES/MNQ monetary multipliers. The listing-conversion separation and reporting-currency policy are project-specific modeling decisions.

## Existing currency feature and persistence

The existing `GET /v1/currencies?groups=REGULAR,CRYPTO` endpoint already returns grouped fiat and crypto/stablecoin entries. The family screen reuses it for quote currencies, while the contract-size asset picker uses its CRYPTO group. Governing a Bitcoin underlying uses the existing digital-asset search. The server verifies that the size currency's reference node is exactly the selected active underlying; merely entering a label such as BTC is insufficient. Linked private crypto currencies are filtered by tenant visibility, and private quote-currency references are validated on submission and approval.

Additive revision `20261002_57` adds nullable `secm.future_family.specification_payload`. It stores a closed typed approved specification. The existing `expiry_cycle` stores allowed months. Existing `future_terms.settlement_method`, `delivery_start_date` and `delivery_end_date` columns hold physical expiry terms; these columns were already present, not newly invented. The immutable proposal retains source evidence, and the append-only expiry convention captures inherited economics and exact dates. No historical trade or family is rewritten. The migration is forward-only to prevent discarding approved specifications.

Crypto and physical contracts are explicitly ineligible in the product booking context and cannot use the legacy convention amendment path to masquerade as cash-settled index contracts. Cash postings, physical transfers, custody instructions, first-notice workflows, delivery events, positions, margin and valuation are not implemented. Listing approval alone does not remove this exclusion.

## Best practice evidence and project decisions

Sources were opened and read on 2026-10-02. Product examples must be verified against the actual venue specification when onboarding a contract; they are not universal defaults.

- [CME month codes](https://www.cmegroup.com/month-codes.html) establishes the twelve month letters. [CME trading-code guidance](https://www.cmegroup.com/education/courses/introduction-to-futures/understanding-contract-trading-codes) explains that roots, expirations and formats vary across platforms and gives a one-digit-year example. Project decision: store the full canonical month/year and show configurable previews; leave actual symbols to listings.
- [ICE Micro CoinDesk Bitcoin specification](https://www.ice.com/products/83047635) distinguishes 0.1 BTC contract size, USD-per-BTC quotes, tick value and monthly series. This is a cash-settled example; its page's “Physical” code label is not a settlement assertion. Project decision: model size, price currency and settlement method separately.
- [ICE's August 2019 Bitcoin launch notice](https://www.ice.com/publicdocs/futures_us/exchange_notices/ICE_Futures_US_BTC_Launch2019_20190816.pdf) documents physically delivered Bitcoin contracts with USD quotations. It is historical evidence that those dimensions differ, not confirmation that the product is currently offered. Project decision: allow explicit sourced physical terms while retaining creation-only booking exclusions.
- [GOV.UK question-page guidance](https://design-system.service.gov.uk/patterns/question-pages/) supports purposeful grouping and helpful hints; it does not mandate one field per page for every workflow. Project decision: grouped screens and a separate review step suit this bounded expert workflow without a lengthy wizard.

## Verification and local activation

Lightweight validation and month-code tests preceded implementation. The final isolated Python run passed **35 tests**, covering additive nullable migration, crypto group reuse, private-currency isolation, governed asset-size matching, physical delivery dates, allowed-month rejection, family-rule mismatch, creation-only booking exclusion, legacy family approval/reuse, existing index execution and replay safeguards. Frontend verification passed **313 tests across 86 files**, including all twelve month codes, one/two year digits, monthly/quarterly/custom cycles, inherited crypto size and delivery dates, review/edit retention and invalid-month rejection. TypeScript checking, production build and API export checking passed. A known Pydantic schema warning in concurrent API construction remains a warning.

Before activation, the operating database was backed up to `C:/Users/forte/Documents/ChatGPT/Tech V2/local-db-backups/fortem_secm_pre_future_family_spec_20261002.dump` (2,164,881 bytes). Operating and retained synthetic databases were upgraded from revision 56 to 57. Operating counts remained **9 trades and 271 instruments**. No operating family, instrument, listing or trade was created for tests. Local API/UI processes were restarted; the operating workspace may require tenant reselection after its session-key rotation.

Browser acceptance completed on the retained isolated demo database on 8001/3001. Created and approved family `BTC_PHYSICAL_UI_20261002` (proposal `01a0fb85-fea7-7068-904a-2bcbca3f0323`), then expiry `Synthetic physical Bitcoin March 2027` (proposal `01a0fb9a-f061-710b-836a-1c930ac2f00e`, instrument `01a0fb9b-66b9-7eba-9129-d617fc70117c`). The expiry inherited 0.1 BTC, physical settlement and monthly delivery rules; entering full year 2027 and H / March showed `SBTCH27`. Review/edit retained the year and dates. Listing creation preserved the parent, and synthetic listing `SBTCH27_TEST` was submitted and approved (proposal `01a0fb9c-116f-7231-a9e2-b26e9cbb437c`) on the explicitly synthetic BINANCE venue. This is illustrative test data, not a claim about a real exchange product. The canonical detail showed one active listing, and convention inspection still showed the creation-only exclusion after approval.

Browser proof is saved locally at `C:/Users/forte/Documents/ChatGPT/Tech V2/futures-expiry-review-20261002.png` and `C:/Users/forte/Documents/ChatGPT/Tech V2/futures-approved-listing-20261002.png`. The final UI build was restarted on 3000 and 3001 after replacing the unreliable native month input with full-year and allowed month-letter controls. No claim of production readiness or crypto trade execution is made.

## Local real-product sample seed — 2026-10-02

At the user's request, `scripts/seed_futures_catalogue.py --apply` added the following approved reference data to **Fortem Demo Tenant** in local `fortem_secm`. These are real product identities with sourced sample terms, not exchange connectivity or a live instrument feed.

| Family code | Underlying | USD per index point | December 2026 listing | March 2027 listing |
| --- | --- | --- | --- | --- |
| CME_ES | S&P 500 Price Return | 50 | ESZ6 | ESH7 |
| CME_MES | S&P 500 Price Return | 5 | MESZ6 | MESH7 |
| CME_MNQ | Nasdaq-100 Price Return | 2 | MNQZ6 | MNQH7 |

All three families are cash settled, use a 0.25-point outright tick, allow H/M/U/Z quarterly months and use a one-digit listing-year convention. Full contract months remain `2026-12-01` and `2027-03-01`, not short symbols. The December final settlement is 2026-12-18 and cutoff 14:30 UTC; March is 2027-03-19 and cutoff 13:30 UTC. Both cutoffs are 08:30 America/Chicago, with daylight saving accounted for. Dates are derived from the published third-Friday rule for these non-holiday dates, not imported from an authenticated exchange calendar. Unscheduled changes still require steward review.

The underlying is stated **at family level** (`underlying_reference_node_id`). Each canonical expiry inherits that reference and records it in its derivative underlying link; each venue listing refers to the expiry. The seed creates two tenant-owned price-return INDEX references, rather than reusing the old synthetic MVP index with its mock administrator. Administrator, calculation agent, observations, licensed methodology detail and index base levels are deliberately not invented. It also adds the missing shared Chicago Mercantile Exchange venue, XCME, with America/Chicago timezone. No exchange-calendar linkage is guessed.

The six listings belong to XCME, use USD and quote factor 1. Their unit multiplier is **1 canonical contract per listed unit**. The family's monetary multiplier (50, 5 or 2 USD per index point) is separate and applied once by the futures booking convention. No FIGI, ISIN, FIX SecurityID or venue-assigned numeric product ID is fabricated. One-digit display symbols are the local naming convention, not a promise that every provider uses that spelling; mappings remain a separate workflow.

The reusable command defaults to a transactional preview and rolls everything back unless `--apply` is supplied. It requires a current tenant administrator with trade-write authority, is restricted to local `fortem_secm`, serializes this seed bundle, uses the existing index/family/expiry/listing proposal and approval services, and commits the entire bundle atomically. Repeat runs verify and reuse existing seed identities; conflicting terms fail instead of overwriting. It does not rerun the broad demo loader, migrate schemas, create trades or attach market data. Additions: **2 indices, 1 venue, 3 families, 6 canonical futures, 6 listings, 17 proposals and 17 approvals**.

Before applying, the local database was backed up to `C:/Users/forte/Documents/ChatGPT/Tech V2/local-db-backups/fortem_secm_pre_futures_seed_20261002.dump`. An applied repeat run changed no counts; total local trades stayed **9**. The running API on 8000 returned all three families and all six listed booking contexts were eligible for the existing cash-settled index-futures ticket. No trade was booked during verification. Crypto/physical booking exclusions remain unchanged.

Seed tests cover approval counts, repeat-run identity/count stability, conflict rejection, unauthorized tenant access, no new trades and Chicago DST conversion. All **3 lightweight isolated seed tests** passed before applying. The final broader isolated run passed **7 tests** across `test_futures_catalogue_seed.py`, `test_future_specification_api.py` and `test_future_family_api.py`; this is targeted regression coverage, not a full Python-suite run.

Sources opened on 2026-10-02: [CME E-mini S&P 500 specifications](https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html), [CME Micro E-mini FAQ](https://www.cmegroup.com/articles/faqs/micro-e-mini-equity-index-futures-frequently-asked-questions.html) for multipliers, exchange and tick distinctions, [CME Micro E-mini fact card](https://www.cmegroup.com/trading/equity-index/files/cme-micro-e-mini-futures-fact-card.pdf) for quarterly cycle, roots and expiry cutoff, [CME Nasdaq micro rulebook Chapter 361](https://www.cmegroup.com/rulebook/CME/IV/350/361.pdf) for cash settlement and expiry exceptions, and [CME DataMine exchange-code documentation](https://www.cmegroup.com/datamine/datamine-list-api.html) for XCME. This is a deliberately small local seed, not a complete venue security master. Refresh source terms before operational onboarding beyond the alpha.

## Multiplier UX verification — 2026-10-02

`ProductBookingContextView` now carries optional governed underlying identity/name and the listing conversion. Canonical detail fetches those facts using trusted tenant context, while history uses its immutable booking snapshot. Old snapshots without these fields remain readable; no backfill or inference is performed. Regression tests cover units, tick value, unavailable fallback, tenant context and seed read models.

The initial focused Python run passed 33 tests; frontend verification at that stage passed 317 tests, type checking and production build. The subsequent bond increment's expanded run passed 58 isolated tests, including the Futures API, seed and family-specification checks, and 324 frontend tests. See [bond booking verification](bond-booking-alpha.md) for the combined final checks.

Browser acceptance used retained synthetic services on 8001/3001. One contract on synthetic ESZ6 at 6000 produced 300000 USD reference value, not purchase consideration or a margin posting. Trade `7867106e-956e-4f00-b944-ddb141fdd1cb` retained underlying, multiplier, tick value and listing conversion in history. Canonical inspection showed the separate listing column. Proof: `C:/Users/forte/Documents/ChatGPT/Tech V2/futures-inspection-ux-20261002.png`, `futures-history-ux-20261002.png` and `futures-ux-review-20261002.png` in the same directory. No operating trade was added.
