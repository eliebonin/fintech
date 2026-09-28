# Tenant fund operational mappings

**Status:** Accepted and implemented  
**Content type:** Architecture and operational-control specification  
**Owner:** Fund operations and tenant data operations  
**Last reviewed:** 2026-09-11

## Purpose

An administrator, agent, custodian, or bank can use different identifiers for
the same tenant fund structure: for example, a fund-level accounting ID, a
fund-level valuation ID, and different IDs for every share class. This design
resolves those records without turning a tenant's operational code into a
shared security-master identifier.

## Ownership boundary

| Domain | Owns | Does not own |
| --- | --- | --- |
| `secm` | Canonical provider organisation, fund vehicle, share-class instrument | A tenant's ABC feed codes |
| `ing` | Source systems, raw payloads, generic provider/custodian aliases | Interpretation of one tenant's daily feed |
| `cfg` | Tenant feed configuration and approved fund/share-class mappings | Shared canonical identity or entitlements |
| `md` / `ten` | Dataset/licence governance and entitlement | Per-row operational mapping semantics |

The provider organisation is canonical and shared. Its feed configuration and
identifiers are local to each tenant.

## Tables

### `cfg.external_data_mapping_profile`

One effective-dated profile defines an interpretable input domain, such as
`ABC_DAILY_VALUATION` or `ABC_DAILY_ACCOUNTING`. It records the tenant,
provider organisation, integration source system, optional dataset, parser
contract version, operational context, accepted source scope, normalisation
mode, lifecycle status, and validity period.

V1 contexts are `VALUATION` and `ACCOUNTING`. Accepted source scopes are
`FUND`, `FUND_SHARE_CLASS`, or `BOTH`.

### `cfg.external_data_object_mapping`

One effective-dated row translates an incoming identifier under one profile:

| Incoming scope | Target type | Target table |
| --- | --- | --- |
| `FUND` | `FUND` | `secm.fund` |
| `FUND_SHARE_CLASS` | `FUND_SHARE_CLASS` | `secm.instrument` |

The database requires target type to match source scope in V1. A PostgreSQL
trigger verifies the target UUID belongs to the appropriate canonical table.

Every row preserves `external_id_raw` exactly as received and separately stores
`external_id_normalized` for lookup. V1 normalisation is conservative:
`EXACT` or `TRIM_UPPER`. It never removes punctuation, leading zeroes, or
guesses a checksum.

## Resolution and history

The resolver accepts:

```text
tenant_id + mapping_profile_id + external_id + report_business_date
```

It normalises the lookup value using the profile policy and selects one
`APPROVED` mapping effective on the report business date. No result is an
unresolved mapping exception; two results are an ambiguity error.

The report business date—not the receipt timestamp—selects the mapping. The
import must persist both the raw `source_payload_id` and resolved
`external_data_object_mapping_id`. A later mapping correction therefore cannot
silently reinterpret a previously processed historic file.

## Controls

- Only `APPROVED` mappings can resolve production records.
- Corrections retire or supersede mappings; rows are not deleted.
- PostgreSQL prevents overlapping approved ranges for a profile, source scope,
  and normalised ID.
- The same source ID may appear in separate accounting and valuation profiles.
- Dataset and licence rights stay on governed data delivery and are not copied
  into each operational mapping row.

## Example

| Profile | Incoming ID | Scope | Canonical outcome |
| --- | --- | --- | --- |
| `ABC_DAILY_ACCOUNTING` | `ACCT-1042` | `FUND` | Fortem Demo Income Fund |
| `ABC_DAILY_VALUATION` | `NAV-I-GBP` | `FUND_SHARE_CLASS` | Fortem Demo Income Fund I Acc GBP |

The synthetic fixture retains the valuation source value as `" NAV-I-GBP "`
while resolving through `NAV-I-GBP`, proving raw source evidence and lookup
normalisation are different fields.

## Relationship to generic mappings

`ing.external_object_mapping` remains the general, time-bound mapping layer
for shared canonical identifiers, listings, trades, people, and organisations.
The `cfg` mapping is deliberately narrower: a code whose meaning depends on a
tenant's provider feed and accounting or valuation context.

## Deferred work

1. `OPERATING_ACCOUNT` scope for custody accounts, subaccounts and strategy
   ownership.
2. Per-tenant/profile maker-checker configuration.
3. Provider-specific normalisation and checksum rules beyond V1 modes.
4. Import-run and import-row persistence beyond the retained raw payload.
5. Fund Management Config UI for profiles, mappings and unresolved-ID review.

## Related material

- [Approved design](../../superpowers/specs/2026-09-11-tenant-fund-operational-mappings-design.md)
- [Implementation plan](../../superpowers/plans/2026-09-11-tenant-fund-operational-mappings.md)
- [Integration and data rights](../integrations-and-data-rights/README.md)
- [Tenant overlays, client ingestion, and Soft NAV](../../../security-master-notes/15-tenant-overlays-client-ingestion-soft-nav.md)

## Verification

Focused verification covers metadata, pure resolver behaviour, deterministic
PostgreSQL fixtures, compilation, and Alembic SQL generation. Migration SQL
generation does not by itself mean the migration has been applied to Docker.

Verified on 2026-09-11:

```text
.venv\Scripts\python.exe -m unittest tests.test_schema_metadata -v
23 tests passed

.venv\Scripts\python.exe -m pytest tests/test_external_mapping_rules.py \
  tests/test_tenant_operational_mapping_resolution.py \
  tests/test_tenant_operational_mapping_database.py -v
8 tests passed

.venv\Scripts\python.exe -m pytest tests/test_alembic_offline_sql.py -v
1 test passed
```

The local fixture test uses the project’s `create_schema()` convenience helper,
which now creates `cfg` for metadata-driven demo environments. Production-like
database deployment must use Alembic revision `20260911_41`; it has not been
applied automatically by this implementation task.
