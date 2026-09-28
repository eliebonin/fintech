# Exchange-traded product onboarding

## Scope

The ETP workflow covers the economic instrument wrapper types `ETF`, `ETC`,
`ETN`, `ETV`, and `ETI`. It does not create a venue listing. A listing remains
a separate economic-to-venue record containing the venue symbol, trading
currency, listing-level identifiers, quote factor, and unit multiplier.

The existing `secm.etp_terms` table is reused. No ETP-specific migration is
needed for this slice.

## Frontend capture boundary

The manual-first form captures facts that an Operations user can normally know
from a prospectus, KID, factsheet, or trusted provider:

- canonical name and optional platform internal code;
- effective date and optional ISIN;
- ETP kind;
- legal form;
- replication/exposure method;
- collateralisation or issuer-credit basis;
- redemption lifecycle;
- distribution policy;
- optional issuer organisation;
- optional economic/base currency; and
- optional primary reference node selected from a live canonical search.

The form does not ask the user to guess detailed provider fields, constituent
weights, creation-unit mechanics, market-maker arrangements, or complete
prospectus disclosures. Those remain enrichment or later specialist workflows.

## Reference relationship

When a user selects an index, commodity, basket, or strategy, the API writes the
relationship to `secm.instrument_relationship` and also stores the optional
`secm.etp_terms.reference_node_id` shortcut. The relationship is authoritative
when more than one reference exists.

The initial role mapping is:

| ETP kind | Default relationship role |
|---|---|
| ETF | `TRACKS_INDEX` |
| ETC | `TRACKS_REFERENCE` |
| ETN | `REFERENCES_INDEX` |
| ETV / ETI | `REFERENCES_INDEX` |

These roles remain controlled vocabulary work for a later catalogue hardening
slice; they are not free-text input on this form.

## Regulatory and market-practice checks

The form reflects several distinctions found in official guidance and issuer
disclosures:

- An ETF is a fund or share class traded throughout the day on a trading venue
  with a market maker and is not interchangeable with an ETN or ETC.
- An ETC is generally a debt/certificate-style product linked to a commodity or
  commodity index, with collateral and issuer-credit terms that need separate
  treatment from a UCITS fund.
- An ETN is a debt obligation whose repayment follows a reference asset or
  strategy and carries issuer credit exposure.
- A single economic product can have multiple listings, currencies, tickers,
  and listing-level identifiers.
- A tracking or benchmark index must identify the concrete return variant where
  that distinction is known; the form therefore links to the canonical index
  node rather than accepting a ticker or free-text benchmark.

Sources: [MiFID II ETF definition](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mifid-ii/article-4-definitions),
[ESMA ETC classification guidance](https://www.esma.europa.eu/publications-data/questions-answers/1275),
[ESMA UCITS benchmark disclosure guidance](https://www.esma.europa.eu/publications-data/questions-answers/1100),
and the [iShares listing/share-class example](https://www.ishares.com/uk/professionals/en/products/251795/ishares-core-ftse-100-ucits-etf).

## Workflow and verification

```text
ETP form
  -> same-origin Next BFF
  -> POST /v1/etp-proposals
  -> pending reference-data proposal
  -> generic Operations review
  -> approval dispatches to ETP materialiser
  -> instrument + etp_terms + optional relationship
  -> separate listing workflow (now accepts ETF/ETC/ETN/ETV/ETI parents)
```

Focused coverage is in `tests/test_etp_onboarding.py` and
`src/app/instruments/etps/new/validation.test.ts` plus the browser BFF client
test. The full test suites remain intentionally out of scope for this slice.

## Deferred choices

- Index/commodity/reference relationship roles should move to a governed
  catalogue and be validated by reference-node type.
- ETF fund/share-class linking can become a dedicated enrichment panel; it is
  optional in the initial manual form.
- Primary-market creation/redemption units, APs, market makers, iNAV, hedging,
  fee schedules, collateral schedules, and regulatory disclosures need richer
  terms models before they are used for valuation or compliance controls.
- Durable idempotency remains an API command-layer concern; the browser key is
  currently transport support only.
