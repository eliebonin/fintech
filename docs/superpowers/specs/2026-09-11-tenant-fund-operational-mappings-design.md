# Tenant Fund Operational Mappings — Design

**Status:** Approved for implementation  
**Date:** 2026-09-11  
**Owners:** Tenant operations, fund operations, and platform data engineering

## Decision

Use tenant-scoped, effective-dated operational identifier mappings to resolve
administrator, agent, and custodian records to a canonical fund or fund share
class. These mappings are not shared security-master identifiers.

The shared master continues to own the canonical organisation for a provider
such as an administrator or custodian. A tenant owns the feed configuration,
the operational meaning of a source identifier, and its mapping to that
tenant's fund structure.

## Scope

The first slice supports IDs supplied by one external party for:

| External record scope | Canonical target | Example |
| --- | --- | --- |
| `FUND` | `secm.fund.fund_reference_node_id` | ABC accounting portfolio `ACCT-1042` |
| `FUND_SHARE_CLASS` | `secm.instrument.instrument_node_id` | ABC valuation class `NAV-I-GBP` |

Each ID is interpreted under an explicit mapping profile, for example
`ABC_DAILY_ACCOUNTING` or `ABC_DAILY_VALUATION`. The profile—not a convention
embedded in the ID string—defines the provider, source system, dataset/feed,
parser contract, and operational context.

This first slice deliberately excludes custody-account and strategy targets.
They can be introduced as a separate `OPERATING_ACCOUNT` scope when an actual
feed needs them; forcing that hierarchy into V1 would make simple fund-file
resolution harder to operate.

## Data model

### `cfg.external_data_mapping_profile`

A tenant-owned configuration record for one interpretable inbound data domain.
It has a provider organisation, integration source system, optional governed
dataset, profile code, display name, context (`VALUATION` or `ACCOUNTING` in
V1), parser contract version, status, and effective period. It declares whether
the profile accepts `FUND`, `FUND_SHARE_CLASS`, or both.

`cfg` is used because this is tenant operational configuration, distinct from
the shared canonical `secm` domain, raw integration payloads in `ing`, and
market-data rights in `md`.

### `cfg.external_data_object_mapping`

An approved, time-bound translation from a provider’s operational ID to one
canonical fund object. It references a mapping profile and stores:

- source scope and target UUID;
- exact received value and separately normalised lookup value;
- mapping role, method, lifecycle status, confidence and approval evidence;
- business validity, record time, source payload and supersession lineage.

The exact received value is never overwritten. Normalisation is profile-driven
and conservative (for V1: trim surrounding whitespace and uppercase only when
the profile declares case-insensitive matching).

## Resolution and history

The resolver receives `(tenant_id, profile_id, external_id, report_business_date)`.
It normalises the lookup value according to the profile and selects exactly one
`APPROVED` mapping valid on the report business date. No mapping returns an
explicit unresolved result; multiple applicable mappings are an exception.

An ingestion result must retain the resolved mapping ID and the report’s source
payload ID. This makes a later mapping correction non-retroactive: a historical
file keeps the mapping version actually used, while a correction or reprocess
creates a distinct run/result rather than rewriting history.

PostgreSQL exclusion constraints prevent overlapping approved validity ranges
for the same tenant, profile, scope, and normalised external ID. The service
also validates that target UUIDs belong to the declared target table.

## Relationship to the existing generic mapping layer

`ing.external_object_mapping` remains the canonical/shared mapping mechanism
for vendor, bank, client, custodian, and provider aliases across general
objects. It is not replaced. The `cfg` mapping is deliberately narrower:
it resolves tenant-owned administrative records whose meaning changes by feed
and operating purpose.

No security-master ID is inferred or promoted merely because a tenant adds a
mapping. Promotion follows the existing controlled reference-data workflow.

## API and UI boundary

The initial API is service-level and testable. A later Fund Management Config
screen can expose:

1. integrations and mapping profiles;
2. an approved mapping list grouped by `ACCOUNTING` and `VALUATION`;
3. unresolved daily-feed IDs that can create mapping proposals;
4. effective-date and supersession history.

The UI displays fund and share-class names/codes, not raw UUIDs by default.

## Controls and failure handling

- `PROPOSED`, `APPROVED`, `REJECTED`, `RETIRED`, and `SUPERSEDED` are governed
  statuses; only `APPROVED` resolves production input.
- A mapping is retired/superseded; it is not deleted.
- A provider ID may recur in a different profile, but not ambiguously in the
  same profile and source scope during overlapping business dates.
- Files retain raw payload, report business date, receipt time, parser version,
  mapping profile and individual mapping IDs.
- Dataset and licence rights remain attached to data delivery/observations;
  they are not copied redundantly to each mapping row.

## Deferred decisions

1. `OPERATING_ACCOUNT` mappings for custody accounts, subaccounts and strategy
   scopes.
2. Maker-checker policy configuration per tenant and profile.
3. Rich profile-specific normalisation expressions and checksum validation.
4. File-parser adapters and persistence of import rows/runs beyond the existing
   raw-payload lineage.
5. Fund Management Config UI and approval workflow.

## Research basis

Industry data models distinguish fund, portfolio and share-class scope rather
than treating an institution’s identifiers as universally interchangeable.
Openfunds provides field-level standardisation for fund data exchange; ISO
20022 includes separate securities custody and accounting report families; and
fund-provider schemas expose a dedicated accounting identifier alongside
share-class valuation data.

- [openfunds FAQ](https://openfunds.org/knowledge/faq/)
- [ISO 20022 securities message definitions](https://www.iso20022.org/iso-20022-message-definitions?business-domain%5B0%5D=6)
- [NN Group Shareclass Static API](https://developer.nn-group.com/api/shareclass-static/documentation)
