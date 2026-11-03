# Transaction reporting: working reference and cross-instrument design input

**Status:** Reviewed design input; implementation not started  
**Content type:** Research and source trace  
**Owner:** Product and regulatory reporting engineering  
**Last reviewed:** 2026-10-29

## User direction and review boundary

The user supplied a working external `transaction_report_v2.py` as inspiration.
It serves their current business and must remain unchanged. The new platform
must support different instrument families and tenants without copying that
implementation's firm, custodian, product or operational assumptions.

Read the complete 666-line builder, its column catalogue, and the associated
report API and Ops screen. Static review only: no imports of external application
code, production queries, example scripts, email, uploads or submissions ran.
No personal identifiers, live LEIs or client records are reproduced here.

Source snapshot SHA-256:

- `transaction_report_v2.py`: `7d80cb60db59bdbd1e22ee1cd4f37916378f7dc82bc86cf110aac674caa5534a`
- `transaction_report_definition.py`: `13e014ca7f1d332ac31a6c177110db93bb050a2081340f5f765cd3ca22f40274`

These filenames/function names identify the user-supplied external reference;
the new product has no dependency on those packages or databases. This is not an
audit of the existing firm's regulatory compliance or the final submission path.

## Observed working flow and useful intent

| Source | Observed behavior | Intent to carry forward |
| --- | --- | --- |
| `nt_fx_reporting`, `bny_fx_reporting` | Custodian confirmations enriched with fund, party and trader references; currency amounts/rates and maturity populated | Feed-specific interpretation belongs at input boundaries |
| `_get_trades` | Execution records enriched with fund LEI, trader identity, counterparty and security data | Reuse governed trade/security/party facts rather than asking Ops to re-enter everything |
| `_default_reporting`, `_default_swap_reporting`, product wrappers | Shared output catalogue plus equity, bond, futures and several swap paths | Common report model with product-specific economic mapping |
| `run_as_category`, `run` | Rebuild one category/row or assemble the day's results | Targeted preparation/review plus whole-day completeness |
| Report API `get_report`, `update_report`, `reset_report_row`, export endpoint | Stored day view, human edits with logging, row regeneration and CSV email export | Human review, traceability and controlled regeneration |
| Ops `TransactionReportingPage` | Date selector, grouped editable grid, write permissions, reset/export actions | Familiar day-based operational review with exceptions discoverable |

The CSV column catalogue has identity type/subtype and export-specific labels.
Its column count/labels do not prove direct correspondence with one FCA schema.
Report generation and emailing demonstrate preparation/export, not regulatory
acceptance. Submission feedback and reconciliation must be established separately.

## Assumptions to replace with explicit product configuration

These are observed boundaries of a working business-specific implementation,
not allegations that its current reviewed outputs are incorrect.

- Firm/fund/custodian LEI maps and trader identifiers are configured in Python.
  New identities must come from governed, effective-dated legal-party and person/
  algorithm records with restricted access. Do not copy private maps into seeds.
- `_get_trades` selects a particular agent relationship and excludes a named fund.
  New population selection must bind reporting legal entity, tenant, applicable
  scope and source lifecycle, with documented exclusions.
- Several paths set branch countries, AOTC, transmission indicators and venue
  codes as defaults. A reporting arrangement can provide assessed defaults;
  they are not universal facts for all firms or executions.
- `_get_trades` turns some unit quantities into monetary notional; shared paths
  then export nominal quantity/percentage price. Regulatory quantity/notation
  must be mapped from actual product economics, not a generic position-value
  formula or the strategy currency.
- Generic derivatives and futures share swap/index classification defaults,
  multiplier 1 and cash delivery. Futures, options and swaps need their own
  contract identity, units and conditional fields, including physical delivery.
- Some paths use the trade date when formatting execution time, fixed decimal
  rounding and binary floats. The new implementation must preserve actual UTC
  execution timestamps and Decimal values, applying only the selected output
  specification's formatting rules. A missing time cannot become midnight.
- Missing data, spot-like exclusions and same-day maturity are represented through
  broad `active` behavior; absent columns become null. New reportability,
  field applicability, readiness and manual exclusion need distinct reasons.
- Some reference numbers use names/IDs concatenated and truncated; final merging
  deduplicates by `id`. New identity must be stable across data corrections,
  distinct across sources/entities and checked for collisions. Display-name
  changes must not change a transaction reference.
- The API edits/regenerates stored rows. The new product should retain source
  values and reviewed overrides separately, validate overrides, and preserve
  exported/submitted versions. Regeneration must not silently discard an override
  or rewrite an accepted report. A trade correction and report cancellation are
  different events.

## Recommended lightweight foundation

Use one bounded UK MiFIR preparation module first, with these separate concerns:

1. **Candidate population:** immutable execution/event facts and reporting scope,
   not current positions, valuation recognition dates or daily P&L inputs.
2. **Reporting profile:** reporting/submitting entities, client/fund relationships,
   branch/capacity/decision roles, identity sources and destination configuration.
3. **Versioned reportability and applicability:** assess firm, instrument and event;
   distinguish REPORTABLE, NOT_REPORTABLE with evidence, and UNRESOLVED. A missing
   product mapping is unsupported preparation, not proof of non-reportability.
4. **Product mapping:** translate frozen execution units, quote conventions and
   terms into a common typed report, with field-level provenance.
5. **Review:** explicit missing-field/errors queue, controlled overrides and
   regeneration, clear readiness, retained exact versions and audit history.
6. **Output boundary:** human-readable CSV/Excel and destination-specific payload
   serializer. Keep encoding/transport outside economic and regulatory decisions.
7. **Submission lifecycle:** later explicit submission, file/row acknowledgements,
   rejection reconciliation, cancellation/replacement and deadline monitoring.

This does not propose a universal multi-jurisdiction framework or automatic live
submission before the first preparation workflow is established.

## Ops inclusion and exclusion: replacing an ambiguous checkbox

29 October follow-up: the user confirms that the existing editable inclusion
checkbox is valuable operational flexibility. Preserve that discretion; improve
the meaning and evidence rather than replacing it with unchallengeable automation.
The following is a recommendation, not implemented behavior or an FCA-prescribed UI.

Keep three concepts separate:

| Concept | Example values | Meaning |
| --- | --- | --- |
| Reporting decision | Reportable / Not reportable / Needs assessment | The regulatory assessment, with rule/evidence and any reasoned Ops reassessment |
| Data readiness | Ready / Missing or invalid fields / Not applicable | Whether the applicable report fields and output validations are satisfied |
| Batch disposition | Included / Held / Not included | What goes into this particular export/submission batch; it does not erase an obligation |

Automatically include reports that are assessed reportable, complete and not
already covered by the relevant reporting lifecycle. Ops then works exceptions,
instead of individually ticking every routine row. Do not infer non-reportability
from missing ISIN/LEI, unavailable product mapping or another firm's submission.
Any transmission/exemption or alternate-route decision needs its actual basis.

Use table checkboxes for **row selection**, with explicit single/bulk actions:

- **Include in batch:** add ready reports; if Ops changes an automated scope
  assessment, retain the prior proposal and the reasoned final decision.
- **Hold:** temporarily omit a report with a reason. It remains outstanding, with
  its deadline/status visible; holding does not waive a reporting obligation.
- **Mark not reportable:** a reasoned scope decision, distinct from temporarily
  holding a report. Retain the applicable basis, user and time.
- **Return to automatic assessment:** show the proposed change and preserve the
  previous override history. Regeneration must not silently erase decisions.

An authorized operator can reassess an automated decision in either direction.
That flexibility cannot turn missing mandatory report data into valid data.
Inclusion/exclusion overrides retain who, when, reason, underlying assessment
and the report revision. Routine row selection needs no extra approval ritual;
additional review can follow the tenant's actual authority/risk policy.

Keep the workspace compact: counters/filters for Ready, Needs attention, Held,
Not reportable and reporting history; readable status labels; small row actions;
expandable field errors and decision history. A bulk action can record one common
reason where it genuinely applies to every selected row. Make page-only versus
all-filtered selection explicit; filters/pagination must not silently change
batch membership.

Illustrative outcomes:

| Row | Decision/readiness | Ops choice | Result |
| --- | --- | --- | --- |
| A | Reportable, ready | Automatic | Included |
| B | Reportable, missing required identity | Fix data | Blocked report remains outstanding |
| C | Reportable, ready | Hold pending clarification | Omitted from this batch, still outstanding |
| D | Not reportable, documented basis | Confirm assessment | Excluded with reason |
| E | Automated assessment disputed | Reasoned reassessment | Revalidate applicable fields before inclusion |

Final batch review should reconcile included, blocked, held and non-reportable
populations. Ready reports may proceed while problematic reports remain explicitly
outstanding; a partial batch is not proof the whole day is complete. Freeze the
exact exported membership and payload versions. Exported is not accepted/reported:
acknowledgements and reconciliation establish that later. Changes to submitted
reports use the appropriate correction/cancellation workflow, not an unchecked box.

Research opened 29 October:

- [FCA transaction reporting](https://www.fca.org.uk/markets/transaction-reporting)
  cites controls against over/under-reporting and regular reconciliation. These
  obligations motivate traceable decisions; they do not prescribe this override
  schema, reason list or approval arrangement.
- [Carbon data tables, updated 30 September 2026](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines)
  supports selectable rows, single/batch actions and progressive disclosure.
- [GOV.UK status tags](https://design-system.service.gov.uk/components/tag/)
  separates noninteractive status descriptions from action controls.

## Instrument coverage to design and test

The following describes architectural coverage, not a declaration that every
listed product is legally reportable or that every listed field is mandatory.

| Family | Mapping concerns |
| --- | --- |
| Equities, ETFs and quoted wrappers | Actual units, execution price/currency, security/listing and venue identity; avoid value-to-nominal conversion |
| Funds and AMCs | Actual units/nominal and quoted convention; legal owner/reporting relationship and event scope assessed explicitly |
| Bonds | Frozen nominal, execution quotation and relevant interest/consideration evidence; actual instrument identifiers and maturity |
| Fully funded structured notes | Security identity, denomination/nominal convention and applicable derivative/reference terms; keep note distinct from swap |
| Futures | Contract count, canonical expiry, multiplier, price notation, underlying and actual delivery terms; not generic swap defaults |
| Options | Contract count, premium notation/multiplier, put/call, strike, expiry, underlying and applicable delivery/exercise facts |
| Swaps | Frozen unit/notional basis, rate/price notation, actual performance reference(s), underlying identifiers, dates and relevant event changes |
| FX forwards | Base/quote amount orientation, actual agreed execution rate, currency pair and maturity; use regime-specific scope rather than one GBP or T+2 assumption |
| Digital assets, cash and economic flows | Explicit legal instrument/event classification; do not export all ledger rows or infer non-reportability from a missing adapter |

For every family, assess applicability before requiring fields. Typed product
adapters and synthetic examples should cover buy/sell, unit/notional conventions,
zero/negative permitted prices, missing identifiers, multiple references and
corrections. Missing mandatory reporting inputs block readiness for that report;
they need not block unrelated trade booking or valuation. Synthetic cases are not
regulatory acceptance; current accepted outputs can later provide comparison cases
without redefining all supported families to match one portfolio.

## Submission-channel clarification and source guidance

The user believes the existing output is uploaded directly to the FCA website.
Record this as **unconfirmed direct submission**; do not assume an ARM is required
or that the current CSV is an accepted FCA upload payload.

- [FCA transaction reporting](https://www.fca.org.uk/markets/transaction-reporting),
  reopened 29 October, identifies permitted submitters, reportability and the need
  for reconciliation/correction. It supports separating scope from file generation.
- [FCA MDP](https://www.fca.org.uk/markets/market-data-processor), updated
  2 October 2026, permits direct firm connectivity and describes onboarding and
  conformance. It lists current ITE schema/instruction packages separately from
  2028 draft materials. The full packages/MIS were not assessed in this review.
- [MDP entity portal](https://www.fca.org.uk/markets/market-data-processor/mdp-entity-portal)
  describes extracts/reconciliation, monitoring and SFTP certificate management.
  This does not verify that an arbitrary CSV can be manually submitted there.
- [PS26/15](https://www.fca.org.uk/publications/policy-statements/ps26-15-improving-uk-transaction-reporting-regime),
  read in the preceding discussion, sets the new regime's effective date as
  3 April 2028. The MDP page now lists drafts published 2 October 2026. Keep
  current production rules and future drafts separate; do not apply future
  scope exclusions to today's transactions by default.

Before freezing an implementation specification: confirm the actual portal/
destination and accepted payload, reporting-entity scenarios, identity sources,
applicable official schema/validation versions and a small anonymised set of
accepted reports/acknowledgements. These are inputs to a scoped next plan, not a
request to run or modify the existing production workflow.

## Outcome

At this research checkpoint, F53 remained NOT IMPLEMENTED. The subsequent
[bounded preparation delivery](../delivery/regulatory-reporting-20261029.md) and
[current capability](../product/features/regulatory-reporting.md) supersede that
implementation status; regulatory acceptance is still not claimed. This review supplies concrete
intent, known assumptions and cross-instrument boundaries for planning. No product
code, schema, current operational report or transport was changed; no external
runtime or full test suite was executed. Source AST parsing, local document
link/whitespace checks and two repository content-policy cases passed. These
provide static/documentation verification, not regulatory output acceptance.
