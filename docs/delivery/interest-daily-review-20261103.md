# Daily interest and accrued-balance review

**Status:** Implemented alpha; local migration 109 active  
**Reviewed:** 3 November 2026  
**Scope:** F38/F39 Ops maintenance, not P&L publication or payment accounting

Follow-up: [the independent explorer](accrued-balance-explorer-20261103.md)
now implements the deferred exploration described below. The maintenance
workflow and financial controls remain unchanged.

## Current workflow

This supersedes the 1 November three-tab maintenance UI. Both pages use one
strategy and one value date; exploration is deferred for a separate discussion.

1. `/valuation/interest`: review the full relevant bond population's local daily
   interest, compare the normalized daily rate with the previous five calendar
   days, assess corrections and bulk validate.
2. `/valuation/interest/balances`: available only after the current daily review
   is validated. Inspect opening stock, the daily increment, trade/coupon bridge
   evidence and proposed closing stock; assess overrides and bulk validate.

Monday normally covers Saturday–Monday. Explicit weekend entries shorten that
default to avoid double-counting. Ops can set 1–31 covered days for holidays or
other source conventions. Historical amounts are spread across covered calendar
days **only for comparison**; actual earned amounts remain unchanged. Baselines
exclude the current coverage interval, show known-day coverage and leave missing
or overlapping days unassessed. The fixed ±25% check is informative, not a blocker
or a pricing model; trades and floating rates can explain differences.

## Decisions, gaps and financial effects

An unknown amount must either be supplied with a source/reason or explicitly
acknowledged with a reason. Acknowledged gaps produce **Reviewed with gaps**;
they allow balance review, remain unknown and create no zero-valued financial
input. Known values cannot be hidden as missing. Daily gaps remain disclosed on
the balance page. An independently sourced closing stock can be assessed even
when its daily bridge is incomplete; this does not invent daily income.

Row edits first change a local draft. **Save & check** retains a review revision
without changing native financial inputs. Bulk validation covers every row,
including other pages, and atomically writes assessed native inputs, the review
receipt/items and audit. Balance validation explicitly rebuilds that day's
maintained history. Neither stage publishes valuations or books cash.

Coupon/principal schedules provide contextual notices. A schedule does not
confirm payment or silently reset a stock. Ops assesses any required closing-stock
correction, preserving new-period interest. Automatic accounting and receivable
management are outside this change.

## Implementation and controls

- [Domain orchestration](../../valuation/interest_review.py),
  [comparison model](../../valuation/interest_review_model.py) and
  [command contracts](../../valuation/interest_review_contracts.py) sit below HTTP.
- [Migration 109](../../alembic/versions/20261102_109_interest_review.py) adds
  append-only `nav.interest_review` and `nav.interest_review_item`: typed exact
  amounts, scope/date/stage/revisions, row/gap counts, decisions, covered days,
  native source links, original/proposed proof, actor/operator and timestamps.
  Database guards enforce scope, source agreement, immutable population and the
  daily prerequisite. JSON evidence supplements typed numbers.
- [API](../../apps/reference_api/interest_review_routes.py) GET requires scoped
  `VALUATION_READ`; POST requires scoped `VALUATION_REVIEW`, with the existing
  module and data-display gates. Calculation permission is not required. No user
  or group grants are introduced. The BFF preserves verified context.
- Native source signatures, ledger event identities, schedule versions, comparison
  receipts and full-population hashes reject stale review. The post-write proof
  permits only the command's own new source revisions; concurrent position or
  schedule changes are rejected. Balance changes do not invalidate their own
  daily prerequisite. Source changes require refresh/review.
- Exact idempotency keys bind actor/operator and command bytes. Uncertain writes
  require explicit unchanged retry. Only read-only HTTP 429 responses receive
  bounded abort-aware Retry-After retries; workload limits remain enforced.
- [UI](../../apps/ops-console/src/features/valuation/interest-ops-review.tsx)
  uses contextual native dialogs, protected drafts, local errors, an explicit
  whole-population confirmation, 25/50/100/All pagination and progressive proof
  disclosure. There are no page-specific links forwarding Ops to P&L valuation.

## Verification and activation

- 27 focused backend tests passed in an owned disposable database: the new model,
  contracts, API and integration tests plus existing balance-history API and
  integration checks. Includes permissions without calculation access, scope,
  draft isolation, acknowledged gaps, exact receipts, full-population/stale-source
  rejection, audit rollback and deferred database guards.
- 51 frontend tests passed across nine focused files, including loaded review
  tables, editor, exact inputs, read retries, help, retained transport and BFF;
  TypeScript `--noEmit` passed. No full project regression was run.
- Migration 109 applied locally; API 8000 and frontend 3001 restarted. Browser
  checks use FCAGF/20 October 2026 read-only: data loaded, row editor opened and
  closed, whole-population confirmation opened and cancelled, and direct balance
  navigation rejected until daily validation. A stale development-module help
  hydration mismatch cleared after frontend restart; the fresh balance load had
  no browser warning/error. No operating review was validated or financial input
  changed. Existing source data are proposals, not fabricated past approvals.

## Limits and remaining work

The initial review population is canonical BOND: relevant period holdings/trades
and current supplied daily inputs. This is not a separate queue for every residual
accrued stock after a holding disappears. There is no automatic interest model,
holiday-day inference, tenant-configurable diagnostic threshold, scheduled batch,
workbook upload or background notification service. Existing native ingestion
APIs remain available; review receipts are not retroactively assigned to imports.
Historical source collection is bounded to 40 days for the diagnostic. Manual
refresh/revalidation detects changes; this is not a real-time push interface.
Exploration/chart navigation and broader operational populations remain follow-up
work. F38 remains PARTIAL and F39 ALPHA.

## Design references

The [GOV.UK task-list guidance](https://design-system.service.gov.uk/components/task-list/)
informs explicit stages and dependency/status labels. The
[check-answers pattern](https://design-system.service.gov.uk/patterns/check-answers/)
informs review/correction before a consequential bulk action.
[Carbon data-table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines)
informs table toolbars, contextual row actions and progressive disclosure. These
are interaction references; the five-day/25% diagnostic and acknowledged-gap
policy are project decisions, not regulatory standards. Native dialogs retain
focus/close semantics; dense technical proof stays secondary to business amounts.
