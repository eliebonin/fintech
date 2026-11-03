# Regulatory Reporting preparation — 29 October 2026

Delivered first bounded slice of [F53](../product/features/regulatory-reporting.md).
The [instrument coverage matrix](../product/features/regulatory-reporting.md#instrument-coverage)
lists the recognised preparation types, event/lifecycle limits and the absence
of completed regulatory submission mapping for any family.
See the [specification](specifications/regulatory-reporting-workspace.md) and
[sequential implementation plan](../superpowers/plans/2026-10-29-regulatory-reporting.md).

## Ownership and workflow

`regulatory_reporting/` owns strict inputs, pure preparation checks, scoped
execution reads, retained state/revisions and export evidence. API adapters use
the existing audited router/transaction boundary. The console adds a dedicated
menu entry, server permission gate, allowlisted BFF and three focused views.

The legal-entity assessment is separate from a fund/strategy. Prepare by actual
UTC execution dates, inspect identity mappings, record a reasoned scope/hold
decision, review complete-population totals and freeze a preparation CSV plus
manifest. Repreparation preserves prior human choices but changed sources require
reassessment. Exports retain exact revisions/outstanding counts and are never
rewritten. Exported is neither submitted nor accepted.

Financial execution amounts/units and price/rate are not edited or converted into
monetary position notional. Full frozen booking terms remain in the evidence.
Reporting preparation does not modify booking/valuation or make missing regulatory
inputs block those workflows. Missing product/event mapping is visible, not a
silent non-reportability rule. OTC descriptions are permitted for preparation;
they do not replace final instrument-identity requirements.

## Activation and access

Additive migration `20261029_104` was applied to the existing local application
database. It adds schema `reg`, five retained/current tables, immutable-history/
artifact triggers, a queue index and the module catalogue entry. No tenant
entitlement or group permission was granted. No reporting profile, operating
report/export, trade or valuation was created or changed. API 8001 was restarted;
the existing frontend continues on 3001.

Final runtime checks: API health returned `ok`, OpenAPI exposes ten reporting
paths, unauthenticated profile access returns 401 and the frontend reporting route
returns HTTP 200 through its context gate. No operating reporting command was run.

To use the workspace: platform administrator enables Regulatory Reporting for a
tenant; tenant administrator assigns REPORTING_READ and the needed explicit
prepare/review/export/configure actions. Strategy scope applies to report actions.
Then open `/regulatory-reporting` and configure an assessed legal entity. There
is no implicit admin operational authority or automatic production submission.

## Verification and limits

Focused unit, disposable PostgreSQL, frontend, typecheck and isolated Edge browser
checks cover exact decimals, controlled mappings, legal-entity revisions, source
changes, cancellation, current reference/strategy denials, audit rollback,
idempotent export, server pagination and read-only UX. Tests use synthetic
reporting identities and never run the external working implementation.

The broader metadata suite exposed an existing column-documentation failure:
94 columns across existing organisation/AMC/cash/corporate-action/lifecycle tables
lack comments. All new `reg` columns are documented. This task does not claim that
unrelated metadata failure is fixed. A pre-existing Starlette/httpx test-client
deprecation warning also remains. No full Python suite or live regulatory
submission was run.

Final checks: 18 reporting unit/contract cases, six shared permission cases and
two repository-content cases passed (26 together). Eleven reporting API cases
passed in an owned disposable database; a preceding combined run also passed the
five existing strategy-scope regressions (16 together). Fifty-five focused
frontend/navigation/help/BFF cases passed. Two isolated Edge browser scenarios
passed, including pagination controls, review, whole-population export,
permission-rechecked CSV download and read-only controls. Desktop/mobile images
were inspected. TypeScript, OpenAPI freshness, generated types, new-document links
and scoped whitespace were checked. No operating report or regulatory acceptance
test was performed.

The initial scope intentionally stops short of current official schema/complete
field applicability, official instrument reportability, national-ID governance,
submission transport, acknowledgement/reconciliation and regulatory corrections.
The destination/accepted payload is still unconfirmed. See the capability record
for those explicit remaining items and the memory/scale trade-off.
