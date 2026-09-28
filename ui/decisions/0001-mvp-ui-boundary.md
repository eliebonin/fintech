# Decision 0001: MVP UI boundary

## Decision

Create a separate `ui/` specification workspace before selecting a frontend
stack or writing application code. The first UI slice is an operations and
review workspace around canonical reference data, external-ID mapping,
market-data evidence, trade lifecycle, and Soft-NAV review.

## Why

These workflows exercise the platform's most important controls: tenant
isolation, UUID identity, effective-dated canonical records, source lineage,
append-only corrections, and reproducible valuation inputs. Starting with a
dashboard or a generic CRUD screen would hide those constraints and create
unstable API assumptions.

## Choices resolved by follow-up decisions

- Next.js App Router and pnpm workspace foundation (see Decisions 0002 and
  0003).
- MUI 9 as the initial design system (see Decision 0002).
- One operations console as the first deployable app.

## Still deferred

- client-side state/cache library;
- generated API-client packaging and OpenAPI publication;
- browser-based entitlement enforcement versus API-only enforcement; and
- production deployment topology and separate tenant/steward applications.

These choices should follow the approved screen and data-contract specs.
