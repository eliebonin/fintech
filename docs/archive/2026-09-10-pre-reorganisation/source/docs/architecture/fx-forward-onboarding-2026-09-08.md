# OTC FX-forward onboarding (2026-09-08)

## Decision

An actual bilateral FX forward is one economic `INSTRUMENT` node. It is not
an FX quote curve and it does not require a venue `LISTING`. The implementation
uses the existing canonical tables; it adds no new PostgreSQL table or
migration.

```text
financial_reference_node (INSTRUMENT)
  └─ instrument (instrument_type = FX_FORWARD, asset_class = FX,
                 base_currency_id = GBP)
       ├─ instrument_dates (effective, maturity, settlement)
       └─ fx_forward_terms (GBP/USD, USD_PER_GBP, agreed rate,
                             settlement type, optional fixing currency)
```

The Fortem-generated UUID remains the identity. `internal_code` is an optional,
unique operational code. Provider, bank, custodian, and counterparty IDs belong
in the existing integration/external-mapping layer and are not used as the
primary key.

## Contract semantics

The form requires:

- canonical name;
- effective-from date;
- base currency;
- quote currency;
- explicit quote convention, for example `USD_PER_GBP`;
- positive agreed forward rate in that convention;
- settlement type (`DELIVERABLE`, `NDF`, or `CASH`); and
- maturity date.

Settlement date, cash-settlement date, final-settlement date, and an NDF fixing
currency are optional because confirmations may not provide every date at the
first capture. When supplied, dates are checked so they do not precede
maturity. The final settlement date is populated from the explicit final,
cash-settlement, or settlement date in that order; no date is invented when
none is supplied.

`base_currency_id` is the contract's economic/first currency and is stored on
`secm.instrument`. `quote_currency_id` and `quote_convention` are stored on
`secm.fx_forward_terms`. There is intentionally no generic
`quantity_currency_id`: quantities and notionals are trade-level facts and
must not leak into the common instrument model.

A counterparty monetary MTM such as `USD -2,145.80` is not the agreed forward
rate. It belongs in a later valuation-mark or market-data workflow, with its
own currency and provenance. The current onboarding slice does not derive or
persist that mark.

## Workflow

```text
manual form
  -> POST /api/instruments/fx-forwards (Next BFF)
  -> POST /v1/fx-forward-proposals
  -> PENDING CREATE_FX_FORWARD proposal
  -> reference-data review queue
  -> generic or FX-forward decision endpoint
  -> atomic instrument + dates + terms + tenant scope
```

The API also supports the direct decision endpoint
`/v1/fx-forward-proposals/{proposalId}/decision`. The generic
`/v1/reference-data-proposals/{proposalId}/decision` dispatcher recognises
`CREATE_FX_FORWARD`, so the existing review screen can approve or reject it.
The work queue identifies the pair convention and maturity instead of treating
the proposal as an equity or identifier mapping.

Submission is manual by default. Automated ingestion may use the same contract
only when a source system is supplied; idempotency remains a command-layer
concern and is not inferred from a browser header alone.

## Why this boundary is appropriate

The [ISDA FX Definitions](https://www.isda.org/book/2026-fx-definitions/)
provide the documentation framework for privately negotiated FX transactions,
including forwards. Their glossary distinguishes a forward rate from the
settlement obligation, and distinguishes deliverable transactions from
non-deliverable transactions. The [BIS glossary](https://data.bis.org/help/glossary?item=Non-deliverable%20forwards)
also describes NDFs as cash-settled without physical delivery. Those distinctions
are represented here as rate convention, settlement type, fixing currency, and
separate valuation data rather than as labels on a generic price row.

## Focused verification

- `tests/test_fx_forward_onboarding.py` covers successful proposal and
  approval, queue classification, generic approval dispatch, materialised
  terms/dates, and same-currency rejection.
- `apps/ops-console/src/app/instruments/fx-forwards/new/validation.test.ts`
  covers required fields, pair direction, and positive rate validation.
- `apps/ops-console/src/lib/browser-api-client.test.ts` covers the same-origin
  BFF route.

The focused API tests pass (`2 passed`), the focused browser tests pass (`8
passed`), TypeScript typecheck passes, and the production build includes
`/instruments/fx-forwards/new` and `/api/instruments/fx-forwards`.

## Deferred choices

1. **Trade-level notionals and counterparties.** Keep them in trade storage;
   do not add them to canonical FX terms.
2. **Trade price versus MTM.** Store a contractual rate in trade/terms and a
   counterparty monetary valuation in the valuation-mark domain. A future
   resolver may derive a unit-equivalent rate for analytics, but must retain
   the original amount, currency, source, and calculation lineage.
3. **FX pair/rolling tenor curves.** `GBPEUR 1M` remains a market-data series
   (or a pair/curve reference object), not an `FX_FORWARD` instrument. That
   future slice needs pair calendars, spot lag, tenor, forward-points versus
   outright quote kind, and resolved value date.
4. **Governed quote conventions.** The current request validates a safe
   uppercase code but leaves the vocabulary free for now. A later catalogue
   can provide descriptions and pair-specific validation.
5. **Full confirmation terms.** NDF settlement-rate sources, payment
   calendars, broken dates, split value dates, fixing dates, holiday centres,
   and calculation-agent roles remain a dedicated confirmation/enrichment
   slice. The common date row is deliberately not expanded here.
6. **Correction lifecycle.** Approved terms are not edited in place. A
   corrected contractual identity should follow the platform's amendment or
   replacement policy with immutable evidence and effective dating.
