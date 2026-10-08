# Valuation population and Decimal follow-up

Date: 2026-10-07. Scope: two owner-requested changes following implementation review.

## Decisions and implementation

- Remove the historical trade-count cap entirely, including the SQL LIMIT. Continue loading all qualifying strategy trades under the existing economic and information cutoffs. Existing product, evidence, authority, period and query/lock-budget guards remain. This is not a performance/scaling signoff; batching, checkpoints and background execution remain future work.
- Remove the Decimal-to-float-to-Decimal roundtrip from the legacy date-selection path. ObservationCandidate requires a finite Decimal; PriceResolution and database resolution retain that exact value through snapshot storage. Existing LEGACY date, lag, staleness and missing-data rules remain compatible. Removing the precision-loss implementation does not mean deleting existing policies.
- Existing immutable snapshots are not rewritten: previously rounded evidence remains historical evidence. A new resolution can retain full database precision. No schema migration, price rewrite, rights grant, trade mutation, automatic commit or push is involved.

## Verification ledger

Five targeted regression cases failed before implementation for the intended reasons: the 1,000 cap blocked a 1,002-trade population; high-precision database selection lost digits; floats and nonfinite Decimal candidates were accepted. Evidence: logs/valuation-cap-precision-red.log.

Regression coverage checks complete population identity after historical replay, exact Decimal selection and PostgreSQL snapshot persistence, and rejection of binary floats/nonfinite financial candidates. Financial integration tests use disposable databases only.

Lightweight resolver/economics/replay verification: 32 passed in 0.91s. PostgreSQL-backed resolver, valuation service/storage and Soft-NAV consumer verification: 37 passed, 16 existing SQLAlchemy deprecation warnings, 75.86s; runner exit 0 and disposable database cleanup (logs/valuation-cap-precision-green.log).

Full isolated Python regression: 1,173 passed, 493 warnings, 1,732.75s (28:52), logs/valuation-cap-precision-full.log. Warnings include existing SQLAlchemy deprecations and Pydantic field-metadata warnings; this is not a warning-free signoff. The full run covers the new population/precision tests alongside API, snapshot, Soft-NAV and booking regressions. No frontend files changed. Whitespace checks passed for the touched tracked source/test files.

Sequential author review; no independent signoff. Other findings from the preceding market-data/valuation review are outside this narrow change.
