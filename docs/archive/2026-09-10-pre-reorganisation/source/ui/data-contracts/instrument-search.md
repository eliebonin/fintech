# Contract: instrument search view

The first UI contract is intentionally view-oriented. It is not a projection
of SQLAlchemy tables and it contains no tenant credentials.

## Request

```http
GET /api/instruments/search?q={query}
```

The authenticated server derives tenant and user-account context from the
session. The BFF sends both `X-Tenant-Id` and `X-User-Account-Id`; a request
query parameter cannot select another tenant, and the API accepts the request
only when that account has an active effective membership.

## Response

```json
{
  "data": [
    {
      "instrumentId": "0198f4de-...",
      "canonicalName": "HSBC Holdings plc ordinary shares",
      "instrumentType": "EQUITY",
      "assetClass": "EQUITY",
      "status": "ACTIVE",
      "issuer": "HSBC Holdings plc",
      "baseCurrency": "GBP",
      "definitionVersion": 3,
      "effectiveFrom": "2025-01-01",
      "identifiers": [{ "scheme": "ISIN", "value": "...", "scope": "INSTRUMENT" }],
      "mappings": [{ "namespace": "BANK_A_STATIC_PROD", "externalId": "ABC", "status": "VERIFIED", "mappingRole": "PRIMARY" }],
      "listings": [],
      "taxonomy": ["LISTED_EQUITY"],
      "notes": "..."
    }
  ],
  "meta": {
    "tenantContext": "demo-tenant",
    "source": "synthetic-fixture",
    "generatedAt": "2026-09-01T00:00:00Z"
  }
}
```

`meta.source` is mandatory during fixture mode and must be replaced with an
auditable API/provider lineage value before production use. Production
responses should add correlation ID, entitlement decision, effective-version
metadata, and structured errors without exposing database topology.
