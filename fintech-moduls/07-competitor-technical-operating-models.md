# Competitor technical operating models

## Scope and evidence standard

This paper evaluates what major competitors publicly disclose about how their products operate technically. It does **not** claim knowledge of proprietary internal schemas, infrastructure, algorithms, tenancy isolation, or security implementations that are not public.

The recurring pattern is clear: institutional competitors are managed, integration-led platforms. They accept heterogeneous source data, normalise it into governed domain objects, run named rules or calculations asynchronously, expose results through entitlement-aware APIs, and support a high-touch implementation process.

## Comparative technical map

| Vendor / category | Ingestion and integration | Domain/control model | Computation and workflow | Delivery / commercial pattern |
|---|---|---|---|---|
| FundApps — compliance monitoring | Tenant-specific APIs accept position files in XML/CSV and other formats; SFTP is supported for some feeds; composite data can be uploaded separately. | Input data maps to allowed rule properties; maintained regulatory/rule content is a core service. | Position uploads return an asynchronous job/result link; compliance results are calculated after ingestion. | Managed SaaS plus continuously maintained rules and data integrations. |
| NeoXam DataHub — EDM | REST/GraphQL, S3, SFTP/FTP, queues/JMS/Kafka, email, direct DB/native APIs; vendor connectors and visual mapping. | Golden-copy data domains, field-level ranking/survivorship, data-quality controls, N-eyes approvals, bi-temporal views, entitlements. | Event-driven updates, configurable rules/workflows, exception queues, monitoring. | Configurable enterprise platform plus implementation and managed services. |
| OpenGamma — derivatives calculation | Portfolio files in standard Strata or CCP-specific formats; JSON REST and Java SDK. | Product/methodology availability is entitlement-controlled; the customer provides portfolio data while the service subscribes to required market/CCP scenario data. | `POST` calculation returns `202 Accepted`; caller polls resource for output; what-if jobs and detailed error/result structures are first-class. | Specialist calculation SaaS; coverage/methodology enabled during onboarding. |
| Aladdin — whole-portfolio platform | REST APIs, bulk CSV loaders, SFTP/IBM MQ, secure extracts, Snowflake-backed data cloud, SDKs. | Central data ecosystem with common data language, data dictionary, governed custom development, and broad operational entities. | APIs expose read/write data and operational services; analytics and time-series outputs can be consumed via APIs/data cloud. | Large transformation programme with vendor implementation channels, training, UAT, data interfaces, and partner ecosystem. |
| MSCI — analytics platform | Portfolio analytics exposed through development toolkits/web services and a Python wrapper; input/data details are licensed. | Proprietary risk models and client portfolio data; outputs include granular portfolio/position risk analytics. | Programmatic portfolio analysis and stress-testing access via web services/toolkits. | Licensed models/data/analytics, commonly embedded in client risk processes. |

## Public technical evidence

### FundApps: controlled input contracts plus asynchronous monitoring

FundApps documents a tenant-specific API surface, accepts structured position uploads, and exposes processing as an asynchronous workflow. Its position-upload endpoint returns `202 Accepted`; its earlier API documentation describes a result resource that can be polled after daily position upload. It also documents separate composite/constituent uploads, including SFTP options. [FundApps data specification](https://techdocs.fundapps.co/docs/data-specification), [positions upload](https://techdocs.fundapps.co/docs/positions-upload-v3), [bring-your-own-data](https://techdocs.fundapps.co/docs/bring-your-own-data-guide-byod), [API versioning/deprecation guidance](https://github.com/fundapps/TechDocs)

Technically, this is a strong pattern for Fortem: accept a strict, versioned position snapshot contract; store the raw upload; return an immutable job; run controls asynchronously; and expose results through a stable API. The important distinction is that FundApps sells maintained legal/regulatory content. Fortem should not try to replicate that content operation without a legal-content operating model.

### NeoXam DataHub: enterprise data management as configurable workflow

NeoXam publicly describes a broad ingestion perimeter—files, APIs, queues, email, database access and vendor connectors—then a configurable golden-copy lifecycle with visual mapping, ranking/survivorship, workflows, data-quality checks, exception management, entitlements, and bi-temporal views. It exposes REST/GraphQL APIs and positions deployment as cloud, private-cloud, or hybrid. [NeoXam DataHub](https://www.neoxam.com/datahub/), [NeoXam MDM](https://www.neoxam.com/datahub/mdm/)

Fortem should copy the **boundary discipline**, not the breadth: raw source payload → mapping/proposal → approved canonical fact → distributed API. A universal visual ETL/MDM builder is not an initial Fortem product. The better niche is well-modelled financial objects and operations workflows around derivatives, valuation provenance, and UCITS evidence.

### OpenGamma: narrow compute APIs with explicit method/data boundaries

OpenGamma's API is the most concrete reference for calculation-service design. It uses OAuth 2.0, entitlement-aware discovery of available methods, JSON request/response contracts, a Java SDK, asynchronous calculation resources, polling, granular error objects, and named valuation dates/currencies. It accepts standard and CCP-specific portfolio formats, while OpenGamma itself supplies the licensed market/CCP scenario inputs needed for its calculation service. [OpenGamma API documentation](https://docs.opengamma.com/)

Fortem should adopt this pattern for valuation snapshots, liquidity runs, and risk/control runs:

```text
POST input snapshot / calculation request
  -> 202 + immutable job URI
  -> GET job status
  -> GET completed result, errors, explanation, and snapshot lineage
```

One important difference: OpenGamma says completed calculation results automatically expire after a short period. Fortem's valuation, UCITS-control, and client-reporting results require durable, reproducible retention with policy/version/source lineage.

### Aladdin: platform-plus-ecosystem rather than a monolith

Aladdin publicly describes a cloud-hosted/API-first platform, REST APIs with read/write access to operational services, an API/data dictionary/developer-guide surface, a Snowflake-backed managed data cloud, bulk file loaders, and SFTP/IBM MQ integration. It also explicitly presents implementation as business-process review, data interfaces, training, UAT, and go-live—not a software download. [Aladdin APIs](https://www.blackrock.com/aladdin/platforms/products/apis), [Aladdin Data eXchange](https://www.blackrock.com/aladdin/platforms/products/aladdin-data-exchange), [Aladdin Data Cloud](https://www.blackrock.com/aladdin/platforms/products/aladdin-data-cloud), [Aladdin implementation](https://www.blackrock.com/aladdin/discover/resources/implementations)

The strategic lesson is not to imitate its whole-portfolio scope. It is to make Fortem's platform **open at the boundary**: stable APIs, generated clients, data dictionaries, bulk import/export, supported integration patterns, and room for client-specific calculations without contaminating canonical shared data.

### MSCI: models and analytics delivered programmatically

MSCI exposes API/toolkit access to portfolio analysis, stress testing, and granular risk results, including a Python wrapper for Barra PortfolioManager/BarraOne interfaces. [MSCI developer library](https://developer.msci.com/code-libraries/msci-bdt-package), [MSCI APIs](https://developer.msci.com/apis)

This reinforces that Fortem should preserve its existing Python models behind explicit versioned service contracts. The external API should carry input snapshot, model/version, scenario/policy, output, and explanation—not require clients to absorb Fortem's internal Python implementation.

## Shared design patterns to adopt

### 1. Contracted ingestion, not direct database access

Support a small number of typed channels in V1:

```text
HTTPS JSON / multipart upload
SFTP batch file
authorised provider adapter
```

Every submission receives an immutable `source_payload_id`, schema version, checksum, source/tenant identity, received time, parser/mapping version, and processing status. Expand to queues and event streaming only when an integration requires them.

### 2. Asynchronous, durable job resources

Large control, valuation, liquidity, and risk calculations must not be synchronous HTTP calls. Use job resources with idempotency keys and durable results:

```text
POST /v1/control-runs
Idempotency-Key: client-generated-key

202 Accepted
Location: /v1/control-runs/{runId}

GET /v1/control-runs/{runId}
  status = QUEUED | RUNNING | COMPLETED | FAILED | CANCELLED
```

The completed result links input snapshot, policy/methodology, code version, calculated timestamp, full error list, and retained explanation. Results are immutable; a correction is a later run.

### 3. Canonical core plus configurable policy layer

Keep canonical instrument/market-data economics relational and governed. Place client-specific valuation policies, control thresholds, sleeve methodology, mappings, and report definitions in tenant-scoped versioned policy objects. Do not introduce a generic no-code schema builder in the initial product.

### 4. Entitlements throughout the data path

Use entitlement checks at ingest, storage classification, resolver selection, API read, bulk export, and client report generation. A shared observation may be physically retained but cannot be surfaced to a tenant without dataset/use entitlement. This is stricter than merely isolating tenants by UI or database schema.

### 5. Implementation is part of the product

Treat onboarding as an explicit technical workstream:

```text
data inventory and rights review
-> canonical mapping and reconciliation fixtures
-> sandbox integration
-> historical replay / golden-master comparison
-> UAT and controls approval
-> production cutover with parallel run
```

Publish connector contracts, supported formats, rate/size limits, API versioning, and deprecation policy. Fortem should generate Pydantic/OpenAPI contracts and TypeScript/Python clients from the same source.

## What not to copy

* Do not build a global security-data catalogue or broad connector marketplace before a customer proves the need.
* Do not promise continuously maintained legal rules across jurisdictions without dedicated legal-content ownership.
* Do not copy an incumbent's broad IBOR/OMS/accounting scope.
* Do not treat a generic data lake or BI dashboard as a canonical control plane.
* Do not expose raw vendor data through APIs without explicit licensing and entitlement controls.

## Technical differentiation for Fortem

Fortem should be opinionated where generic platforms are necessarily broad:

```text
canonical economic terms for OTC and structured products
+ versioned barriers, schedules, legs, composition, and lifecycle events
+ valuation-source and override provenance
+ UCITS/liquidity evidence tied to actual economic look-through
+ stable APIs around existing Fortem Python analytics
```

That combination is technically credible, commercially narrow enough to deploy, and difficult to achieve through generic EDM or generic compliance configuration alone.
