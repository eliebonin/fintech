# Accrued-balance FX implementation plan

> **For agentic workers:** Use superpowers:executing-plans sequentially, respecting the user's native execution preference.

**Goal:** Add evidenced accrued-stock FX P&L without aborting valid components for missing optional inputs.

**Architecture:** Pure replay plus scoped readers; immutable typed derived daily
balances are frozen with each calculation attempt. Use existing canonical-bond
component ownership, with explicit standalone receivable ownership after sale.

**Tech stack:** Decimal/dataclasses, SQLAlchemy/Alembic, FastAPI, React, pytest/Vitest/Playwright.

**Spec:** [Agreed design](../specs/2026-10-27-accrued-balance-fx-design.md).

## Tasks and review focus

- [x] Pure replay RED→GREEN: verified anchors, signed trade-accrual movements,
  partial/late coupon receipts, missing history, recovery and zero-coupon scope.
- [x] Source adapter: batch original ledger/daily/payment/schedule evidence as of
  information cutoff; resolve policy FX with missing-only warnings; retain
  detached receivables and deterministic per-canonical allocation.
- [x] Storage/integration: migration 101 immutable typed derived balance facts;
  stage financial components and proofs once, preserve partial totals and
  source-health/publication serialization when accrual/payment revisions change.
- [x] UI: dedicated balance bridge in position inspection, readable missing-data
  coverage and partial-total status; preserve technical evidence and permissions.
- [x] Focused acceptance, documentation/register reconciliation and local
  activation after target/version and migration checks. No operating valuations,
  payments, trades, balance inputs or permissions are created for verification.

Important cases: no verified balance means unknown, not zero; actual receipt does
not imply full settlement; paid coupon must not erase newly earned interest;
cancelled buys and principal-only maturity must not fabricate accrued movements;
foreign receivables after full disposal need FX without requesting security marks;
new/corrected source facts after staging require recalculation, not silent repricing.

Sequential acceptance complete: 74 scoped backend checks, 1,055 frontend
regressions and 2 new browser journeys passed; focused final display/type checks
followed. Migration 101 is active locally; no operating financial command was
performed. See [delivery](../../delivery/accrued-balance-fx-20261027.md).
