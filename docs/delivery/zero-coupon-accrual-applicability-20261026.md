# Zero-coupon accrual applicability

**Status:** Implemented; focused verification passed; API 8001 activated.  
**Content type:** Delivery record  
**Owner:** Valuation engineering  
**Last reviewed:** 2026-10-26

## Correction and boundaries

Zero-coupon bonds incorrectly received missing-interest warnings because the
accrual loader treated every active bond as requiring a coupon input. The ledger
reader retained valuation conventions but omitted coupon type from the original
booked terms before the applicability check.

The reader now carries that frozen coupon fact into the existing projection,
without changing stored events or consulting today's security-master terms.
An absent daily input is **not applicable** only when every contributing booking
confirms `couponType: ZERO`. A zero rate, instrument name, absent schedule or
current-master change is not proof. Unknown, conflicting or mixed terms are not
silently waived; conflicting explicit frozen facts block reconstruction.

- Price/FX P&L and clean/dirty execution normalization are unchanged. No zero
  interest input or separate discount-accretion accounting entry is invented.
- Valid supplied interest is still validated and included, even for zero-coupon
  bonds. Invalid supplied amounts/evidence still block.
- Optional and strict coverage both exclude confirmed not-applicable dates from
  missing requirements. Coverage counts each canonical bond/day once, including
  multiple listings, and retains `notApplicableCount`/`notApplicable` evidence.
- Position evidence and applied rules record `DAILY_ACCRUAL_NOT_APPLICABLE`,
  `ZERO_COUPON` and `FROZEN_BOOKING_TERMS`. No missing-interest warning is created
  for those absent inputs. Supplied zero remains a sourced amount, not this state.
- Maturity/exposure checks remain. Earlier flat episodes do not create continuing
  coverage obligations. This is not an automatic accrual or coupon engine.
- Interest supplied after staging invalidates the prior absence assessment and
  requires recalculation before publication. Existing revision guards remain.
- Historical frozen results are not rewritten. Start a new valuation to use the
  correction; no operating calculation or publication was performed for testing.

Investor.gov's [zero-coupon definition](https://www.investor.gov/introduction-investing/investing-basics/glossary/zero-coupon-bond)
(reviewed 26 October 2026) establishes the absence of periodic interest payments.
Keeping price/FX movement while not generating separate accretion accounting is
the bounded project convention here, not a claim about all accounting regimes.

## Implementation and verification

- [Ledger adapter](../../positions/repository.py), [coverage/attachment/publication](../../valuation/accruals.py),
  [service](../../valuation/service.py) and [applied decisions](../../valuation/decisions.py).
- [Focused offline cases](../../tests/test_zero_coupon_accruals.py): optional/strict,
  unknown/mixed terms, supplied zero/nonzero and invalid evidence, multiple
  listings, maturity and flat-history handling. Initial tests reproduced the defect.
- [Economic acceptance](../../tests/test_economic_pnl_acceptance.py): real
  calculation, stage and publish from frozen ZERO terms, unchanged price/FX P&L,
  later-input stale publication, current-master non-authority and conflicting proof.
- 44 lightweight offline tests passed (applicability, decisions, methodology,
  product inputs). 72 focused tests passed in the owned disposable PostgreSQL
  runner (including service, economic acceptance, accruals, typed interest,
  bond redemption and request identity). These are overlapping, not additive counts.
- The first database run also exposed an outdated request-identity test; its
  assertion now includes the calculation-contract field already in the backend.
  No retry-identity implementation changed in this correction.
- No full Python suite, frontend change/browser acceptance, independent financial
  reconciliation or full NAV/production sign-off is implied.

No schema migration, operating data changes, permission grants or evidence
backfill were needed. API 8001 was restarted on 26 October with the existing
local Docker database configuration; `/health` returned `status: ok` and startup
completed. Frontend 3001 and the database container were not restarted. No
operating calculation or publication was performed during activation.
