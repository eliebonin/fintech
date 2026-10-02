# Governed Trade Properties Implementation Plan

Date: 2026-09-30. Status: superseded by the user-approved combined configuration
workflow on 2026-10-01. Implementation resumed following explicit approval.

The delivered alpha, revised scope, standard party curation, verification and
remaining boundaries are recorded in
[Governed trade configuration alpha](../../delivery/governed-trade-configuration-alpha.md).
The original proposal below is retained as design history; it is not a claim
that every phase or the illustrative currency adapter has been delivered.

## Objective and scope

Deliver tenant-configurable trade properties whose permitted values come from
either a tenant-owned reference catalogue or an explicitly supported platform
dataset. Separate the dataset, property definition and assigned value. Preserve
existing bookings and scalar fields; do not turn financial relationships or
instrument terms into arbitrary metadata.

The first end-to-end cases are a tenant-owned Investment rationale catalogue and
the platform currency catalogue, consumed by an optional Reporting currency
property. Reporting currency is an annotation only: it must not change execution
currency, strategy base currency, settlement or valuation behaviour. These are
proposed examples, not new required fields to impose on tenants.

Single-select references are the first delivery. Hierarchies, multiple selection,
external ingestion, dependent selectors, formula fields, general reporting and
non-trade assignment are subsequent increments. Design must accommodate them,
but the initial UI must not advertise unimplemented capabilities.

## Current foundations and paused work

`trd.trade_property_definition` and `trd.trade_property_value` already support
tenant-owned scalar definitions and immutable assigned values. Definitions have
versioning and retirement audit; values are JSON scalar strings or booleans.
Embedded CHOICE strings have no separate record identity or dataset lifecycle.

`secm.taxonomy` and `secm.taxonomy_value` model shared classifications and
hierarchy, but lack tenant ownership. `secm.instrument_taxonomy_assignment`
targets instruments, not trades. Do not retrofit tenant catalogues into these
tables without a deliberate ownership/migration decision.

The interrupted simple-editor work includes `trade_configuration.py`,
`trade_configuration_routes.py`, lifecycle tests and possibly router registration
in `main.py`. Its actual state must be inventoried before implementation resumes.
It is partial work, not evidence of a complete configuration module. Reuse useful
authorization/retirement behaviour, replace the embedded-choice assumptions,
and preserve unrelated dirty files. Do not delete or reset the checkout.

## Proposed architecture decisions

1. Keep scalar properties and reference properties distinct. Add a reference
   value kind and an immutable binding to a governed dataset. Initially cardinality
   is one selected record. Retain old scalar/CHOICE definitions for compatibility.
2. Add a small tenant reference-catalogue domain rather than changing the existing
   shared security-master taxonomy in place. Catalogue and record IDs are stable;
   record codes are unique within their dataset and cannot be recycled for a
   different meaning. Record versions carry labels, descriptions and audit.
3. Register supported platform sources in application code. The currency adapter
   selects existing `secm.currency` identities, never duplicated currency records.
   No arbitrary database table, SQL expression, browser-selected tenant or remote
   URL can become a source. Tenant-owned datasets are not automatically shared.
4. Bind selections using relational IDs with foreign keys. Reference assignment
   storage is separate from scalar JSON. For the first two sources, use explicit
   catalogue-record-version and currency references with an exactly-one-target
   constraint, not an unconstrained `(table_name, uuid)` pair. Dataset binding,
   tenant ownership and source-kind checks accompany ordinary referential integrity.
   A future source requires a reviewed adapter and integrity model.
5. Property definitions capture source binding, label, description, requiredness,
   cardinality and definition version. Dataset changes do not silently change the
   field's source. Binding changes require a replacement definition version.
6. Tenant record meaning changes create a replacement identity; label corrections
   create an audited record version. Assigned trades retain the selected record
   version. Platform assignments retain canonical identity plus a server-created
   booking-time code/label snapshot if that source has no version history. Current
   names may be shown separately, never substituted for historical evidence.
7. For the alpha, selection eligibility is checked at booking time: active dataset,
   active binding, active allowed record, authorised tenant/user. Retirement blocks
   new bookings without invalidating historical reads or exact replay. Trade-date
   effective selection is deferred and must not be implied for backdated trades.
8. Tenant administrators with TRADING access manage fields/catalogues. Platform
   sources remain platform-owned. Publish changes explicitly and audit actor,
   timestamp, reason and version. A separate maker-checker approval role is not
   introduced implicitly; this alpha does not claim regulatory approval compliance.

## Delivery sequence

### Phase 1 Inventory and schema design

- Inspect current branch, dirty files, migration head and interrupted editor changes.
- Specify concrete tables, composite keys, source-kind integrity, audit events,
  definition versions, record versions and platform source permissions.
- Keep tenant reference catalogues distinct from canonical master entities and
  existing instrument taxonomies; document any future bridge explicitly.
- Define create, publish, replace and retire semantics, duplicate-command handling,
  concurrent updates, active-record limits and paginated catalogue reads.
- Produce the schema/API decision record before migration work.

Exit condition: one reviewed schema supports both first-slice examples without
unconstrained references, duplicate platform records or tenant leakage.

### Phase 2 Governed dataset storage and lifecycle

- Write lightweight failing schema/lifecycle tests first.
- Add an additive migration for tenant datasets, stable records, record versions
  and append-only audit events, with tenant-aware uniqueness and foreign keys.
- Implement draft creation, explicit publication, label correction, replacement
  and retirement. Never hard-delete referenced records or overwrite their meaning.
- Serialize conflicting publication/retirement operations and reject stale versions.
- Implement the currency source adapter using the existing canonical catalogue.

Exit condition: tenant A cannot manage/read tenant B's catalogue; retired records
remain historically readable; shared currency identity is preserved.

### Phase 3 Property bindings and backward compatibility

- Extend definitions with reference kind, dataset binding and supported cardinality.
- Add immutable reference assignments with explicit FK targets and server snapshots.
- Preserve existing scalar and embedded CHOICE read/write contracts during rollout.
- Do not automatically reinterpret old CHOICE strings as governed record IDs.
  Offer a separately reviewed conversion mapping; preserve old definitions and
  historical values, replacing definitions for future governed selections.
- Publish requiredness with a clear impact acknowledgement. Existing trades are
  not backfilled or made invalid. Retiring a dataset used by active required fields
  must be blocked until affected bindings are replaced or retired atomically.

Exit condition: historical trades and existing retry fingerprints still work;
optional reference properties can coexist with current scalar properties.

### Phase 4 APIs and transactional booking

- Add typed catalogue/record/property lifecycle APIs and bounded source search.
- Every lookup, management command, selection and detail read uses trusted tenant
  context and server authorization. Reject forged, inactive, wrong-source and
  cross-tenant IDs even if the client dropdown previously displayed them.
- Validate and persist selections atomically with the trade. Lock/recheck source
  eligibility against concurrent retirement; use deterministic lock order.
- Capture definition version, selected record identity/version and display evidence.
- Extend replay hashing with stable selected identities; exact replays remain
  valid after retirement, while changed selections using the same key conflict.
- Use safe field-associated errors and command retry protection; distinguish
  known validation rejection from uncertain network/commit outcome.
- Regenerate and check OpenAPI and TypeScript contracts.

Exit condition: real rollback-backed bookings round-trip both source types;
no partial trade is left after an invalid or failed child assignment.

### Phase 5 Configuration pages

- Under Tenant profile, link to Trade configuration for field bindings, requiredness,
  active/retired versions and usage/impact. Do not create values inside the ticket.
- Add a Reference catalogues area for tenant catalogue records and lifecycle.
  Platform sources are discoverable/read-only there, with explicit ownership.
- Field creation selects Scalar or Governed selection, then an authorised source.
- Show code, label, description, source, requiredness and version; make retirement,
  replacement and requiredness impacts explicit before confirmation.
- Use paginated/searchable lists, audit/history inspection, validation feedback,
  stale-version handling and protection against tenant switches during editing.

Exit condition: an admin can configure a tenant dataset and bind a field without
scripts, while a non-admin cannot perform management writes directly or via UI.

### Phase 6 Ticket and historical readback

- Render source-bound selectors using bounded server search, not full dataset dumps.
- Show source and selected code/label; keep actual record identity in the payload.
- Preserve scalar controls, review/edit/confirm and unchanged retry snapshots.
- Revalidate on confirmation and preserve the draft if a source becomes unavailable.
- Display booked definition/record versions or captured platform labels on detail;
  label a current-name view separately if provided. Do not silently reclassify history.
- Keep counterparty, broker, trader and instrument economics first-class.

Exit condition: configure -> publish -> select -> review -> book -> read historical
detail works for both example sources, including label changes and retirement.

### Phase 7 Robust verification and documented handover

- Lightweight unit tests precede each component; complete integration tests follow.
- Test actual two-tenant datasets, source mismatch, non-admin/revoked membership,
  guessed IDs, malformed values, requiredness changes and source unavailability.
- Test publication/retirement races, stale edits, duplicate management commands,
  atomic rollback, replay after retirement and unchanged-key changed-selection conflict.
- Test label correction versus semantic replacement, preserved historical display,
  legacy scalar/CHOICE values and conversion without inferred mappings.
- Test configuration navigation, tenant switching, selector search/pagination,
  review/edit and uncertain retry interactions.
- Run complete Python/frontend suites, typecheck, build, migration/contract checks
  and scoped browser exercises. Do not submit a real financial trade during UI checks.
- Document actual outcomes, sources, migration/rollback limits, permissions and
  deferred features. Do not merge/push or broaden authority without user direction.

## Research evidence and applicability

Sources were opened and reviewed on 2026-09-30. Recommendations above are project
design choices informed by these sources, not rules prescribed by a single standard.

- [Reltio RDM overview](https://docs.reltio.com/en/applications/rdm/rdm-at-a-glance),
  updated May 5, 2026: reference-data management separates standardised codes,
  classifications and hierarchies from consuming dropdowns. Vendor precedent,
  not a requirement to use Reltio or its tenancy architecture.
- [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/), Recommendation
  August 18, 2009: concept identity, labels, notation, schemes and relations are
  distinct. Useful for catalogue semantics; no RDF/graph implementation mandated.
- [PostgreSQL 18 constraints](https://www.postgresql.org/docs/18/ddl-constraints.html):
  foreign keys enforce identity references, including composite keys; cross-table
  CHECK expressions cannot reliably enforce changing eligibility. Apply FK/unique
  constraints plus transactional validation/appropriate triggers. Confirm the
  actual deployment major version before using any version-specific feature.
- [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  permissions must be checked on every request, including access to guessed IDs.
  Applied to management, searches, assignment and historical reads.
- [Microsoft temporal-table scenarios](https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal/usage-scenarios?view=sql-server-ver17):
  history supports auditing and point-in-time reconstruction. SQL Server-specific
  implementation, cited only for the history use case; not a PostgreSQL prescription.

## Original approval boundary (historical)

At proposal time this plan did not resume the paused implementation. Approval would authorise
the first governed-data slice for trades, with single-select tenant catalogues
and platform currencies. It would not authorise a full MDM system, arbitrary
external sources, credit approval, maker-checker permissions, multiple selection,
hierarchical UI, or instrument/strategy property rollout.
