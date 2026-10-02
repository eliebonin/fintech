# Structured security and futures booking alpha

**Status:** Implemented and activated locally with bounded alpha verification  
**Content type:** Delivery report  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-02

The approved plan adds funded structured-security and cash-settled index-futures booking to the dedicated trade workspace. Review confirmed that explicit quote units and contract facts are necessary, but a general product language, new structured payoff master, clearing engine or valuation implementation would overdo this slice. One typed convention record extends the existing canonical master and approval queue. See the [reviewed plan and primary research sources](../superpowers/plans/2026-10-01-structured-product-and-futures-booking.md).

## Delivered workflow

1. A tenant administrator with the TRADING module creates the structured instrument using the existing builder. For futures, use **Instruments → Create → Futures family** to define and approve a non-tradable family, then **Create → Future** to select the approved family and create an exact cash-settled index expiry.
2. **Instrument detail → Inspect / configure conventions** displays the current sourced facts and submits a new convention version for Operations approval. Only tenant-owned instruments can be configured. Structured conventions follow approval of the economic instrument; this avoids duplicating its payoff builder.
3. For listed execution, add and approve the venue listing through the existing contextual listing workflow. Its currency and quote divisor must match the booking convention. A listing's generic unit multiplier is not silently interpreted as currency per futures index point; that monetary point multiplier is explicitly sourced in the convention.
4. **Book trade → Structured security / Future** searches approved, tenant-visible products by name, code, identifier or listing symbol. Results are paginated and expose specific ineligibility reasons. The selected contract facts are read-only.
5. Complete execution and the existing parties, trader, purpose, activity, governed custom properties, tags, references and comments. Review before confirmation. History retains a versioned immutable snapshot and exact economics, independent of later convention amendments.

Configuration requests appear in **Operations**, not the instrument-creation-only request list. Futures creation requests also appear in **Instrument requests**. No booking button was added to listings.

## Supported economics

The subsequent [futures creation and contract conventions increment](futures-creation-and-contract-conventions-alpha.md)
supersedes the initial family-creation UI and adds governed family specifications,
delivery cycles, symbol previews and crypto/physical instrument creation. Its
creation-only scope does not widen the booking support described in this report.

### Standalone futures-family onboarding (2026-10-02)

The family page provides paginated approved-family search and a creation form: display name, tenant family code, governed active index underlying, active contract currency and source evidence. Submission creates a `CREATE_FUTURE_FAMILY` request in Operations; approval creates only the tenant-private family reference and `secm.future_family` row. It creates no instrument, listing or trade. Approved-family review links return to the family page rather than a nonexistent instrument detail.

The expiry form now requires an approved-family selection. Underlying and currency are inherited read-only. The server verifies family ID, code, underlying, currency, active status and tenant ownership on submission and again at approval. Pending families are unavailable for selection. Duplicate tenant codes are rejected transactionally under the same identity lock used by expiry creation. Separate months can reuse a family; duplicate family/month expiries remain prohibited.

API additions: `POST /v1/future-family-proposals` and paginated `GET /v1/future-families`. The browser uses trusted-tenant BFF routes and the existing expected-tenant write guard. No database migration is needed. The earlier API flow without `familyId` remains compatible and can still create a family implicitly; the frontend no longer uses it. Existing tenant families created by that flow are selectable.

Family identity currently governs underlying and contract currency only. Exchange-specific tick, monetary multiplier, quote divisor, trading cutoff, final settlement and source rules remain explicit per-expiry conventions. Family-level default inheritance, editing/retirement screens, physical and non-index futures, and valuation are not included.

Verification for this increment: lightweight family validation passed first; the isolated family/booking regression run passed **29 tests**, including pending exclusion, standalone non-tradable creation, duplicate conflict, tenant isolation, forged identity rejection and reuse by two expiries. Frontend verification passed **306 tests across 84 files**, including selector paging, complete-family selection and error display. Final production build, TypeScript compilation and API export consistency passed. Tests used disposable databases, not operating trades.

Browser verification created and approved the synthetic family `UI_FAMILY_20261002` through the actual form and Operations queue, followed the approved-families link, then selected it in the expiry form. The inherited USD currency and governed S&P 500 underlying were displayed read-only. Proposal: `01a0fb66-c70b-7e3a-b3b6-933b9ae1c160`; family reference node: `01a0fb67-1e8a-7aa4-b266-f87b2650f6db`. This browser record exists only in the retained isolated demo database; no operating record was created. Screenshot: `C:/Users/forte/Documents/ChatGPT/Tech V2/futures-family-acceptance.jpg`. Operating and synthetic API/UI processes were restarted on ports 8000/3000 and 8001/3001. Operating users may need to reselect their tenant following session-key rotation.

Funded notes/certificates support nominal quantities with percentage quotes, units with monetary quotes, and units with percentage quotes and an explicit denomination. Quote conversion applies once. Quantity minimum and increment are governed. Prices use no-accrual or dirty/all-in treatment; an actual security settlement date is entered, without a guessed T+2 default or substitution of maturity. OTC requires a counterparty and approved instrument-level OTC conventions. It uses no reference listing and invents no venue. An ISIN is independent of that route. One parent security trade is persisted; its payoff components are not separate trades.

Cash-settled conventional index futures support an exact expiry/listing and one outright fill. Quantity is a positive integer contract count. The sourced monetary point multiplier, quote divisor, tick and trading cutoff govern execution. Zero quotes are supported; negative quotes require explicit approval. OPEN/CLOSE records intent only, without checking available holdings. Final contract settlement is displayed separately; no purchase-settlement date is stored. Contract month must match the final-settlement month in this alpha.

For example, GBP 100,000 nominal at 98.5% gives GBP 98,500 consideration. Two futures contracts at 6,000 points with USD 5 per point give USD 60,000 reference contract value, **not a purchase payment or margin requirement**. CME's product page illustrates sourced multiplier/tick conventions, while its [margin guidance](https://www.cmegroup.com/education/courses/understanding-the-benefits-of-futures/the-benefits-of-futures-margins) distinguishes futures margin from a purchase down payment. These sources were reopened on 2026-10-01; their market facts are examples, not universal defaults.

## Persistence and safeguards

Revision `20261001_56` adds `secm.instrument_booking_convention`: approved actor/time, effective date, instrument, version and a closed typed payload. A database trigger rejects updates/deletes; amendments append versions. Effective-as-of selection orders by effective date then version. Historical master reconstruction across arbitrary instrument-definition amendments is not claimed; current approved projections must agree, otherwise booking fails closed.

Product writers require the trusted active tenant, membership, module/write permission, valid strategy, current approved instrument/listing, active references and matching terms fingerprint. Product dates cannot be changed through a convention amendment to silently create another futures expiry. Relevant booking references are locked during persistence. Tenant/endpoint replay locks ensure concurrent identical retries create one trade, while conflicting payloads return a conflict. Reviewed retries keep the original payload, key and tenant. Invalid annotations roll back the whole booking.

The generic cash writer and its selection UI reject structured products and futures. The alpha P&L endpoint rejects strategies containing these unsupported products rather than returning a partial cash-only total. No new daily valuation, margin, cash-posting or settlement automation was added.

## Verification evidence

Lightweight exact-decimal rules preceded integration and UI work. Final frontend verification passed **303 tests across 83 files**, production compilation and TypeScript checking. The final isolated Python product/rules/migration run passed **46 checks**, covering listed versus OTC execution, identifier search independent of route, unit/nominal calculations, zero and approved negative quotes, private-reference visibility, module refusal, stale snapshots, concurrent replay, append-only convention records, annotation rollback and offline/online migration reconciliation.

The first complete Python suite returned 467 passed and one failure in the earlier bond migration's offline SQL generation. Revision 54 attempted live inspection on an offline connection. The fix preserves online compatibility validation and emits the clean migration path in offline mode; it does not weaken live reconciliation or rewrite existing bond values.

The subsequent complete Python rerun returned **473 passed and six migration-harness failures** in 645 seconds. Those six tests invoked the corrected migration without an Alembic online/offline context. The harness was corrected while that run was in progress; all six subsequently passed, together with the offline SQL test, and were included in the final 46-check isolated run. This is full-suite execution plus focused repair verification, **not a claim that one final full-suite invocation was entirely green**. Existing SQLAlchemy/Starlette deprecation warnings and a Pydantic schema warning during concurrent request construction remain warnings, not hidden failures.

API export checking passed. The standard generated-contract check compares against Git HEAD, so it reports the intentional uncommitted contract additions in this dirty feature branch. Regeneration with before/after hashes confirmed reproducibility; no commit was made to manufacture a clean check.

Synthetic browser verification used the retained isolated database `fortem_fx_signoff_d07737a03c2b43eca72b74953fe0b44b` and ports 8001/3001. It booked SELL/CLOSE two futures at 6,000 with a custom numeric zero, reviewed/back-edited, and persisted USD 60,000 reference value, no payment direction, no settlement date and CLOSE intent. Trade: `0337d57d-a068-408f-8eab-60bd21f703b2`. It also booked an OTC funded note: BUY GBP 100,000 nominal at 98.5%, settlement 2026-10-05, Bank A Demo counterparty, zero custom property; history retained PAY GBP 98,500, route OTC, no listing and one BOOKED event. Trade: `e3a7a69a-77ed-4046-ac2a-2baf21308050`. These are simulations, not executed market orders or operator-database trades.

The browser also submitted and approved a new June 2027 future through the actual creation form and Operations screen, then followed the approved-instrument and convention links. Its no-listing convention inspection displayed the exact month, multiplier, tick and dates without implying OTC execution. Proposal: `01a0f95c-1942-7080-ab24-27f250c783e7`; instrument: `01a0f95e-3dd5-79cf-b75e-949a8a0845f3`. Proof images: `C:/Users/forte/Documents/ChatGPT/Tech V2/product-future-creation-acceptance.jpg` and `C:/Users/forte/Documents/ChatGPT/Tech V2/product-conventions-acceptance.jpg`.

## Local activation and data preservation

A read-only legacy audit found zero existing operating trades on STRUCTURED_PRODUCT or FUTURE instruments, resolving subjects through both canonical instruments and listings. No historical cash-shaped product booking needed reconciliation.

The operating database was backed up to `C:/Users/forte/Documents/ChatGPT/Tech V2/local-db-backups/fortem_secm_pre_product_booking_20261001.dump` (2,157,970 bytes), then upgraded additively from revision 55 to 56. Before and after counts were **9 trades and 271 instruments**. No operating trade was booked, rewritten or deleted, and no product conventions were seeded there. API/UI ports 8000/3000 were restarted on the final build; the operating futures booking page was verified in a fresh demo-tenant session. The synthetic browser tab was closed after evidence capture. No commit or push was made; unrelated existing changes were preserved.

## Deferred and manual checks

For the latest futures completion boundary, sample seed, and distinction between listing conversion and contract monetary multiplier, see [Futures creation and contract conventions alpha](futures-creation-and-contract-conventions-alpha.md). The cash-settled index booking slice and multiplier-label UX follow-up are implemented and browser-verified. Daily positions/exposure and the full futures lifecycle are not delivered by booking alone. The subsequent [bond booking alpha](bond-booking-alpha.md) reuses this workflow with nominal quantities and explicit accrued-interest confirmation; it does not extend valuation.

Bilateral structured derivatives, clean prices needing accrued-interest calculation, cross-currency security settlement, physical or non-index futures, spreads/packages and average-price allocation remain deferred. Clearing broker/account information can use existing governed properties; no clearing-account master or clearing acknowledgement is claimed. Positions, actual close availability, lifecycle events, delivery, variation margin, market data and valuation require separate modules.

The existing native cross-product discard-dialog limitation in the embedded browser remains a manual check; this work does not claim to resolve it or disable the guard. Automated frozen-retry and stale-term state checks cover the new ticket. Product-specific operator walkthrough and realistic term-sheet sampling remain recommended before production acceptance. UI density remains an alpha tradeoff, not a completed UX redesign.
