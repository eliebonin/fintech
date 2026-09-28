# Project state and quality review

**Review date:** 7 September 2026  
**Scope:** Markdown architecture/specification files, Python schema and services,
Alembic migrations, mock-data loaders, and Python tests.

## Executive conclusion

The project is a strong architectural prototype, but it is not yet a
production-ready financial platform.

Its conceptual foundation is better than that of many early security-master
projects. The economic-instrument/listing distinction, canonical UUID identity,
external mappings, market-data provenance, trade grain, and frozen valuation
evidence are broadly sound. The main risk is no longer missing product tables.
It is the difference between concepts represented in the schema and behaviour
that is enforced end to end.

| Area | Assessment |
|---|---|
| Architecture and domain analysis | Strong |
| PostgreSQL schema coverage | Strong but broad |
| Documentation | Rich, but fragmented and partly stale |
| Python implementation | Functional prototype |
| Test coverage | Reasonable breadth, limited behavioural depth |
| Production controls | Incomplete |
| Suitable for internal demonstrations | Yes |
| Suitable for live client data or NAV reliance | No |

The repository contains approximately 73 Markdown files, 93 Python files and
159 Python test functions. These figures demonstrate breadth, not production
readiness.

## Strong foundations

### Reference identity

The central reference model is coherent:

```text
financial_reference_node
    |-- economic instrument
    |-- venue listing
    |-- index, family and other reference objects
    `-- currency, commodity and crypto roles
```

The following decisions should be retained:

- Economic instruments and venue listings are distinct.
- Structural node type, economic instrument type and optional business taxonomy
  are governed separately.
- The immutable internal UUID is distinct from ISIN, FIGI, Bloomberg, RIC,
  custodian, bank and client identifiers.
- Provider and client identifiers are effective-dated mappings, not alternate
  primary keys.
- Futures families, index families and concrete contracts or variants have
  sensible identities.
- Contractual economics live in terms, legs, barriers, schedules and
  compositions rather than classification labels.

### Trading and valuation boundaries

The model also correctly establishes that:

- A trade is a booked economic event, not an order or universal multi-leg
  container.
- Cash balances and position snapshots are not trades.
- A raw market-data observation and a tenant valuation mark are different
  domains.
- Market-data series describe a precise observable stream before observations
  are stored.
- Dataset, provider, licence, entitlement, source payload and vintage concepts
  are represented.
- NAV runs and resolution snapshots retain evidence needed for reproducibility.
- Calendars belong in a shared `cal` domain rather than the security master.

### Implementation discipline already present

Positive implementation details include:

- Alembic migrations rather than metadata-only database creation.
- Consistent comments on SQLAlchemy columns.
- Deterministic and largely idempotent mock-data loaders.
- Multi-asset mock data, UK and US valuation cuts, portfolios, trades and
  multi-year observations.
- Targeted tests for catalogues, onboarding, entitlements, migrations,
  immutability controls and resolution evidence.

## Critical findings

### P0. Market-data resolution is not yet point-in-time reliable

The resolver accepts `valuation_cut_id`, but candidate selection does not use it
to restrict the selected series or observation. The cut is persisted in the
snapshot without proving that the chosen value represents that cut.

The resolver also currently:

- stores but does not execute the policy `selection_method`;
- uses weekdays instead of the configured holiday and session calendar;
- checks platform receipt time without fully applying source publication and
  vintage eligibility;
- removes an original observation whenever an accepted correction exists, even
  when that correction arrived after the historical information cut; and
- does not explicitly enforce all timestamp and cut relationships involved in
  historical replay.

Consequently, a historic NAV replay can potentially use the wrong valuation cut
or a correction that was not knowable at the time.

Primary implementation locations:

- `security_master_schema/market_data_resolver.py`
- `security_master_schema/valuation_resolver.py`
- `security_master_schema/market_data_vintages.py`

This is the highest-priority functional correction.

### P0. Immutable facts and mutable lifecycle state conflict

Several mutation-blocked tables carry fields that imply state transitions:

- Definition versions contain `DRAFT`, `APPROVED`, `SUPERSEDED`, `RETIRED` and
  `is_current`.
- Valuation marks contain `DRAFT`, `REVIEWED`, `APPROVED`, `REJECTED` and
  `SUPERSEDED`.
- Market-data vintages contain `CURRENT`, `CORRECTED`, `RESTATED`, `SUPERSEDED`
  and `REJECTED`.

Their PostgreSQL triggers prohibit every update and delete. For example, an
approved current definition cannot be changed to non-current, while the unique
current-version index prevents insertion of another approved current version.
The intended supersession lifecycle is therefore not operational.

The preferred model is:

1. Keep the substantive fact/version immutable.
2. Append separate approval and lifecycle events.
3. Derive effective/current state through a deterministic projection or view.

A more limited alternative is a controlled database procedure allowed to retire
the old version atomically, but this is less purely append-only.

Relevant migrations:

- `20260901_07_reference_definition_versions.py`
- `20260901_10_valuation_marks.py`
- `20260901_11_market_data_vintages.py`

### P0. Tenant database topology is documented but not implemented

The adopted topology is:

```text
central canonical and market-data database
              +
one operational overlay database per tenant
```

The current API nevertheless opens one configured `DATABASE_URL`, and the
shared SQLAlchemy metadata contains ordinary foreign keys between canonical,
tenant, trade and NAV schemas.

A physical split requires:

- separate core and tenant metadata/migration tracks;
- registry-controlled runtime connection routing;
- per-tenant credentials and connection pools;
- central UUID validation through the canonical API rather than cross-database
  foreign keys;
- local validation/link evidence in the tenant database; and
- durable pending or exception handling when the core service is unavailable.

Until these exist, the platform has logical tenant concepts but cannot claim
the documented physical tenant isolation.

### P1. Soft NAV remains a constrained proof of concept

The present service intentionally supports only same-currency positions. It does
not yet calculate or freeze:

- FX conversions;
- cash balances;
- bond accrued interest;
- fees and other liabilities;
- approved valuation overrides; or
- administrator-NAV reconciliation.

Two further implementation gaps should be corrected:

1. Quote factor and unit multiplier are read from mutable listing columns rather
   than the effective-dated quotation and contract-unit terms.
2. `nav_valuation_line` has fields for the precise price and FX input snapshot
   items, but the calculation service does not populate them.

The existing Soft-NAV test proves one same-currency listing calculation and
input record. It does not yet prove the documented fund valuation gate.

### P1. Raw observation immutability is documented but not enforced

The architecture consistently describes raw market-data observations as
immutable. Market-data vintages and resolution snapshots have mutation-blocking
triggers, but an equivalent PostgreSQL trigger was not found for
`md.market_data_observation`.

Application convention is not sufficient for this invariant. An accidental SQL
update must not be able to rewrite historical valuation evidence.

### P1. Trade correction behaviour is incomplete

The trade model has an appropriate append-only lifecycle envelope. The Python
derivation currently identifies the latest effective event, but does not yet
govern:

- permitted transition sequences;
- the economic payload of amendments;
- effective date versus recording and booking dates;
- cancellation and rebooking;
- novation;
- source idempotency across complete booking workflows;
- affected position/NAV periods; or
- recalculation and supersession evidence.

This is sufficient to retain lifecycle evidence, but not to operate a complete
corrected-trade process.

## Documentation assessment

The detailed notes are thoughtful and frequently distinguish adopted decisions
from deferred scope. In particular:

- `security-master-notes/18-critical-review-and-delivery-choices.md`
- `security-master-notes/19-tenant-database-topology-and-priorities.md`
- `docs/architecture/schema-hardening.md`
- `security-master-notes/24-external-evidence-and-research.md`

are valuable architectural records.

The documentation nevertheless contains multiple generations of truth:

- The root architecture note and decision log still describe a
  `security_price` table, while the implementation uses
  `market_data_series` and `market_data_observation`.
- ABC/XYZ/FOO examples remain after their defaults were deliberately removed.
- Some API documentation omits implemented endpoints.
- Real-company mock names remain despite an adopted decision to fictionalise
  demonstration data.
- Product-specific design notes sometimes describe planned tables as if they
  were already operational.
- Brand-specific names remain in database, container, fixture and comment names
  despite the later neutral-naming direction.

The project needs one current architecture index that classifies each document
or decision as:

- adopted and implemented;
- adopted but incomplete;
- deferred;
- superseded; or
- research/background only.

The older documents can remain as design history, but should not silently
compete with the current architecture.

## Python and delivery quality

The Python is generally readable and explicit. Domain helpers are small and
testable, but application structure is becoming concentrated:

- `apps/reference_api/repository.py` is more than 3,000 lines and combines
  catalogues, search, onboarding, work queue, mappings, market data, trades and
  demonstration P&L.
- `apps/reference_api/main.py` also carries a growing route surface.
- Some database identities are created with UUIDv4 in the API despite the
  UUIDv7 database-identity decision.
- Python dependencies use broad ranges without a lockfile or `pyproject.toml`.
- No Python linting, static type-checking or CI configuration was found.
- Tests commonly use fixed local credentials and shared mutable mock data,
  limiting isolation and safe parallel execution.
- A substantial part of the suite verifies table shape rather than complete
  behavioural invariants.

The Git repository has no commits and all project files are currently untracked.
Runtime log files are also present in the project root. Establishing a clean
baseline commit, ignore policy and automated checks is now foundational rather
than administrative polish.

The API currently trusts tenant and account headers supplied by the BFF. The
documentation correctly states that production Auth0 claim validation and
server-derived tenant context remain outstanding.

## Assessment of deferred work

### Deferrals that have become foundation blockers

These items should be promoted into the immediate implementation plan:

1. Correct point-in-time market-data and correction resolution.
2. Repair version, approval and supersession state modelling.
3. Implement actual core/tenant database routing and deployment boundaries.
4. Complete frozen price and FX input linkage.
5. Enforce raw observation immutability.
6. Authenticate and derive tenant context rather than trusting raw headers.
7. Define trade-correction impact and recalculation behaviour.
8. Establish source contracts, idempotency and durable ingestion exceptions.
9. Establish Git history and continuous verification.

### Deferrals that can safely remain later scope

The following should not delay foundation hardening:

- complete volatility cubes and high-frequency storage;
- custody-grade corporate-action elections, claims and tax processing;
- settlement instructions and fails processing;
- full repo, securities-lending, credit and rate-exotic coverage;
- daily index constituent ingestion and calculation;
- advanced performance-fee equalisation and tier methods;
- automatic private-instrument promotion;
- broad generic rules or formula engines; and
- additional UI workflows for every modelled instrument type.

## Recommended next milestone

Do not prioritise more instrument tables or forms yet. Complete one dependable
vertical slice:

```text
authenticated tenant
    -> registry-routed tenant database
    -> frozen positions and cash
    -> calendar-resolved valuation cut
    -> entitled point-in-time price and FX resolution
    -> reproducible Soft NAV
    -> immutable review and approval events
    -> corrected-trade recalculation evidence
```

Required acceptance scenarios should include:

1. UK and US portfolios selecting different named cuts.
2. A T-1 fund price using the relevant market calendar.
3. A holiday and a daylight-saving transition.
4. A correction received after the historic cut that remains ineligible.
5. A correction received before the cut that supersedes the earlier value.
6. A cross-currency position with independently frozen price and FX inputs.
7. Cash, bond accrued interest, fees and liabilities.
8. An amended trade causing a new affected-period run without rewriting the old
   run.
9. Cross-tenant access attempts rejected at routing, application and database
   boundaries.
10. A complete replay producing the same result and evidence identifiers.

## Final verdict

The foundation is sound in concept and worth preserving. The
`node -> instrument -> listing` architecture and most of the schema should not
be redesigned.

The project should presently be described as a **well-designed prototype with
substantial implementation**, not as a completed production foundation. Its
main risk is continuing to expand product and UI breadth while the resolver,
lifecycle, versioning and tenant boundaries remain only partially enforceable.

Once the proposed vertical slice works under historic corrections, calendar
cuts, cross-currency valuation, trade amendments and cross-tenant tests, the
platform will have crossed the important boundary from broad prototype to a
dependable financial-data foundation.

## Verification note

This review was based on static inspection of the Markdown documents, Python
implementation, SQLAlchemy metadata, Alembic migrations, mock-data loaders and
existing tests. The complete test suite was not rerun, in accordance with the
instruction not to run it unless explicitly requested. No implementation files
were changed as part of the review other than adding this document.
