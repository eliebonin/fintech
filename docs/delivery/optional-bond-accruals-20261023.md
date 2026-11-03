# Optional assessed daily bond accruals

**Status:** Implemented; focused verification recorded below.
**Date:** 23 October 2026

**Current-status follow-up (26 October):** [Confirmed zero-coupon applicability](zero-coupon-accrual-applicability-20261026.md)
now distinguishes absent coupon inputs from missing applicable interest, using
original frozen booked terms. Supplied inputs and publication safeguards remain.
The verification below records the original 23 October delivery, not that follow-up.

## Agreed behaviour

Daily interest is optional by default in economic position P&L. Every supplied
eligible input is validated and included, even when another bond/date is missing.
Missing coverage is not an input with amount zero: price/FX P&L proceeds and
explicitly excludes unprovided interest. Supplied assessed zero remains sourced zero.

`requireCompleteAccruals: true` opts into complete canonical-bond/date coverage,
including eligible weekends and disposal days. The input-form checkbox is unchecked
for new requests. Strict mode never fabricates assessment, derives coupon interest
or discount accretion, or substitutes schedules for assessed facts. Zero-coupon
instruments are not assigned invented zero accruals.

Supplied invalid evidence, failed required currency conversion, missing prices,
and unsupported maturity remain blockers. Missing accumulated balance/receivable
FX remains unassessed, not zero. Clean/dirty trade normalization, coupon/payment
separation, booking, cash snapshots and source access are unchanged.

## Evidence and review

- `accrualCoverage` freezes OPTIONAL/REQUIRED mode, supplied/missing counts and
  missing canonical instrument/date pairs in calculation and batch evidence.
- `MISSING_DAILY_ACCRUAL` line evidence and `DAILY_ACCRUAL_NOT_SUPPLIED` applied
  rules explain omissions without adding an ACCRUAL amount. Multiple listings
  retain warnings, but batch counts and supplied earnings are not multiplied.
- Results prominently show **Accrual not supplied—not included**, with missing
  dates. Current DISPLAY restrictions still suppress financial evidence.
- Publication can proceed with disclosed optional omissions and existing review
  controls. If omitted interest is supplied after staging, publication requires
  recalculation. Existing supplied-input revision protection remains.
- Published results remain immutable. Default retry identities remain compatible;
  strict identities are distinct. Reassessment preserves the recorded mode;
  legacy results without this field retain their former strict behaviour.

This is core platform functionality. Source-specific CSV reconciliation scripts
remain convenience tooling, not a supported upload contract.

## Verification and limits

- 48 focused disposable-database/API tests passed (economic acceptance, typed
  interest, current-source publication, request/retry identity and reassessment).
- 23 focused frontend request/rendering/workspace tests passed; typecheck passed.
- Two isolated Edge browser journeys passed: optional warning/strict request and
  the existing explicit review/publication interaction. Initial bundled Chromium
  launch failed because its executable was absent; installed Edge was used.
- API contract export check passed; regeneration produced identical SHA-256.
  `contract:generate:check` reports differences against Git HEAD because the
  current contracts include this and pre-existing uncommitted work; it is not a
  clean-HEAD pass. No generated content was discarded to silence the check.
- 15 offline contract/boundary/neutrality checks passed; scoped diff check passed.
- No full suite, full NAV sign-off or independent reconciliation implied.
- No migration, operating interest entries, trade changes or valuation publication.

Implementation: [accrual consumer](../../valuation/accruals.py),
[calculation](../../valuation/service.py), [request](../../apps/reference_api/valuation_contracts.py),
[results](../../apps/ops-console/src/features/valuation/result-workspace.tsx).
Tests: [economic acceptance](../../tests/test_economic_pnl_acceptance.py),
[request/retry](../../tests/test_optional_accrual_contract.py).
Plan: [bounded sequential change](implementation-plans/optional-bond-accruals-20261023.md).
