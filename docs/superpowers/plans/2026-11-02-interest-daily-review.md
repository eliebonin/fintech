# Two-stage daily interest operations

## Agreed scope

One strategy and one value date. Page one reviews position-level local-currency
daily earned interest, a five-calendar-day comparison normalized for covered days,
informative deviations, sourced reasoned corrections and atomic bulk validation.
Monday normally covers Saturday–Monday; coverage remains editable for holidays or
source conventions. Normalization is diagnostic only: never divide the actual
amount recognized as earned interest.

Page two is gated by a current daily validation receipt. It shows the previous
closing stock, validated daily earned increment, other known bridge movements,
proposed closing stock, schedule notices, outlier checks, reasoned overrides and
atomic bulk validation. Review and publish are different concepts: neither action
publishes P&L. Data exploration follows later.

## Controls and implementation

1. Exact Decimal comparison model with missing/overlapping coverage explicit,
   no assumed zero or unexplained weekday/holiday interpolation. Show benchmark
   coverage and normalized/current units; use a labelled informative threshold.
2. Retained daily/balance review revisions with typed financial amounts, source
   revision identities, before/proposed/override values, covered days, reasons,
   actor/real operator and timestamps. Draft changes and validation decisions are
   distinct. One idempotency key per exact bulk intent, current authority before
   retry, full-population locking/revalidation and all-or-nothing transactions.
3. Snapshot source signatures tie balance preparation and validation to the daily
   receipt, previous stocks, relevant trades and schedule versions. Changes require
   re-review rather than approval of stale data. Unknown opening stocks stay unknown
   until supplied; Ops may provide a sourced exact closing stock with a reason.
4. Reuse native daily-input and balance-source writers and immutable history builds.
   New workflow drafts must not silently affect financial inputs. Existing imported
   source records are review proposals, not fabricated past approval decisions.
   Preserve detailed reconciliation metadata when revising existing daily sources.
5. Coupon schedules explain expected reset/drop dates without claiming payment
   confirmation or starting accounting. A reset/override needs an explicit reviewed
   stock decision; preserve any new-period interest and avoid adding income twice.
6. Replace the two-date maintenance ribbon with strategy/date. Provide clear Daily
   accrual review → Balance review pages and current status/counts. Bulk actions cover
   the complete reviewed population, never only visible paginated rows. Keep exact
   source/evidence accessible, errors local, drafts protected and retries manual.
7. Focused unit tests first, then owned disposable-database authority, revision,
   stale-source and rollback tests; read-only operating browser checks. An additive
   migration is required for retained review decisions. Do not alter operating
   sources, balances or valuations merely to demonstrate this UI.

## Status

Implemented and locally activated on 3 November; see
[delivery, verification and limits](../../delivery/interest-daily-review-20261103.md).
The agreed gap rule is explicit acknowledgement with a reason and **Reviewed with
gaps** status. Missing values never become zero. Both stages require strategy-scoped
VALUATION_REVIEW for writes, independently of calculation authority. Data exploration
is deferred; no operating source or financial result was changed for acceptance.
