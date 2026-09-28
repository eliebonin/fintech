# Scope and design principles

## Purpose

Build a PostgreSQL-backed canonical reference-data master for financial instruments. The master is the authoritative record of what an instrument is, how it relates to other financial objects, where it trades, and how its data has changed over time.

## Initial asset universe

* Currencies and FX pairs
* Indices and QIS indices
* Equities, ETFs, bonds, funds, fund share classes, and AMCs
* FX forwards, futures, vanilla options, swaps, structured products, and composed options

## First-release boundary

The first release owns canonical reference data. It does **not** initially own positions, valuations, P&L, or a full pricing engine.

It must be ready to support them later by providing stable IDs, explicit terms, source provenance, market references, and relationships.

The platform has two deliberately separate data planes:

* **Shared canonical data:** Fortem-governed instruments, listings, entities, identifiers, reference data, and market-data observations that may be used under the applicable licence.
* **Tenant-scoped data:** client positions, cash, private instruments, aliases, classifications, valuation policies, approved overrides, Soft-NAV inputs and results.

A tenant overlay may reference a shared UUID but never mutates the shared canonical record. A private tenant instrument may be promoted into the shared master only through an explicit validation and approval workflow that does not disclose confidential terms.

## Operating model

Operations creates the canonical instrument when it is needed. Vendor and internal-system data enrich the record, propose changes, and provide source lineage. Operations remains the authority for canonical changes and overrides.

## Principles

1. **Separate economic identity from venue identity.** An instrument is what a contract or security is; a listing is how and where it trades.
2. **Keep source observations separate from golden data.** Vendor and internal source values must remain traceable even when a canonical value is corrected.
3. **Do not encode economics in labels.** Instrument types and terms describe contracts; desk labels belong in a governed taxonomy.
4. **Make relationships explicit.** Underlyings, components, issuers, funds, share classes, and indices must be modelled links, not text fields.
5. **Record market-data meaning.** Official venue closes, evaluated prices, composites, and internal marks are different observations.
6. **Prefer extensibility at contract-leg boundaries.** Derivative economics evolve; fixed two-column designs should be views over a general model where possible.
7. **Resolve values under an explicit context.** A client valuation policy and entitlement set select a usable value; they do not alter the source observation.
8. **Treat client intake as a controlled boundary.** Client files and APIs are source payloads, not direct writes into canonical tables.
