# Share-ratio replay implementation plan

> Execute sequentially with superpowers:executing-plans and test-driven-development. User has asked for implementation without further plan approval, no subagents and focused tests.

**Goal:** Transform holdings for reviewed share-ratio events without mutating booked trades.
**Architecture:** Immutable replay decisions in security master feed typed action facts into positions; valuation consumes transformed boundary quantities and freezes adjustments in financial evidence.
**Tech stack:** Python Decimal, SQLAlchemy/PostgreSQL, Alembic, pytest.
**Spec:** [Reviewed share-ratio replay](../specs/2026-10-13-share-ratio-replay-design.md).

## Global constraints

No legacy trade rewrites, no synthetic income, no accounting/loyalty/fractional cash inference. Scope/source/information-cutoff guards remain enforced. Preserve unrelated working changes and use the existing user-selected feature checkout. Do not commit unrelated work or run DB tests on platform_secm.

## Review focus

- Post-event sales must flatten the converted holding, not leave a false short.
- Deferred recognition must not escape unit conversion.
- Historical information cutoffs must not see new approval decisions.
- Multiple versions of one economic event must never compound ratios.
- A reviewed event must not bypass a changed/unreviewed source or complex entitlement.

## Tasks

1. **Pure reconstruction.** Add tests in `tests/test_position_split_replay.py`; observe RED for absent split contract. Add `SplitEvent`/`SplitAdjustment` contracts and `positions/splits.py`, integrate `reconstruct(..., splits=())`. Run split/reconstruction/position-attribution tests; expected all pass.
2. **Governed loading.** Add isolated tests in `tests/test_split_replay_evidence.py` for immutable decisions, approval authority, revocation, cutoff, changed source, conflicting events and unsupported fractions. Add model/migration86 and `market_data/split_replay.py` publisher/loader. Run disposable focused runner; expected all pass.
3. **Valuation integration.** Add calculation/evidence regressions; wire reviewed facts into main and daily projections, keep unrepresented-action guard, include adjustments in staged identity. Run focused service/storage/action tests. Expected neutral split P&L and retained source/quantity evidence.
4. **Activation and documentation.** Review source terms for the Air Liquide basic allocation; activate only with reviewed evidence, validate a pre-event synthetic scenario without overwriting operating trades or publishing financial results. Update feature record/register/map and guard delivery. Report precise live/test status and remaining corporate-action boundaries.

## Execution ledger

- Design reviewed against existing bridge: no price normalization is needed when boundary quantities are correct.
- Ruling: stay in the existing user-approved feature checkout and preserve dirty changes; no separate worktree, commits or subagents for this request.
- Ruling: run focused suites only, consistent with the user's explicit verification preference.
- Tasks 1–3 complete: final pure suite 64 passed (one DB case excluded); owned disposable PostgreSQL suite 109 passed; valuation frontend nine passed and typecheck passed. RED→GREEN demonstrated for reconstruction, governance, immutable sources, stale-price units, evidence UI and unreviewed successor/cancellation safety.
- Task 4 complete: migration86 applied locally; reviewed Air Liquide event activated; synthetic workaround restored through a linked correction; fresh API attempt01a136ae-297a-7bc1-8dda-c3ad4264bb69 completed and staged nine positions, with Air Liquide100→110 retained in evidence. No official publication.
- Final review: sequential author review, per the user's no-subagents instruction. Fixed unreviewed successor/cancellation removal of historical unit changes with three RED→GREEN regressions; a reviewed successor applies once, without compounding old ratios.
- Remaining boundary: complex/loyalty/fractional-cash entitlements and commercial-rights certification are not claimed. Action review remains operator-driven. Live calculation81.2s exceeded client timeout60s; retained attempt was retrieved, not duplicated.
- No commits/push/worktree creation; documentation and code remain on the existing feature checkout with unrelated changes preserved.
