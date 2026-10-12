# Valuation Price Basis Implementation Plan

> For agentic workers: use superpowers:executing-plans, sequentially. No subagents.
> Status: proposed plan only; no implementation or migration applied.

**Goal:** Let valuation policies request as-traded prices while safely admitting
evidenced split-adjusted inputs, without asking tenants to manage adjustment mathematics.

**Architecture:** Separate the rule's economic output requirement from source
metadata. A provider-neutral normalization boundary produces an observation-linked
proof and valuation value; resolver arbitration considers only usable inputs.
The valuation engine verifies and consumes that result without altering trades.

**Tech stack:** Existing PostgreSQL/Alembic, SQLAlchemy, Python Decimal/Pydantic,
Next.js/TypeScript and generated OpenAPI contracts. No new third-party dependency.

**Spec:** ../specs/2026-10-09-valuation-price-basis.md

## Global constraints

- Preserve original observations, booked trades and immutable policy/result evidence.
- Unknown adjustment evidence fails closed; never infer factor 1 from absence.
- Keep current corporate-action safety, permissions, calendars and FX boundaries.
- Sequential implementation; focused tests against disposable databases, no full suite.
- Reuse current feature checkout; preserve unrelated dirty changes. No commit/push
  or operating-data mutation beyond authorized activation during implementation.
- Allocate the next unused migration revision at implementation, not at planning.

## Review focus

1. Future splits outside the requested history window still affect the provider's
   historical adjustment anchor: Task 2 tests complete anchor coverage.
2. A higher-priority unusable provider must not win or fabricate a converted price:
   Task 3 tests eligibility before arbitration, including a lower-priority usable source.
3. Split events during a held position require position replay, not just price
   conversion: Task 4 tests that the existing guard continues to block.
4. Revisions known after an old information cutoff must not leak into replay:
   Tasks 2/4 test revision exclusion and immutable frozen evidence.
5. Mixed-price T/T-1 selections must use the same economic output units even if
   their providers/source bases differ: Task 4 tests the P&L bridge.

## Task 1: Policy economic requirements and compatibility

Files: `security_master_schema/models.py`, next additive Alembic revision,
`apps/reference_api/valuation_policy_contracts.py`, `valuation_policies.py`,
`market_data/policy_compatibility.py`; new `tests/test_valuation_price_requirements.py`.

Interfaces: produce nullable legacy-compatible `price_requirement` and
`allow_split_conversion` fields (API `priceRequirement`, `allowSplitConversion`).
`effective_price_requirement(rule) -> tuple[str | None, bool]` lives in new
`market_data/price_basis.py`. Null preserves legacy behavior; new output AS_TRADED
is explicit. Legacy RAW rules resolve native-only. Other old source filters stay
selection-only and do not automatically gain new valuation capability.

- [ ] Write tests: old RAW policy remains native-only; old fingerprints replay;
  new AS_TRADED rule rounds trips; unsupported requirements and dividend-adjusted
  exact filters with AS_TRADED are rejected; immutable rows are untouched.
- [ ] Run RED using the isolated runner and the new test module.
- [ ] Add the contracts/schema/adapter and compatibility checks; preserve
  immutable versions and idempotency as in the CLOSE consolidation.
- [ ] Run GREEN for that module plus `test_composite_policy_api.py` and
  `test_pricing_policy_compatibility.py`.

## Task 2: Adjustment proof and Yahoo evidence acquisition

Files: new `market_data/price_basis.py`, `price_basis_store.py`, additive evidence
schema/migration; `market_data/providers/yahoo/adapter.py`, `market_data/contracts.py`,
`ingestion.py`, `storage.py`; new `tests/test_price_basis.py`,
`test_yahoo_adjustment_evidence.py`.

Interfaces: `normalise_as_traded(source_value: Decimal, source_basis: str,
proof: dict | None, *, allow_split_conversion: bool) -> NormalisedPrice` with
`source_value`, `valuation_value`, `valuation_basis`, `evidence`.
`load_price_basis_proof(c, observation_id, information_cutoff) -> dict | None`.
Persist immutable evidence tied to observation/vintage/payload, methodology,
anchor, coverage, split ratios and recorded time; corrections supersede rather
than overwrite. No fictitious RAW observation or source permission grant.

- [ ] Write unit tests: RAW 80 -> 80; adjusted 40 / 0.5 -> 80; multiple/reverse
  splits; proven factor 1; incomplete timeline; anchor missing; zero/negative
  factors; dividend-adjusted rejection; Decimal precision and overflow.
- [ ] Watch those tests fail, then implement the pure normalization boundary.
- [ ] Test and implement retained Yahoo split-event parsing, effective dates,
  correction lineage, coverage across market date through anchor, and historical
  information cutoffs. Only build a usable proof where provider semantics and
  completeness are established; otherwise record a specific blocking reason.
- [ ] Run unit GREEN, then isolated ingestion/proof tests. Existing stored prices
  remain unchanged; plan a targeted evidenced re-ingestion for TTE, not a broad
  S&P/CAC refetch. First check retained payloads for sufficient information.

## Task 3: Usability before provider selection

Files: `security_master_schema/market_data_resolver.py`,
`market_data/policy_selection.py`, `source_priority.py`, `policy_compatibility.py`;
`apps/reference_api/contracts.py`, `repository.py` for frozen snapshot views;
new `tests/test_price_basis_resolution.py`.

Interfaces: consume Task 1 requirements and Task 2 proof/value. Extend
`ResolvedMarketData` with optional `valuation_value`, `valuation_basis`,
`price_basis_evidence`; persist them in resolution evidence, retaining original
`selected_value`. Existing callers and old frozen JSON remain readable.
Use the existing `pricing_evidence.priceBasis` JSON envelope for normalization
evidence and the valuation value/basis; expose optional view fields from that
envelope. Do not rewrite or derive missing normalization evidence for old snapshots.

- [ ] Write RED tests: valid higher-priority converted source wins over lower
  native source; unproven higher source is excluded; native wins within same
  provider/date/rank; forbidden purpose/package remains denied; no eligible input
  returns a clear adjustment-proof diagnostic, not a generic field error.
- [ ] Implement normalization eligibility before existing source arbitration;
  preserve explicit-rule precedence and freshness constraints.
- [ ] Run isolated GREEN with source-priority, closing-method and composite-rule
  regressions. Distinguish configuration compatibility from actual dated proof.

## Task 4: Valuation integration and auditable P&L

Files: `valuation/service.py`, `position_calculation.py`, `storage.py`,
`evidence_access.py`; new `tests/test_valuation_price_basis.py`.

Interfaces: consume `valuation_value` as the market mark, not the original source
value, for AS_TRADED rules. Freeze source/value/basis, conversion version, anchor,
factors, proof IDs and source dates alongside existing T/T-1 input evidence.

- [ ] Write RED tests: 100 shares at native 80 and converted 80 both value at
  8,000; a 75 execution retains its original units/price; mixed provider bases on
  T/T-1 yield the hand-calculated same-basis P&L; corrections do not mutate old runs.
- [ ] Add tests that a split during the holding interval still blocks, that
  dividend-adjusted values do not double-count income, and that unsupported GBP
  conversion still blocks rather than silently changing reporting currency.
- [ ] Implement price-proof verification and frozen attribution evidence.
- [ ] Run GREEN with existing valuation, corporate-action safety and evidence
  permission tests. Do not remove the RAW guard until the proof-based replacement
  covers both old and new request paths.

## Task 5: Policy editor, input evidence and TTE acceptance

Files: `apps/ops-console/src/components/pricing-policy-console.tsx`,
`pricing-policy-help.tsx`, `pricing-policy-compatibility.tsx`,
`valuation-price-evidence.tsx`, `src/lib/pricing-policy.ts`, generated contracts;
focused corresponding UI tests and delivery notes.

- [ ] Write RED UI tests for the economic requirement/conversion toggle,
  read-only authority, original/used price distinction and missing-proof messages.
- [ ] Implement normal economic controls; retain exact source basis as advanced
  and clearly labelled. Show both T and T-1 provenance and conversion evidence.
- [ ] Regenerate OpenAPI/TypeScript and run focused UI tests and typechecks.
- [ ] On the authorized personal dataset, establish TTE's October 6/7 adjustment
  proof using retained payloads first. If factor 1 is evidenced, demonstrate it;
  otherwise demonstrate supported conversion or a precise remaining block.
- [ ] Verify without altering the existing TTE trade or silently revising its
  policy/permissions. EUR price-basis acceptance is separate from successful GBP
  valuation, which still needs FX support, rights and governed calendars.
- [ ] Document commands/results, any provider evidence limitation and activation
  status. Final self-review and focused verification only; no automatic push.

## Proposed delivery order

Policy semantics -> provider proof -> eligible-input selection -> valuation
integration -> frontend and TTE acceptance. Keep the new conversion capability
disabled until the proof and engine gates are complete. If Yahoo cannot establish
anchor/coverage, ship the policy/UI simplification with conversion explicitly
unavailable; report that dependency instead of weakening the economic requirement.
