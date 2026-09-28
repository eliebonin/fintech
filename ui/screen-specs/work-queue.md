# Screen specification: work queue

## Purpose

Surface the small set of items that require an operations or steward decision
before a canonical record or valuation workflow can move forward.

## Implemented first slice

- The server page requests `GET /v1/work-queue` through the BFF.
- The console renders counts for mapping reviews, Soft-NAV reviews, and
  market-data exceptions.
- Up to three pending items are shown with a category, title, detail, status,
  and reference UUID.
- Loading and API-error states remain explicit. Local development may show a
  labelled synthetic queue when the Python API is stopped.

## Queue semantics

| Category | Source condition | First action |
|---|---|---|
| `MAPPING_REVIEW` | `secm.reference_data_proposal.status = PENDING` for the tenant | Open proposal and approve/reject with reason. |
| `NAV_REVIEW` | Tenant `nav_calculation_run` is DRAFT/REVIEW/PENDING_REVIEW | Open the frozen input and valuation evidence. |
| `MARKET_DATA_EXCEPTION` | Resolver or policy records a stale/missing/ambiguous value | Open the affected series and resolve or document exception. |

The queue is a read model. Approvals and corrections remain separate
server-authoritative endpoints and are never implemented as direct queue-row
edits.
