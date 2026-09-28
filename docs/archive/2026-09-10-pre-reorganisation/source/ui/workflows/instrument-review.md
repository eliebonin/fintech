# Workflow: search, reconcile, and inspect an instrument

1. The operations analyst opens the server-rendered workspace in the
   authenticated tenant context.
2. The analyst searches by a canonical name, ISIN/FIGI, listing symbol/MIC, or
   a bank/custodian/client alias.
3. The BFF returns a view model. The analyst confirms whether the match is an
   economic instrument or a venue listing and sees the mapping namespace/status.
4. The analyst reviews effective definition version, identifiers, listings,
   quote/unit factors, and the market-data evidence row.
5. The analyst follows the deep link when a record needs a second-person review.

The current slice is read-only. Propose/approve mapping and canonical-record
mutations remain server-authoritative workflows and must carry actor, reason,
idempotency key, effective date, and prior version/event references.
