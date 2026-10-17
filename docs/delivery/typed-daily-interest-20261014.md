# Typed daily earned interest — 14 October 2026

Status: implemented, focused-test verified and locally activated with approval. Migration 93 is applied and the API restarted/healthy. The operating accrual table contained zero rows; no interest entries were created. Populated backfill preservation was verified separately in disposable databases.

## Required economic record

`nav.daily_accrual_input` now models the following explicit non-null columns:

| Column | Meaning |
| --- | --- |
| `tenant_id`, `strategy_id` | Ownership and position scope |
| `value_date` | Date interest was earned |
| `instrument_id` | Canonical bond reference |
| `daily_earned_interest NUMERIC(30,12)` | Signed earnings for that day, not accumulated interest |
| `currency_id` | Currency of that daily amount |

Identity, revision/supersession, actor/time, request keys and hashes remain. JSONB retains supplementary balances/movements, assessed nominal, methodology/source descriptions and FX evidence. Exact daily amount/currency are also retained in the source package for hash/audit continuity; a DB constraint prevents disagreement with typed columns. Valuation reads the typed amount/currency, not an untyped replacement amount from JSON.

## Submission and valuation

The existing API accepts a minimal `strategyId`, `instrumentId`, `valueDate`, exact-string `dailyEarned` and explicit `currencyId`. Tenant/actor comes from trusted context. Zero is valid; absent, floating-point, nonfinite or over-precision amounts fail. Source reference, nominal and eligibility notes are optional; actor, recording time and version evidence remain mandatory system records.

Balances are optional as a group. If supplied, opening/closing/movements and policy/cut/reporting context must be complete, and the old bridge/FX validation remains. Legacy detailed requests may infer the bond's native currency when the newly introduced currency field is omitted. Detailed balances retain the native bond-currency restriction; daily-only amounts may be explicitly stated in another active currency. Supporting metadata does not automatically prove economic eligibility.

Minimal inputs defer FX conversion to the frozen calculation policy/information cutoff. Derived calculation evidence retains the selected FX and reporting amount. Missing balances are explicitly NOT_PROVIDED; no accumulated stock or receivable FX is fabricated. Only supplied earnings enter ACCRUAL; CARRY appears only when assessed receivable FX exists. Calculations using daily-only inputs retain `ACCRUED_BALANCE_NOT_ASSESSED`. They are not complete dirty valuation/full NAV.

The form accepts daily-only entries without requiring a selected policy for submission. An explicit optional reconciliation toggle enables the richer mode when pricing context is selected. Corrections and retries preserve frozen submission bodies; existing daily-only rows render without assuming balance payload fields exist. Currency/instrument entry remains UUID-based alpha UI, not a new reference selector.

## Migration and preservation

Additive `20261014_93` backfills existing validated dailyLocal/currency fields exactly. It preserves JSON payloads, input/request hashes, IDs and revisions. Values that would round or exceed NUMERIC(30,12), missing/inconsistent legacy evidence or invalid currency references fail the transaction rather than become zero or be silently relabelled. The table's transaction-held exclusive lock protects the narrowly scoped immutable-trigger suspension; the trigger is restored before commit. Failure rolls schema changes back. The migration is forward-only.

Published valuation rows are not rewritten; new recalculations use the updated input path. Existing accrual revision checks at publication remain. Source-health still does not automatically reassess every previously published result for non-trade source changes.

## Verification and limitations

Initial RED: minimal contract/API, daily-only valuation and typed writer disagreement tests failed against the old implementation. Frontend rendering reproduced mandatory balance requirements. One missing metadata column-description registration and an incorrect test opening-price date were corrected without weakening economics or input guards. Installed React server rendering was used; unavailable testing-library dependency was not installed.

Focused disposable-DB run: 36 passed, 16 existing SQLAlchemy seed deprecation warnings, including populated exact migration backfill and failed over-precision rollback with immutable trigger retained. Final review added a legacy request-fingerprint regression: it reproduced a 409 conflict and was fixed by preserving omitted-field hashing for old detailed requests. Final affected consumer/API suite: 35 passed; together with the unchanged two populated migration cases, 37 focused backend cases verified. Final frontend input/evidence/publication checks: 16 passed; TypeScript passed. API schema freshness and whitespace checks passed. No full suite, new browser walkthrough, bulk CSV uploader, operating interest entries or independent external reconciliation is included.

Author self-review retained existing authorization, source versions, exact currency/amount consistency and current-accrual publication checks. The detailed form/endpoint remain backwards compatible; explicit daily-only currency is mandatory. Data validation and correctly classified reported earnings still depend on Ops, and missing stock/receivable FX remains a disclosed limit. No commit/push performed.

[Plan](../superpowers/plans/2026-10-14-typed-daily-interest.md), [schema](../../valuation/tables.py), [migration](../../alembic/versions/20261014_93_typed_daily_interest.py), [consumer](../../valuation/accruals.py), [focused tests](../../tests/test_typed_daily_interest.py), [migration tests](../../tests/test_typed_daily_interest_migration.py).
