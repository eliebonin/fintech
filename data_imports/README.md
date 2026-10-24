# File intake primitives

External source-specific CSV reconciliation is **not** part of this package.
It is isolated under [optional tooling](../tooling/reconciliation_csv/README.md),
including its operators and tests. Only the supported generic intake primitives
and tenant-facing trade-upload workflow described below belong to the product.

`formats.py` generates tenant-context-bound Excel templates and parses bounded
UTF-8 CSV / values-only XLSX. It does not establish business authority or book
anything. `tables.py` registers private retained import jobs and immutable
source-row identities. Current trade-specific orchestration/authority remains
in `apps/reference_api/import_service.py` and `import_adapters/trades.py`.

First delivered workflow: NEW listing-backed equities, ETFs and funds, one
strategy, 500 rows and 512 KiB per file. Formula/numeric Excel input cells,
macros and external relationships are rejected; use exact text/ISO dates.
Original artifacts are bounded database blobs, accessible through authorised
download handlers only. No automatic expiry/cleanup or external scanning service
is claimed. No asynchronous worker or generic JSON-to-table write API exists.

See [capability and remaining scope](../docs/product/features/tenant-data-imports.md)
and [delivery evidence](../docs/delivery/trade-imports-20261018.md). Focused pure
tests: `python -B -m pytest tests/test_import_formats.py -q -p no:cacheprovider`.
Database tests must use the owned disposable runner, never the operating database.
