# Data and schema

31 October additive schema: [reviewed manual-mark delivery](../../delivery/incomplete-price-review-20261031.md)
adds two immutable request/decision tables in `nav` through migration 107.
The 29 October inventory below remains a dated baseline, not a fresh table count.


**Status:** Current alpha reference
**Content type:** Architecture index  
**Owner:** Data-platform team  
**Last reviewed:** 2026-10-29

The implementation model, seeds, and schema-hardening record are linked from the [Security Master notebook implementation plan](../../../security-master-notes/16-database-implementation-plan.md), [schema hardening checkpoint](../../architecture/schema-hardening.md), and [mock-up data README](../../../data/mockup/README.md). This index must be updated when schema or seed governance changes.

The [29 October architecture atlas](../../architecture/atlas/README.md) compares
complete runtime metadata with the local database at `20261029_104`: 204 tables,
ten schemas and 611 foreign-key constraints, with no table-set, column-count or
FK source/target-multiplicity difference. The main models import registers 202
tables; `data_imports.tables` adds two more when the API intake workflow loads.
Migrations retain additional immutability/scope/trigger controls, so `create_all()`
alone is not the full deployed schema contract. This inventory does not compare
all column types/defaults/indexes/trigger bodies. Historical bootstrap stamping
was a verified local exception, not a normal upgrade procedure.

Use [safe isolated verification](../../delivery/README.md#safe-postgresql-verification). Never point pytest at operating `platform_secm`; CI and the local wrapper migrate/seed owned test databases. Forward-only/populated-history downgrade guards must not be bypassed. The [public universe](../../delivery/index-universe-seed-2026-10-06.md) is an opt-in maintained seed, not automatically part of every synthetic fixture. Current schema presence does not certify all workflows in the [feature register](../../product/feature-register.md).
