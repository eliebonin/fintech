# Incomplete price review implementation plan

> Use superpowers:executing-plans sequentially in the current feature checkout.

**Goal:** Stage usable partial P&L and resolve missing marks through reviewed inputs before publication.

**Architecture:** Domain-owned input-gap and manual-mark services feed the existing
position calculation, immutable staging and guarded publication. HTTP/BFF/UI retain
existing authority, context, audit and review conventions. Original observations
and financial evidence are unchanged.

**Tech stack:** Python/Pydantic/SQLAlchemy/PostgreSQL; FastAPI; Next/React/TypeScript.

**Spec:** [Agreed design](../specs/2026-10-31-incomplete-price-review-design.md).

## Constraints and review focus

- Work sequentially; preserve unrelated changes; no automatic commit/push.
- Unknown is never zero; all unpriced positions remain visible with lineage.
- WARN must not absorb permissions, bad economics, calendar errors or incompatible units.
- Missing opening/closing/multi-day marks affect only their actual position population.
- Normal/self publication and amendments cannot bypass required-mark completeness.
- Reviewed marks require exact scope/Decimal proof, current rights and independent real operators.
- Later observations/review decisions require recalculation; prior evidence remains immutable.

## Tasks

- [x] **1. Partial position calculation and staging.** Add lightweight failing
  input-gap/coverage tests, then bounded typed missing-input handling, complete
  unpriced proof, priced-population attribution and a publication guard. Verify
  mixed/all-missing, FAIL, multi-day, zero boundaries and preserved optional inputs.
- [x] **2. Reviewed manual marks.** Add retained request/decision tables and an
  additive migration, domain commands, missing-only input resolution, current
  approval checks, audited scoped routes and request/review/withdraw tests. Use
  existing quotation dimensions and native pricing guards, not provider impersonation.
- [x] **3. Operations UI.** Add compact gap/subtotal disclosures, unpriced position
  rows, manual-mark request/review controls, inspection evidence and publication
  blockers. Keep context-safe requests and existing tab/navigation behavior. Test
  accessible labels, unavailable amounts, independent review and uncertain retry.
- [x] **4. Verification and activation.** Run focused Python/frontend regressions,
  generated contract/type checks and browser smoke acceptance. Apply the tested
  additive schema locally, restart services, create a new WARN policy version and
  rerun FCPGF to stage its real partial report without inventing marks/publishing.
  Update capability/methodology/delivery documentation and local links.

## Execution ledger

2026-10-31: Existing FAIL/WARN/MANUAL_OVERRIDE fields do not provide end-to-end
partial financial staging or reviewed mark requests. The dedicated mark evidence
primitive is insufficient without approval provenance. The user approved partial
staging, missing/reviewed marks followed by recalculation and ordinary publication
only after completeness; no publication of an incomplete report is authorized.


31 October completion: additive 107 applied; API 8000/portal 3001 activated.
Focused backend, frontend, schema/type and three isolated Edge checks passed.
Live FCPGF partial run stages 123 priced positions, two unpriced forwards and
one cash scope with two missing FX dates; its four required marks still gate
publication. Live Positions/Review inspection and disabled publication verified.
No operating mark requests, approvals, publications or invented observations.
See [delivery and limits](../../delivery/incomplete-price-review-20261031.md).
