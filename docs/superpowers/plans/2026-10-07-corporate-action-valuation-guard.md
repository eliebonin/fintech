# Corporate-action valuation safety implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially. Owner requested planning followed directly by implementation; no further approval gate, subagents, automatic commits or pushes.

**Goal:** Prevent unadjusted historical bookings from producing silent wrong valuations after a known unit/security-changing corporate action.

**Architecture:** A dedicated guard loads canonical parents and relevant corporate-action dates in batches, then checks each active replayed booking's execution-to-close interval. It raises a safe ValuationBlocked diagnostic before price resolution or attribution staging. It does not implement quantity transformations.

**Tech stack:** Existing Python, SQLAlchemy, PostgreSQL, pytest.

**Design brief:** Original trades remain immutable. A future corporate-action replay will derive positions; until then, block affected bookings, including actions before the opening cutoff. Ignore actions unknown at the information cutoff and cancelled records. A booking demonstrably after an action is allowed. Date-only same-day ordering, missing dates or contradictory date evidence must not silently pass. Use source timezone, otherwise listing venue timezone, for business-date comparison; unknown timezone is unresolved. Retain existing recognized unit/security-changing event types and treat EX/EFFECTIVE dates conservatively: either relevant role may require replay.

## Constraints and review focus

- No production financial/data writes, rights changes, schema migration or settlement/accounting scope.
- Preserve cash/other-product exclusions and all existing valuation authority/precision controls.
- Equal timestamp and date-only same-day execution are ambiguous; block rather than infer ordering.
- Day-only closing-cutoff dates are also ambiguous; block rather than assume the event has not happened yet.
- Multiple listings of a canonical instrument share its actions; unrelated instruments do not block.
- Existing action/version/date governance is not redesigned. Historical date evidence lacks independent recorded timestamps; full bitemporal corporate-action governance remains deferred.

## Task 1: Historical corporate-action guard

Files: create `valuation/corporate_actions.py`, `tests/test_valuation_corporate_actions.py`; modify `valuation/service.py`, `tests/test_valuation_service.py`.

Interface: `action_requires_replay(executed_at, closing_cutoff, date_rows, venue_timezone) -> bool`; `assert_no_unreplayed_actions(connection, lots, closing_cutoff, information_cutoff, error_type) -> None`.

- [x] Write lightweight temporal tests: pre-execution, pre-opening, in-period, future, equal timestamp, local date, missing/conflicting date and invalid timezone.
- [x] Run lightweight tests RED; expected missing guard implementation.
- [x] Add PostgreSQL regression for a carried holding with a split before opening; expected current calculate incorrectly succeeds.
- [x] Implement guard, batched canonical/date loading and service integration; preserve immutable trade facts.
- [x] Run lightweight and isolated valuation service/storage/API/acceptance tests GREEN, including cancelled and future-recorded events, post-action execution and diagnostic identity.

## Task 2: Verification and documentation

- [x] Sequential self-review against the brief; no independent signoff claim.
- [x] Start full isolated Python regression; stop per owner's explicit instruction after focused verification, retaining partial evidence without claiming a full-suite pass.
- [x] Update delivery scope and document the guard versus deferred replay.

## Execution ledger

Pre-flight: guard consumes existing replayed BookedLot executions and listing subjects; no interface or schema changes outside valuation. Owner's instruction to plan then implement overrides extra skill approval handoffs. Existing feature checkout and sequential execution retained.

Task 1: complete — 16 lightweight RED cases and one real pre-opening split RED regression; 43 lightweight GREEN tests and 34 isolated service/storage/API/acceptance checks passed. Original trades unchanged. Missing timestamps are not silently reconstructed. Self-review confirms canonical parent filtering, recorded-action cutoff and conservative date handling; full date-version governance is explicitly deferred.

Task 2: complete — owner explicitly stopped the full run and accepted focused verification. Last retained completed full-suite progress line: 24%, no failure output, not a full-suite pass. Verified test processes stopped; exact disposable database removed with zero active connections; operating database unchanged. Scope documentation and whitespace checks completed; final lightweight rerun 43 passed in 1.18s. No merge/commit/push requested.

Ruling: finish with scoped verification rather than a repeated full suite — owner's explicit instruction due execution cost — cost: unrelated full-suite regressions have not been excluded for this patch; full regression is deferred to an integration/release checkpoint.
