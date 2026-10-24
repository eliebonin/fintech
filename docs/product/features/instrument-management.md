# Instrument management — capability records

23 October F08/F09: [AMC delivery](../../delivery/amc-onboarding-20261023.md)
adds native certificate creation, current-dependency approval and inspection.
Shared security/booking machinery is reused; the draft fund page is not used
as a persistence workaround.

**Status:** Maintained reference  
**Content type:** Capability reference  
**Owner:** Security-master engineering/operations  
**Last reviewed:** 2026-10-12

[Feature register](../feature-register.md). Product details: [creation and booking](product-booking.md).

## F07 Catalogue and details

- **Desired:** Search shared/private references and identifiers, paginate and inspect without catalogue overload.
- **Status / backend / frontend:** ALPHA. Batched compact catalogue, richer search/detail, tenant filters and correlated listing identifiers; `/instruments` filters/pages/details.
- **Cuts/trade-offs:** Deep evidence stays on detail; server pagination instead of full-universe downloads.
- **Weaknesses:** Large-volume evidence is bounded/synthetic; full-detail reads remain heavier; execution-date readiness can differ from search readiness.
- **Remaining:** Realistic performance/accessibility acceptance and targeted query tuning as the universe grows.
- **Evidence:** [Performance](../../delivery/instrument-catalogue-performance-2026-10-08.md), [search/permissions](../../delivery/swap-search-and-permission-ui-2026-10-06.md), [query](../../../apps/reference_api/instrument_catalogue.py).

## F08 Canonical instruments and listings

- **Desired:** Economic reference separate from listing; contextual and standalone listing creation.
- **Status / backend / frontend:** ALPHA. Governed versions, listings, mappings and private scopes; type-selected forms and contextual listing launch.
- **Cuts/trade-offs:** UUID is identity; ISIN/ticker/provider symbols are mappings. Listing eligibility depends on product/terms.
- **Weaknesses:** Approval does not imply booking, data or valuation support. Today's identifiers do not prove historical continuity.
- **Remaining:** Duplicate detection, stewardship, promotion/amendment controls (F11), preservation of contextual navigation. See the [proposed shared/private ownership direction](#proposed-direction-shared-and-tenant-private-stewardship); it is not an implementation claim.
- **Evidence:** [Capability matrix](../../delivery/booking-capability-matrix.md), [reference architecture](../../architecture/security-master/README.md), [API](../../../apps/reference_api/main.py).

## F09 Requests and approval

- **Desired:** Instrument-only creation requests and a separately accessible broader Operations queue.
- **Status / backend / frontend:** ALPHA. Scoped proposals/append-only decisions and approval dependency checks; Requests and `/operations` for listing/mapping/review work.
- **Cuts/trade-offs:** Manual governed approval, not a combined creation/NAV/data review bundle.
- **Weaknesses:** Product-specific coverage; no universal change-impact or private-to-shared promotion workflow.
- **Remaining:** Impact-aware amendment review and scalable queue/audit reporting; contractual lifecycle remains separate.
- **Evidence:** [Approval hardening](../../delivery/quality-reviews/2026-10-05-cash-and-approval-integrity.md), [trade-side acceptance](../../delivery/trade-side-acceptance-2026-10-06.md), [workflow](../../../ui/workflows/instrument-review.md).

## F10 Instrument taxonomy

- **Desired:** Tenant-curated classifications attached to references without altering shared economic identity.
- **Status / backend / frontend:** FOUNDATION. Generic taxonomy/classification model and seeded classifications; some type-specific choices, no established general tenant taxonomy management UI.
- **Cuts/trade-offs:** Instrument taxonomy is not the delivered trade-property catalogue feature.
- **Weaknesses:** General tenant definition/value/assignment governance and historical selection are not end-to-end verified.
- **Remaining:** Scoped definitions, governed values, effective assignments, permission-aware administration and report/search consumption.
- **Evidence:** [Identity model](../../../security-master-notes/02-reference-identity-model.md), [schema](../../../security_master_schema/models.py), [creation matrix](../../delivery/booking-capability-matrix.md).

## F11 Instrument amendments and lifecycle

- **Desired:** Changed terms, activation/retirement and promotion preserve historical approvals and booked economics.
- **Status / backend / frontend:** PARTIAL. Version/date/active-scope checks exist; creation/review/inspection UI, not a universal safe amendment editor.
- **Cuts/trade-offs:** Unsupported changes are refused rather than rewriting old facts; trade corrections are a separate workflow.
- **Weaknesses:** Amend/promote/retire and downstream-impact UX are uneven across product types.
- **Remaining:** Explicit amendment policy and impact review with immutable BOOKED conventions. Maturity/settlement belongs to F24/F47.
- **Evidence:** [Integrity review](../../delivery/quality-reviews/2026-10-05-instrument-integrity.md), [historical rules](../../delivery/historical-booking-and-record-corrections-alpha.md), [definition-history regressions](../../../tests/test_cash_definition_history.py).

## Proposed direction: shared and tenant-private stewardship

**Recorded:** 17 October 2026
**Status:** On hold at the user's request, 17 October 2026. Retained for future
discussion; current pages and permissions stay unchanged. No implementation,
migration or authority change authorised by recording this note.

The governing distinction should be ownership/visibility and publication
authority, not instrument type or listed-versus-OTC classification.

- **Shared catalogue:** The platform curates canonical public instruments and
  listings. Tenants search/reuse them, request missing instruments/listings and
  propose corrections. Shared publication/amendment belongs to explicit platform
  stewardship; tenant approval must not automatically publish to every tenant.
- **Private references:** Appropriately authorised tenants may create and approve
  tenant-private records of any supported type: bespoke derivatives, private
  bonds, unlisted equity, private funds or confidential structured products.
  Do not restrict tenant creation solely to an OTC asset-type allowlist.
- **Tenant overlays:** Internal identifiers, labels, taxonomy and governed price
  sources remain tenant-scoped layers rather than reasons to duplicate a shared
  security or silently alter its economic terms. A private price does not turn
  its shared instrument into a private security.
- **Duplicate control:** Search/match before creation, with identifier and
  canonical/listing distinctions. A tenant's request for a missing public
  security should lead to reviewed onboarding, not uncontrolled shared duplicates.
- **Promotion:** Private-to-shared publication needs explicit platform review of
  identity, duplicates, dependency visibility, data rights and confidentiality.
  Preserve booked UUID links and frozen evidence; do not automatically expose
  counterparty-specific terms, tenant data or confidential dependencies.

### Remaining design and implementation work

Specify the platform-versus-tenant authority matrix, missing-public-instrument
request path, duplicate handling and promotion/amendment semantics. Audit the
existing writers and approval paths before claiming this boundary is enforced
consistently across all products. Decide how to resolve overlapping private and
shared identities without rewriting historical bookings. Creation/approval
continues to be distinct from booking and valuation readiness.

Existing F08/F09/F11 capability classifications remain unchanged. This is a
recorded direction, not a new delivered module or a request to build it now.

### Reference and applicability

Reviewed 17 October 2026: [LSEG DataScope Select user guide, January 2021](https://developers.lseg.com/content/dam/devportal/api-families/datascope-select/datascope-select-rest-api/documentation/overview-and-concepts/dss_14_5_user_guide.pdf)
distinguishes supplied reference coverage and user-defined instruments. This is
a historical product example supporting coexistence of supplied/custom records,
not an industry mandate for our tenant permissions or a claim about the latest
product release. The stewardship recommendation above is a project design choice.
