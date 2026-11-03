# Regulatory Reporting workspace

Status: accepted implementation scope · 29 October 2026

## Purpose and boundaries

Introduce the REGULATORY_REPORTING module with UK MiFIR transaction-report
preparation as its first workflow. Reporting is assessed against a tenant-owned
legal-entity profile, not a strategy's FUND label or trading location. This slice
prepares and reviews execution facts and freezes a manual preparation export. It
does not submit reports, assert FCA schema acceptance, or implement EMIR/Annex IV.

The current receiving channel is unconfirmed. Therefore the export is explicitly
PREPARATION_ONLY, not a regulator submission file. Passing preparation checks is
not complete RTS 22 validation. Full official field applicability, current XSD
serialization, acknowledgements and cancellation/resubmission follow separately.

## Behaviour

- Platform administrators enable the module; tenant administrators grant explicit
  REPORTING_READ, REPORTING_PREPARE, REPORTING_REVIEW, REPORTING_EXPORT and
  REPORTING_CONFIGURE actions. Operational admin status grants no bypass. The four
  report actions are strategy-scoped; configuration is tenant-wide.
- Entity profiles contain a legal name, LEI, firm category, assessed firm scope,
  assessment rationale and version. Profile changes retain immutable history.
  Regulatory status is explicitly assessed; no category alone confirms liability.
- Prepare executions for one chosen profile/strategy and an inclusive UTC date
  range, without a trade-count cap. Keep all families and event/status facts;
  unsupported/missing mapping remains visible for assessment. Never use positions
  or valuation-effective dates to select execution reports.
- Preserve exact execution quantity, unit, price, price currency, timestamp,
  lifecycle status and frozen BOOKED terms. No float conversions, midnight dates,
  inferred decision-maker identity, fabricated ISIN, venue or nominal conversion.
- Separate reportability (REPORTABLE/NOT_REPORTABLE/NEEDS_ASSESSMENT), preparation
  readiness (READY/INCOMPLETE) and disposition (AUTO/HOLD). An explicit assessment
  can override a proposal in either direction with a reason. Hold requires a
  reason; returning to automatic restores the current generated proposal.
- Controlled mapping fields can be amended with a reason: instrument ISIN,
  buyer/seller reporting IDs, capacity, actual venue MIC and investment/execution
  decision IDs. Generated economic facts cannot be edited in this workspace.
- Repreparation retains human decisions/mappings, creates a new revision if
  execution/profile evidence changed and flags that reassessment is necessary.
  Old revisions and exported files never change. Cancelled/superseded executions
  cannot quietly be exported as fresh transactions.
- Filter and paginate on the server. Show totals for the complete permitted
  population. Page selection is transient and never changes inclusion.
- Freeze all currently ready/reportable/non-held rows in the selected scope.
  Blocked, held and non-reportable counts remain in the export manifest. A partial
  export is not completion of the reporting day. Re-export requires a stable
  idempotency key; retained download rechecks current rights for every member.
- Export revalidates current profile, execution and report revisions. Source
  changes require repreparation. A new export supersedes no old submission.

## UX

Menu: Regulatory Reporting. Pages/tabs: Transaction preparation, Reporting
entities, Export history. Use readable instrument/strategy names and separate
status columns, with evidence IDs inside disclosures. Put a concise how-to at the
top. Explain empty configuration, denied access and preparation-only exports.
No operational reports, permissions or submissions are created by migration.

## Sources and decisions

Research: [reference implementation review](../../research/transaction-reporting-reference-20261029.md).
Reopened 29 October: [FCA scope](https://www.fca.org.uk/markets/transaction-reporting),
[SUP 17A](https://handbook.fca.org.uk/handbook/sup17a),
[PERG 13 Q43](https://handbook.fca.org.uk/handbook/perg13), and
[MDP current/future interface distinction](https://www.fca.org.uk/markets/market-data-processor).
These establish regulatory boundaries, not our local READY label or UI design.
[Carbon tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines)
supports explicit row actions and progressive disclosure. No 2028 draft rule is
applied to current transactions. Accepted production reports will later supply
regulatory comparison cases; synthetic tests establish local workflow behaviour.
