# Industry standards and integration boundaries

## Evidence status

Standards in this note are boundary vocabularies and adapter targets, not
relational schemas to copy wholesale. Some links are primary-source anchors;
adapter conformance, version selection, and licensing remain implementation
work. See the [external evidence and research register](24-external-evidence-and-research.md)
for the source-vs-design distinction.

## Decision

The PostgreSQL master remains the canonical internal model. Industry standards are used for identifiers, classifications, and integration contracts; their message/XML schemas are not copied directly into relational tables.

```text
External standard or vendor payload
  -> retain raw payload and lineage
  -> map through an adapter
  -> normalize into canonical master/trade/market-data records
  -> publish again in the required standard format when needed
```

This prevents interchange-specific nesting, optionality, and workflow fields from becoming the internal operating schema while preserving fidelity for audit and reprocessing.

## Client ingestion boundary

Offer clients a strict canonical contract while accepting a limited set of practical delivery channels:

```text
HTTPS JSON or multipart upload / SFTP batch file / authorised provider adapter
  -> immutable source payload
  -> tenant-specific mapping version
  -> canonical contract validation and identifier resolution
  -> reconciliation, exception queue, and approval where needed
  -> tenant-scoped operational record or canonical-data proposal
```

The service should support three commercial tiers: documented Fortem templates; maintained adapters for common administrator/custodian/provider exports; and priced, versioned bespoke mappings. The internal contract is never relaxed for a client-specific file.

An ingestion request is asynchronous and idempotent. It returns a durable job resource and retains tenant, source identity, payload hash/locator, schema version, mapping version, received and effective times, resolved IDs, validation issues, and resulting record IDs. Ambiguous identifier matches are exceptions, not guesses.

FundApps documents the same practical pattern: API, SFTP and UI submissions, a limited identifier set, enrichment from the client's data vendor, and transformation into its controlled internal specification. [FundApps Data Adapter](https://docs.fundapps.co/data/ada/propertiesDataAdapterPL.html)  Aladdin and SimCorp similarly retain bulk file rails alongside broader APIs and integration services. [Aladdin Data eXchange](https://www.blackrock.com/aladdin/platforms/products/aladdin-data-exchange) [SimCorp data management](https://www.simcorp.com/solutions/simcorp-one/data-management)

## Core standards stack

| Domain | Standard/source | Use in the platform |
|---|---|---|
| Security identity | ISIN (ISO 6166) | External identifier attached to the correct instrument or listing node. |
| Instrument classification | CFI (ISO 10962) | External/regulatory classification alongside internal taxonomy. |
| Legal entities | LEI (ISO 17442), GLEIF data | Identifier on legal-entity organisations. |
| Organisations | BIC and local registration identifiers | Identifiers on organisations, with source/validity dates. |
| Venues | MIC (ISO 10383) | Controlled venue identifier on listings and execution records. |
| Fiat currencies | ISO 4217 | Currency profile/code. Cryptoassets use their own canonical nodes and codes. |
| OTC derivative messaging | FpML / ISDA | Confirmation, processing, and reporting integrations; semantic benchmark for terms. |
| Securities events | ISO 20022 `seev` | Corporate-action notification, elections, confirmations, reversals, and cancellations. |
| Securities settlement/trades | ISO 20022 securities messages | Integration vocabulary when custody/settlement scope requires it. |
| Electronic execution/market data | FIX | Inbound/outbound orders, executions, streaming market data, and venue integration. |
| Official macro statistics | SDMX | Later integration with official macroeconomic-statistics providers. |
| OTC reporting | UPI, UTI, CDE | Trade/reporting layer, not economic instrument identity. |

## Practical data-model rules

### Identifiers

```text
security_identifier
  identifier_scheme             -- ISIN / FIGI / CUSIP / SEDOL / vendor code / ticker
  identifier_value
  financial_reference_node_id
  source_id
  valid_from / valid_to

org_identifier
  identifier_scheme             -- LEI / BIC / registration number / tax ID / ...
  identifier_value
  org_id
  source_id
  valid_from / valid_to
```

An external identifier is never assumed globally unique without its scheme, source/issuer where relevant, and validity period. A ticker normally belongs to a listing/venue context; an ISIN normally identifies the security/economic issuance.

External systems also use local, provider-specific IDs that are not standards identifiers. Maintain an `external_id_namespace` plus effective-dated `external_object_mapping` service to map a bank, client, custodian, administrator, broker, vendor, or internal system's object ID to Fortem's immutable UUID. Namespace and tenant scope are mandatory parts of the lookup; the same string can legitimately occur in more than one client or provider namespace.

```text
POST /v1/external-id-mappings:resolve
  namespace + external object type + external ID + context + as-of date
  -> one resolved Fortem UUID, an ambiguity/error response, or an onboarding exception
```

Formal identifiers such as ISIN and FIGI remain in the canonical identifier model. The external mapping layer records provider/local identity, mapping method, confidence, verification, source payload, validity and supersession. It must never silently infer a match from a ticker or display name.

### Classifications

CFI, regulatory product classifications, internal business taxonomy, risk taxonomy, and UCITS labels have different purposes. Store each as a separately sourced and effective-dated classification/label assignment. Do not overwrite the internal product type because an external CFI or regulatory code differs in granularity.

### Integration payloads

For FpML, ISO 20022, FIX, and vendor formats, retain:

```text
source_message
  source_message_id
  source_id
  format                         -- FPML / ISO20022 / FIX / VENDOR_JSON / ...
  external_message_reference
  published_at
  received_at
  payload_locator or payload_hash
  processing_status
  normalized_record references
```

The raw payload is evidence. The normalized records are the platform's operational truth after validation and approval.

## FpML boundary

FpML is widely used for OTC derivatives and is useful as a semantic benchmark and integration format. It is not the database schema.

Use it to:

* validate coverage of rate, FX, credit, equity, commodity, repo, and securities-lending economics;
* ingest or emit confirmation/trade-processing messages where counterparties require it;
* retain original source payloads next to normalized terms.

Do not use its XML object nesting, message workflow fields, or party-reference mechanics as the relational master model.

## Scope discipline

Start with the standards that are required by actual source feeds, client/counterparty integrations, or reporting obligations. Do not build adapters speculatively. The internal schemas should expose stable canonical concepts even when upstream vendors change their payload shapes.
