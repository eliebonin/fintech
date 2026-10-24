# Lightweight AMC implementation plan

> Execute sequentially using executing-plans and focused test-driven development.

**Goal:** Create and book an AMC as `ACTIVELY_MANAGED_CERTIFICATE`, sharing
funded-security mechanics without pretending it is a fund or ETI.

**Architecture:** A dedicated typed proposal and effective-dated AMC terms record
use the existing reference approval queue, private visibility and audit router.
AMC booking uses the existing funded-product ticket and frozen conventions.
Unit-price daily valuation reuses the price/FX arithmetic, retaining AMC identity.

**Spec:** The owner-approved recommendation immediately preceding implementation:
shared identity/currency/units/dated prices, explicit issuer/adviser/reference,
optional listings, explicit quote/redemption terms, no fund hierarchy or assumed
NAV lag. This plan also acts as the execution ledger; no separate approval loop
or subagents, following the owner's standing instructions.

**Constraints:** Preserve unrelated dirty changes and original import evidence.
No permissions, provider rights, operating trades or valuations are created.
No automatic cash legs, fee accruals or invented contractual economics.
Focused tests in owned disposable databases only. No full regression or push.

## Tasks

- [x] 1. Add `amc_terms`, additive migration 97, strict AMC proposal and booking
  convention contracts. Test explicit quotation/redemption and optional metadata.
- [x] 2. Add creation, current-access approval revalidation, identifier uniqueness,
  native AMC materialization and review-queue dispatch. Test private scope,
  stale issuer/reference refusal, unchanged-source replay and rejection.
- [x] 3. Extend existing product booking, readiness and frozen valuation adapter
  for AMC. Test signed units, consideration, sale/partial position, explicit
  factors and no fund/NAV coercion. Percentage quotes remain creation/booking
  supported; daily valuation initially requires native unit-price conventions.
- [x] 4. Add creation UI/BFF and AMC option in the existing booking ticket, keeping
  context transport, pending-request recovery and permission checks. Verify
  focused UI tests, typecheck and generated contracts.
- [x] 5. Update the reconciliation adapter to create FCGMS through the new normal
  workflow, with source vs mockup terms explicit. Document activation separately
  from code/tests; apply migration/restart only with required authority.

## Review focus

Cross-tenant issuer/reference IDs; source replay after revoked authority;
unknown maturity versus open-ended terms; percentage versus unit quotation;
booked factors versus listing multiplier; missing publication time/price inputs;
unrelated existing work and no silent relabelling of historical evidence.

## Research (checked 23 October 2026)

- [SSPA AMC recommendations, amended 1 April 2025](https://sspa.ch/wp-content/uploads/2025/03/sspa-amc-recommendations_effective-per-april-1_-2025.pdf):
  issuer risk, adviser/strategy roles, fees and pricing. Swiss-market guidance,
  not universal legal requirements.
- [BNP certificate prospectus, 21 May 2026](https://www.bnpparibas.pl/_fileserver/item/1551538):
  issuer/guarantor obligations and certificate-specific final terms.
- [SEC fund NAV explanation](https://www.investor.gov/introduction-investing/investing-basics/glossary/net-asset-value):
  NAV per share differs from a certificate's quoted price.

## Progress / rulings

- Planned. Existing feature branch and current dirty checkout retained because
  the reconciliation work depends on uncommitted source/import foundations.
- No commits or subagents: user requested sequential implementation and has not
  requested Git publication for this task. Final review will be a separate
  self-review, not independent sign-off.
- Complete: migration 97 locally active; FCGMS created through normal approval;
  existing app API 8001 restarted, frontend 3001 HTTP 200, booking READY.
- Final evidence: 48 focused backend and 32 frontend tests passed, typecheck
  clean. No full suite or financial posting. See the delivery for exact limits.
- Self-review: no additional blocking findings. Dedicated AMC amendment UI,
  monetary-preview support, percentage-quoted daily valuation and browser/manual
  contractual acceptance remain explicit follow-up scope, not silently enabled.
