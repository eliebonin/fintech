# Typed daily interest — implementation plan

Goal: expose mandatory tenant/strategy/date/bond/daily-earned-interest/currency columns while preserving immutable balance/evidence revisions.

Design: additive migration 93 introduces NUMERIC(30,12) daily_earned_interest and currency_id. Backfill existing validated dailyLocal/currency exactly, leaving JSON payload/hashes intact; reject unrepresentable legacy inputs rather than round. Currency explicitly labels the amount; minimal records require it. Legacy full balance requests may infer the bond currency for compatibility. Core daily-only submissions do not need balances, nominal or pricing context; calculation selects reporting FX under its own frozen policy. Detailed balance mode keeps current reconciled/FX checks. Missing balance/receivable FX remains unassessed, not zero.

- [x] Tests first: minimal exact/zero API input, invalid numeric/partial balance rejection, typed columns and immutable revisions, valuation from minimal input, existing detailed compatibility, typed/payload mismatch block.
- [x] Implement additive schema/backfill with immutable trigger restored in the transaction; update API contracts/writer and valuation consumers to read typed fields. Keep historical results intact.
- [x] Update existing input register for minimal mode plus optional reconciled details; preserve retry, context and authorization. Generate contracts, run focused pure/disposable-DB/frontend/type checks.
- [x] Document current schema, compatibility, unassessed balance limits and exact verification. Request operating migration/restart activation separately; no financial or permission writes.

Execution rulings: sequential/current feature checkout per user preference, no subagents/full suite/unsolicited commit. Scope confined to daily interest and its existing consumers; optional supplementary data does not imply full accrued-stock reconciliation. Apply_patch handles edits; no unrelated dirty changes discarded.

Progress: initial four backend tests RED; core/detailed writer, typed consumers and migration implemented. Focused run 36 passed, including exact populated backfill and failed-precision rollback (16 existing seed deprecation warnings). Frontend four checks and typecheck passed. Added an old request-key replay regression during final review; verification pending. Operating activation approved by user, contingent on final focused checks. Currency UUID UI remains an explicit alpha trade-off; no automatic accrual or CSV bulk workflow added.

Completion: legacy fingerprint replay reproduced RED (409), fixed, final affected suite 35 passed. Populated migration cases 2 passed on unchanged migration; final frontend 16 passed plus typecheck. Operating migration 93/API restart approved and completed, health and core-column type/nullability verified; operating accrual table had zero rows. Author self-review only, no full suite or commit/push. All four tasks above complete; [delivery](../../delivery/typed-daily-interest-20261014.md) is final evidence.
