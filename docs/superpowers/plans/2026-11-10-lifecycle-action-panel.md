# Lifecycle action side-panel implementation plan

Execution: sequential in the existing checkout; user approved this design on 5 November, requested a Git checkpoint on 10 November and completion/verification/push on 11 November. No subagents or unrelated reorganisation.

**Goal:** Review, prepare and book one lifecycle event from the worklist, retaining applied filters, page and position.
**Architecture:** A wide right-hand drawer reuses BondRedemptionConsole in locked event context. Native dialog focus/escape semantics keep keyboard interaction within the drawer; the worklist remains visible behind it. The existing full-page route remains available for complex/configuration tasks. No new financial writer.
**Approved design:** the preceding discussion; use the primary-detail layout researched in the linked delivery.

## Constraints and review focus

- Same native authority, allocation, source fingerprint, idempotency and independent-review checks in both presentations.
- No prepare/post from opening a panel. Explicit Load closing inputs remains a read-only preview command.
- Filter native proposal/posting history by instrument in SQL before counts/page selection, including linked cancellation receipts. Preserve tenant/strategy authority before reads.
- Dirty close requests require discard confirmation. Busy or uncertain financial commands cannot be dismissed; retain unchanged-request identity for retry.
- Confirmed commands refresh the worklist without unmounting the active workflow; read failure never relabels a committed write as rejected.

## Tasks

- [x] Add failing browser coverage for in-page preparation, preserved filters, focus return, dirty-close protection and unchanged-key uncertain retry. Add isolated history-filter tests.
- [x] Extend scoped history reads with an optional instrumentId; export and generate contracts.
- [x] Add embedded context/command callbacks to the shared console. Implement guarded drawer and parent refresh, preserving full-page behavior.
- [x] Run focused frontend/BFF/browser/backend checks and TypeScript; inspect responsive screenshots. Update current delivery/capability documents.
- [x] Exercise direct and independently approved booking through real isolated BFF/API/PostgreSQL; fix and regress the recording-clock discrepancy exposed by acceptance.
- [x] Package the verified follow-up for commit/push to `codex/pnl-ops-review`; the final task response records the verified remote commit.

## Verification boundaries

Use mounted mocked regressions plus real full-stack acceptance in an explicitly owned disposable database, with synthetic trades/authority only there. Do not prepare, book, cancel or approve operating trades or grant operating assistance/permissions. The operating port54329 is unavailable; the owned temporary PostgreSQL container is separate. Final results and limits are in [the delivery](../../delivery/lifecycle-action-panel-20261110.md).
