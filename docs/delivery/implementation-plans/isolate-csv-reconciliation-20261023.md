# Isolate external CSV reconciliation tooling

User-directed boundary: the external CSV import is convenience tooling, not a
product subsystem or official upload contract. Retain useful scripts and tests,
but keep them removable without affecting application startup, valuation or the
supported tenant trade importer. Do not modify existing financial records.

Keep all source-specific modules, local operators and their tests under
`tooling/reconciliation_csv/`. Leaving adapters in `data_imports`/`market_data`
would misrepresent ownership; deleting them would lose reproducibility. Product
tests use native synthetic fixtures instead of CSV preparation helpers.

- [x] Add failing architecture/runtime/CLI boundary tests.
- [x] Move modules/operators/tests mechanically; retain hashes, Decimal handling,
  permissions, idempotency and explicit apply/rollback safeguards.
- [x] Remove CSV dependencies from generic valuation tests. Keep production
  imports and standard test collection independent; exclude tooling from Docker
  contexts/source archives. No new deployment/packaging system is implied.
- [x] Relink documentation and clearly separate test-data exercise from product
  capability evidence. Run focused native and explicitly opted-in tooling tests.

Sequential execution in the existing dirty checkout, preserving unrelated work.
No operating import, migration, restart, permission or valuation publication.
