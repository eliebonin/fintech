# Composite Pricing Policy Implementation Plan

> Execute inline using executing-plans and TDD. User overrides: current checkout, sequential execution, no subagents, no auto commit/push or further plan approval. Ledger retained here instead of Git-backed skill scratch scripts.

**Goal:** Configure and preview mixed exchange closing sessions and FX fixings with reproducible input selection, without valuation/P&L.

**Architecture:** Small calendar/convention helpers extend the current resolver. Additive schema fields freeze per-item pricing evidence. A focused policy API owns immutable version configuration and read-only preview; the ops console consumes generated contracts.

**Tech Stack:** Python/SQLAlchemy/PostgreSQL18/Alembic, FastAPI/Pydantic, existing versioned calendars, Next16/React/TypeScript/Vitest.

**Spec:** ../specs/2026-10-07-composite-pricing-policy.md

## Global constraints

Preserve legacy rules/snapshots and idempotency fingerprints; no implicit NON_DISPLAY activation, source imports, financial mutations or automatic listing choice. All DB tests use scripts/run_isolated_python_tests.py; frontend edits follow apps/ops-console/AGENTS.md and installed Next guides. Add descriptions to every new column. No production/commercial activation claim.

## Review focus

Unknown calendar dates must not silently become weekdays; ambiguous/nonexistent local times must fail explicitly. Missing specific rules cannot fall through. Daily bars cannot masquerade as intraday/fixing marks. Policy scope, strategy ownership and dataset permissions must be revalidated. Old snapshot replays must retain their frozen values and legacy fingerprints.

## Tasks

1. [x] Temporal helpers. Create market_data/pricing_conventions.py and tests/test_composite_pricing_conventions.py. Interface: local_target(day, local_time, timezone_name) -> UTC datetime; session_target(day, sessions, lag=0) -> target session; session_distance(requested, used, sessions) -> int. RED/GREEN DST, early close, holidays, unknown coverage and trading-session staleness.
2. [x] Schema and resolver. Modify models.py, add migration66, create market_data/policy_selection.py; extend market_data_resolver.py. Produce pricing_evidence on ResolvedMarketData and frozen items; add venue/convention/fixing/basis filters, calendar-aware resolution for non-LEGACY only, optional strategy context. Tests: tests/test_composite_policy_resolution.py and legacy resolver/schema tests, all isolated.
3. [x] Configuration and preview API. Create apps/reference_api/valuation_policy_contracts.py, valuation_policies.py, valuation_policy_routes.py; wire router in main.py. Consume existing ResolutionRequest/batch resolver. Produce GET options/detail, idempotent POST immutable policy version and POST read-only preview. Extend snapshot contracts/repository evidence and preserve old fingerprint serialization. Tests: tests/test_composite_policy_api.py plus snapshot API/replay tests.
4. [x] Ops-console configuration/preview. Add /market-data/policies page, client policy console, BFF routes and typed payload helpers/tests; link Market data; display frozen pricing evidence. Generate OpenAPI/TS contracts. RED/GREEN frontend payload/interaction tests and permissions/errors, typecheck.
5. [x] Acceptance and review. Broaden mixed-market fixtures and denial/revision tests; full disposable Python suite, frontend suite/typecheck, contract/whitespace checks. Apply additive local migration after focused checks; verify unchanged financial/price counts. Document delivered scope and remaining external data/rights prerequisites. Separate author review, not independent signoff.

## Ledger

Tasks 1–4 implemented and verified. Temporal helpers: 5 tests RED missing helper / GREEN. Initial resolver/schema regression: 45 passed, broadened focused run: 53 passed. Final composite resolver/API and existing rights checks: 26 passed in 64.55s (`logs/composite-policy-rights-and-review-green.log`). Configuration tests first failed for missing endpoints, then passed after implementation. Managed-version audit fields are a separate additive migration67 after verified migration66, retaining immutable migration history.

Frontend: 124 files / 593 tests passed in 28.74s (`logs/composite-policy-frontend-final-2.log`); ops-console and API-contract typechecks passed. OpenAPI export check and whitespace check passed. Task 5 complete: browser read-only acceptance and separate author review completed; final full isolated Python regression passed 1,096 tests with 488 warnings in 827.04s, exit 0 (`logs/composite-policy-full-python-final.log`). The first full run exposed a legacy partial-rule dictionary compatibility failure; corrected with a default LEGACY convention, then verified against all eight existing rights tests before restarting the full suite. No automatic commit/push or operating-data configuration writes.

Pre-flight: temporal helpers feed new-rule resolver; snapshot evidence feeds API and UI. Existing legacy rule fields remain defaults; policy requests add optional strategy context only when supplied. Current snapshot fingerprint serializes all fields, so absent strategy must be removed to preserve historical hashes. Existing pure date resolver counts weekdays; new conventions require independent calendar logic without altering legacy behavior.

Ruling: reuse valuation_cut for fixed-time conventions, while session closes use listing calendars — avoids a second fixing/time-definition catalogue; cost is explicit fixing-code and cut matching in adapters and rules.

Ruling: source calendar package is labelled versioned comparison evidence, not authoritative — existing governed sessions take precedence; cost is explicit NOT_ASSESSED for unsupported calendars rather than automatic approximation.
