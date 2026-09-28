# Index onboarding

## User goal and roles

An Operations user creates a proposal for one concrete index variant. The page
is deliberately sparse: it captures canonical identity and the minimum
classification needed to route enrichment, while allowing a provider or
steward to complete methodology facts later. The browser never creates an
approved canonical index directly.

The screen requires an authenticated tenant context and an active user-account
membership. Operations stewards approve or reject the resulting proposal from
the normal reference-data work queue.

## Identity boundary

The form creates an economic `INDEX` reference node. It does not create a
listing, an instrument execution record, or a market-data series. The
canonical name should identify the concrete return/currency variant, for
example `S&P 500 Net Total Return USD`; the internal code is an optional,
unique, human-friendly alias and is not the UUID identity.

An optional family name groups related variants such as price return, gross
total return, and net total return. Variants remain separate nodes with their
own identifiers, provider mappings, methodology, and series.

## Fields

### Required

- `canonicalName` — official descriptive name of the concrete variant.
- `effectiveFrom` — date from which the proposed canonical definition applies.
- `indexKind` — `PUBLIC`, `QIS`, `PROPRIETARY`, or `CUSTOM_BASKET`.

`indexKind` is selected from the active `secm.index_kind_catalogue`, not from
frontend-only labels. The catalogue supplies the display name, governed
description, dissemination class, methodology-ownership classification, and a
short example. Dissemination and ownership are deliberately separate: a
publicly quoted index such as S&P 500 can still have a provider-owned
methodology. The API validates that the submitted code is active in this
catalogue before accepting the proposal.

### Optional catalogue-backed fields

- `returnProfileId` — governed return semantics, such as price return or net
  total return;
- `baseCurrencyId` — currency of the published index level;
- `administratorOrganisationId` and `calculationAgentOrganisationId` — active
  organisation references.

- `indexFamilyId` — an existing active family selected from the database-backed
  family catalogue. Family identity is not free text on the variant form; a
  missing family is a separate Operations setup task.

The page loads these options server-first through tenant-authenticated
reference-data queries and renders the options into the initial HTML. The BFF
routes remain available for browser/API consumers, but the first paint does not
depend on a client-side fetch or hydration completing. Only active catalogue
rows visible to the tenant are offered.

Currency options are returned by `GET /v1/currencies?groups=...` as labelled
groups. The index form starts with `REGULAR` (`FIAT`) currencies and offers an
`Include cryptoassets` toggle; enabling it requests `REGULAR,CRYPTO`, where
`CRYPTO` contains `CRYPTOASSET` and `STABLECOIN` roles. This is a selector
configuration and display default, not a rule that an index must be fiat
denominated. Newly approved crypto currency roles appear automatically.

## Family setup

Family creation is intentionally a separate Operations screen at
`/instruments/index-families/new`. It captures a canonical family name, an
optional unique internal code, and an optional provider/administrator
organisation selected from the active organisation catalogue. The screen
submits `POST /api/instruments/index-families`, which forwards to
`POST /v1/index-family-proposals` and creates a pending
`CREATE_INDEX_FAMILY` proposal. It does not create an index variant, listing,
or market-data series.

The approval endpoint is
`POST /v1/index-family-proposals/{proposal_id}/decision`. Approval creates a
non-tradable `INDEX_FAMILY` financial-reference node, a `secm.index_family`
row, and a tenant-private scope row. The approved family then appears in the
DB-backed family selector on this page. Pending family and concrete-index
proposals are both reference-data work-queue items.

### Optional methodology facts

Base date/level, weighting method, rebalance and calculation frequency,
dividend treatment, launch date, methodology reference/URI, and a flag that
the known history includes back-tested or simulated observations. These facts
are stored in an effective-dated methodology version when the proposal is
approved; they are not encoded as mutable taxonomy labels.

## Workflow and states

1. The user enters the identity and any known facts.
2. The browser submits `POST /api/instruments/indices` with
   `submissionMode = MANUAL`.
3. The BFF forwards the payload to `POST /v1/index-proposals`.
4. The API validates catalogue references and persists a `PENDING`
   `CREATE_INDEX` proposal with an immutable payload.
5. Operations approves or rejects the proposal. Approval atomically creates
   the `INDEX` node, selected `INDEX_FAMILY` relationship, `index_terms`,
   optional `index_methodology_version`, tenant scope, and approval evidence.

The page displays catalogue loading and error states, allows optional fields to
remain blank for enrichment, and shows the returned proposal ID/status after
submission. An API error leaves the form values intact so the user can correct
or resubmit without creating a partially approved record.

## Deferred scope

Constituent snapshots, provider-specific methodology parsing, automated source
matching, and full approval-detail UI are separate slices. These screens do
not create market-data series or infer an index listing from an index identity.

## Acceptance examples

- Submit `S&P 500 Net Total Return USD`, `PUBLIC`, the DB-backed `MVP S&P 500`
  family, a USD base currency, and a Bloomberg administrator. The response is
  `PENDING`; no index row is active until approval.
- Submit a proprietary QIS with only a name and effective date. The response
  remains `PENDING` and optional catalogues can be enriched later.
- Leave `returnProfileId` blank: the page permits it, but the approval workflow
  must not silently infer return semantics from the name.
- Submit a family first, approve it, then select its returned `indexFamilyId`
  when creating a concrete variant; family creation and variant creation stay
  separate audit events.
