# Critical review and delivery choices

## Review conclusion

The shared canonical identity model is retained without redesign:

```text
financial_reference_node
  -> economic instrument
  -> venue listing when tradeable on a venue
```

Fortem UUIDv7 remains the immutable internal identity. Formal identifiers and all provider, bank, client, custodian, and legacy codes remain effective-dated mappings; none becomes a primary key.

The table layer is useful, but table breadth must not substitute for operating controls. Delivery therefore shifts from adding product tables to completing one tenant-safe, reproducible Soft-NAV vertical slice.

## Choices adopted

1. Introduce versioned database migrations before non-synthetic data is accepted. SQLAlchemy metadata remains the model source; migrations become the controlled way to evolve deployed databases.
2. Use one central canonical/market-data database plus one isolated logical
   operational overlay database per tenant. Make tenant ownership explicit in
   overlay records; use RLS as defence in depth after the database-routing and
   authenticated-role model is established.
3. Build the market-data resolver as a service with fixed precedence: exact series, exact canonical node, instrument type, then policy default. Do not build a generic rules language.
4. Treat `market_date`, valuation date, source timestamp, receipt timestamp, and information cut as distinct. The resolver never uses an observation received after the historic information cut.
5. Add fund, umbrella/sub-fund, and share-class semantics before adding further exotic product terms. Fund NAV/dealing/publication conventions are first-class data.
6. Add bond coupon and accrual terms alongside the fund slice because daily NAV needs accrued interest, not only bond clean prices.
7. Implement corporate-action application only after the resolver and position snapshot boundaries are stable. Raw observations remain immutable; transformations create attributable derived results.
8. Keep FpML, FIX, ISO 20022, vendor payloads, and files at the integration boundary. Store retained payloads and mappings, not a duplicate interchange-schema hierarchy.
9. Replace real-brand mock fixtures with fictional names and correct semantic inconsistencies before client demonstrations.

## Explicit non-goals

* No claim that Soft NAV is official administrator NAV or UCITS fund accounting.
* No duplicate table for T-1 prices.
* No tenant access based on knowledge of UUIDs.
* No uncontrolled free-text product-type logic.
* No production market-data redistribution assumption merely because data is physically stored.

## Delivery gates

| Gate | Required evidence |
|---|---|
| Schema | A blank PostgreSQL database reaches the current version only through migrations; upgrade and downgrade tests pass. |
| Tenancy | Cross-tenant reads and writes are denied through application and database tests. |
| Mapping | Ambiguous, expired, overlapping, or type-incompatible external IDs produce durable exceptions. |
| Resolver | Entitlement, policy precedence, valuation date, cut-off, staleness, and override decision are frozen in a snapshot. |
| Fund Soft NAV | A fund share class using T-1 NAV, a bond with accrued interest, cash, and FX is reproducible against a golden expected result. |

## Deferred decisions recorded at the V1 boundary

1. **Soft-NAV expansion.** V1 supports only same-currency position lines. The
   next calculation increment adds cash snapshots, frozen FX resolution, coupon
   and accrual calculation, liabilities, reconciliation and approved overrides.
   Price and FX inputs must each retain named valuation cut, information cut,
   series, observation, dataset, entitlement and policy lineage.
2. **Tenant isolation.** The adopted boundary is a central core plus one
   tenant-specific overlay database per client. Cross-database UUIDs are
   validated through the canonical API because PostgreSQL cannot provide
   ordinary cross-database foreign keys. RLS remains defence in depth and waits
   for authenticated database roles/session claims and complete policy coverage.
3. **Corporate-action materialisation and custody.** V1 derives adjusted values
   without mutating source facts. Persisted derived histories, account
   entitlements, elections, tax, claims and custody postings are deliberately
   deferred to a separate operational lifecycle scope.
4. **Production integration contracts.** Local deterministic loaders prove the
   data flow but are not production ingestion. Versioned API/file contracts,
   raw-message retention, validation/error queues, idempotency, generated
   clients and consumer contract tests remain a dedicated delivery slice.
| Corporate actions | Split/dividend effects are reproducible from event information available at the historic cut. |

## Research basis

IOSCO calls for documented asset-appropriate valuation methods and price-source selection criteria. FCA valuation guidance calls for fair and accurate valuation, source reliability, recorded alternative sources, reconciliation and tolerance controls. Vendor licensing can apply to downstream and derived outputs. These support the above controls; they do not require an early generic rules engine.

Sources: [IOSCO valuation principles](https://www.iosco.org/library/pubdocs/pdf/ioscopd413.pdf), [FCA COLL 6.3](https://handbook.fca.org.uk/handbook/coll6/coll6s3?timeline=true), [LSEG redistribution guidance](https://www.lseg.com/en/data-analytics/market-data/data-redistribution).

## Foundation-control implementation status

The additive foundation slice implements the six controls identified as P0:

The UI-driven schema hardening follow-up is documented in
[`docs/architecture/schema-hardening.md`](../docs/architecture/schema-hardening.md).
It adds tenant membership, tenant-owned external mappings, entitlement-aware
reference API reads, version-aware instrument/listing reads, observation
idempotency, series dimensions, and explicit Soft-NAV price/FX input links.
Field-level overrides, runtime tenant-database routing, RLS, full volatility
surface modelling, and complete subtype applicability rules remain deferred.

* trusted tenant routing through `ten.tenant_database_registry`;
* effective-dated, approved instrument and listing definition versions;
* tenant-local evidence for UUID links to the central canonical database;
* append-only trade lifecycle/correction events with source idempotency keys;
* generic tenant valuation marks requiring a resolution snapshot or approved
  override; and
* source-vintage publication/receipt lineage for historic market-data cuts.

The pure validation contracts are tested. Live PostgreSQL upgrade/downgrade,
RLS/session-context enforcement, production tenant provisioning, version-table
backfill, and typed override approval remain delivery gates rather than being
silently implied by the model additions.
