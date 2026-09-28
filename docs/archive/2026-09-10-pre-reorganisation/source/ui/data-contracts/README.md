# UI data contracts

UI data contracts are stable, view-oriented API contracts. They should not
mirror PostgreSQL tables blindly.

Every contract should identify:

- tenant context and authorization requirements;
- Fortem UUIDs and object types;
- effective version/status and display label;
- source/provider/dataset/licence lineage where relevant;
- market date, valuation cut, and information cutoff for values;
- mutation idempotency key and lifecycle semantics; and
- structured error codes for missing, stale, ambiguous, unauthorized, or
  pending data.

The first contract is documented in
[`instrument-search.md`](instrument-search.md). Subsequent contracts should
cover mapping review, trade booking/detail, and Soft-NAV run review. Generated
TypeScript clients and consumer-driven contract tests will be added once the
Python API shapes are approved.

In the repository, these generated contracts belong in the private
`api-contracts` workspace package. They are consumed by applications
through its public exports; no app imports backend implementation modules.
