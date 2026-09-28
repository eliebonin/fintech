# Module 3 — OTC and structured-product lifecycle hub

## Commercial proposition

Provide a canonical lifecycle and control hub for OTC derivatives, structured notes, and bespoke products. It gives operations, portfolio management, risk, and valuation teams one explainable economic record without forcing replacement of the existing OMS, administrator, or accounting system.

This is Fortem's strongest differentiator because it combines product knowledge with operational control: swaps, FX forwards, options, futures, credit products, autocalls, Phoenix/Athena products, supertrackers, range accruals, AMCs, and composed options.

## Design boundary

The hub stores the internal canonical economics. FpML, FIX, confirmation PDFs, custodian records, and administrator files are boundary payloads retained with mapping lineage; their layouts are not copied into the internal relational model.

FpML is valuable for integration because it covers OTC product and lifecycle processes across rates, FX, credit, equity, commodities, securities, and loans. [ISDA FpML](https://www.isda.org/isda-solutions-infohub/fpml/)

## Core workflows

```text
confirmation / booking feed / manual request
  -> source payload retained
  -> extraction and mapping proposal
  -> operations validation against canonical reference data
  -> canonical instrument and trade/event record
  -> confirmation difference / incomplete-term exceptions
  -> lifecycle event processing and valuation evidence
```

Lifecycle examples:

* swap reset, coupon, financing payment, and termination;
* FX forward settlement and roll;
* option exercise, expiry, assignment, and barrier event;
* structured-product coupon observation, autocall, knock-in, maturity payment;
* amendment, increase, partial termination, novation, and correction.

## Economic model

```text
instrument
  instrument_type = SWAP / OPTION / STRUCTURED_PRODUCT / COMPOSED_OPTION

swap_terms / swap_leg
  legal contract terms; each leg references a generic reference node

option_terms
  underlying, put/call, exercise style, strike, settlement, quantity

instrument_composition
  parent instrument, signed component rate, role, effective date

barrier_rule
  owner instrument or payoff component, role, direction/effect,
  level basis/value, observation style/schedule, underlying scope

instrument_schedule / schedule_event
  coupon, reset, observation, payment, fixing, valuation dates

trade
  one booked economic event; related cash events point to originating instrument

trade_external_reference
  confirmation, source trade ID, agent/custodian and lifecycle references
```

The legal/economic parent is one instrument for an OTC composed option or structured note. Its composition exposes the payoff components; it does not require booking artificial child trades. A listed strategy is different: separate listed contracts may be booked as distinct trades and optionally grouped operationally.

## Controls

* Required-term completeness by governed instrument type and taxonomy.
* Confirmation-versus-booking comparison with field-level tolerances.
* Versioned terms: corrections do not overwrite prior known economics.
* Maker/checker approval for booking, material amendment, and lifecycle resolution.
* Calendar and schedule validation, including business-day convention checks.
* State-machine controls for events such as autocall determination, coupon eligibility, and settlement.
* Valuation input provenance via Module 1 rather than embedded price fields.

## APIs

```text
POST /v1/otc/source-documents
POST /v1/otc/extraction-proposals
POST /v1/instruments/{id}/approve
POST /v1/trades
POST /v1/trades/{id}/lifecycle-events
GET  /v1/instruments/{id}/economic-summary
GET  /v1/trades/{id}/reconciliation
```

The economic-summary response should be an explicit API contract generated from the canonical model. It is not a raw FpML or confirmation representation.

## MVP

Begin with three product families that reflect Fortem's credibility:

1. FX forwards;
2. two-leg total-return/financing swaps; and
3. autocall/Phoenix structured products with schedules, barriers, and coupon/autocall events.

For each, support source ingest, canonical booking, validation, lifecycle event capture, and valuation-input lineage. Defer a universal confirmation parser, full collateral management, automated legal interpretation, and every exotic payoff.

## Commercial model

Price by active OTC/structured universe, product families enabled, and integration scope. A strong first sale is a controlled deployment around an existing manual confirmation/reconciliation process, measured against operational exception reduction and reconciliation quality.

## Market evidence and positioning

The market contains established derivatives specialists: OpenGamma, for example, provides derivatives analytics across trading, risk, treasury, and operations with API-based integration: [OpenGamma](https://opengamma.com/). This validates demand but makes a generic margin/risk product a poor initial target. Fortem's differentiation is the canonical economics, confirmation validation, barrier/schedule lifecycle, and valuation control of bespoke structured and OTC instruments. FpML remains the integration boundary for standardised messages and lifecycle events: [ISDA FpML](https://www.isda.org/isda-solutions-infohub/fpml/).

See [market evidence and go-to-market](06-market-evidence-and-go-to-market.md) for pricing confidence and design-partner gates.
