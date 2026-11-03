# F53 Regulatory Reporting

Status: PARTIAL · reviewed 29 October 2026

## Desired capability

Support applicable UK/FCA, EU and Swiss regulatory reports, with report-specific
scope, frequencies, review, submission and correction/reconciliation evidence.
UK MiFIR transaction preparation is the first implemented workflow. The module
is independent of trading/valuation entitlements.

## Implemented

- REGULATORY_REPORTING module and explicit reporting read/prepare/review/export/
  configuration actions; operational actions are strategy-scoped, with no admin
  bypass. Migration 104 registers the module without granting tenant access.
- Versioned reporting legal-entity profiles: legal name, checksum-validated LEI,
  category, assessed firm scope and reason. No FUND strategy-label inference.
- UTC execution-date preparation across all instrument/event families; exact
  booked units, quantity, price and full frozen BOOKED evidence are retained.
  Preparation is not restricted to current open positions or the first 1,000
  executions. Unknown products/events remain visible and incomplete.
- Separate reportability, local preparation readiness and AUTO/HOLD disposition;
  reasoned scope decisions, controlled identity/mapping amendments and immutable
  history. No editing execution economics from the reporting screen.
- Repreparation is repeatable, preserves human mappings/decisions, and places
  changed evidence back into Needs assessment. The prior choice remains retained
  and can be reconfirmed. Cancelled sources cannot become fresh ready reports.
- Server filtering/pagination and complete-population totals, version-checked
  export preview, frozen preparation CSV/evidence and idempotent export replay.
  Current strategy/reference rights are checked on retained download/replay.
- `/regulatory-reporting`: Transaction preparation, Reporting entities and Export
  history, readable instrument names, explicit status/action labels, top how-to
  and controlled inspection. Financial facts remain read-only.

## Instrument coverage

The following are **recognised classifications for local preparation**, matching
`SUPPORTED_FAMILIES` in [the assessment code](../../../regulatory_reporting/assessment.py).
They share the current baseline checks; this is not a set of completed
product-specific FCA mappings. **No instrument family currently has a validated
FCA submission serializer in this module.**

| Instrument family | Recognised type codes | Retained preparation facts |
| --- | --- | --- |
| Equities | `EQUITY` | Booked quantity, execution price/currency and timestamp. |
| ETFs / exchange-traded products | `ETF`, `ETP` | Actual booked quantity and price basis; listing identity remains in evidence. |
| Funds / fund share classes | `FUND`, `FUND_SHARE_CLASS` | Recorded units/nominal and execution quotation; no valuation-NAV substitution. |
| Actively managed certificates | `ACTIVELY_MANAGED_CERTIFICATE` | Recorded AMC booking basis and frozen terms; not reclassified as a fund or bond. |
| Bonds | `BOND` | Recorded quantity and quote basis, including frozen conventions; no automatic reporting-unit conversion. |
| Structured products / notes | `STRUCTURED_PRODUCT`, `STRUCTURED_NOTE` | Whole booked product and frozen terms; not flattened into an equity or swap. |
| Futures | `FUTURE` | Recorded quantity basis, execution price and frozen contract/multiplier terms. |
| Options | `OPTION`, `VANILLA_OPTION` | Recorded quantity, premium quotation and frozen option/multiplier terms. |
| Swaps | `SWAP`, `GENERIC_SWAP` | Frozen unit/notional basis and execution quotation; no forced conversion to monetary notional. |
| FX forwards | `FX_FORWARD` | Booked amount/rate and frozen currency-pair/orientation terms. |

Eligibility for a preparation export still requires assessed firm scope, an
explicit REPORTABLE decision, complete local mappings/evidence, BOOKED lifecycle
state and a supported event. The current event allowlist is `INVESTMENT`,
`SUBSCRIPTION` and `REDEMPTION`; inclusion in that list does not establish legal
reportability. Exact amounts and frozen terms are retained by
[the execution reader](../../../regulatory_reporting/source.py), not transformed
into all final regulatory fields.

Other classifications, including direct digital assets and cash, can appear in
the prepared population but remain incomplete with `productMapping` unless their
actual type code is recognised above. Dividends, coupons, resets and other
unmapped event types remain incomplete with `eventMapping`. Cancelled,
superseded or other non-BOOKED lifecycle states require `lifecycleReview` and
cannot be exported as fresh ready reports. None of these gaps automatically
classifies a transaction as NOT_REPORTABLE.

The [unit cases](../../../tests/test_regulatory_assessment.py) exercise the ten
main family classifications and baseline-check behaviour. They do not establish
regulatory acceptance, every alias or full end-to-end acceptance for each family.

## Deliberate limits, trade-offs and remaining work

- **Preparation only.** No accepted FCA/ARM submission file or connectivity,
  acknowledgement handling, regulatory cancellation/resubmission or daily
  completion certification. Repeated preparation exports are allowed; they are
  not successive NEW regulatory submissions.
- **Local baseline checks.** READINESS=READY means preparation checks passed,
  not complete RTS 22 applicability, identity, instrument or XSD validation.
  Native current-regime product serializers, all applicable report fields,
  deadlines/business-day schedules and regulator reconciliation remain to build.
- **Manual scope/mapping.** No authoritative instrument-scope feed is connected;
  firm scope is explicitly assessed and instrument/event scope needs review.
  An ISIN/listing or missing adapter never proves either scope direction.
  Buyer/seller and investment/execution decision identities must be explicitly
  supplied; the booking account is not silently reused. Identity type/country/
  national-ID governance and entity-master binding are not complete.
- **Product breadth.** All execution families retain their actual frozen terms;
  this is not certified regulatory mapping for every product. Missing ISIN can
  use an OTC description for preparation, without asserting that it is sufficient
  for final reporting. Unmapped lifecycle events remain incomplete, not excluded.
- **Scale and UX.** One entity/strategy/date range per command; no trade count
  cap, but preparation/export currently materialise the scope in memory. Only
  synthetic small/mid-sized fixtures are verified. Bulk review, cross-strategy
  batches, background jobs and automated scope enrichment remain later work.
- **Security/operations.** The existing local identity transport is not production
  authentication. No tenant access, real profiles, reports or submissions are
  seeded automatically. LEI checksum is not a live GLEIF status check.
- EU, Swiss, EMIR, AIFMD/Annex IV and other regulatory reports remain unimplemented.
  Future 2028 UK draft rules are not applied to today's preparation.

## Evidence

[Specification](../../delivery/specifications/regulatory-reporting-workspace.md),
[delivery/verification](../../delivery/regulatory-reporting-20261029.md),
[research and external working-reference intent](../../research/transaction-reporting-reference-20261029.md),
[implementation map](../feature-implementation-map.md).
