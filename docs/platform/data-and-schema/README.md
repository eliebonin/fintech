# Data and schema

**Status:** Current alpha reference
**Content type:** Architecture index  
**Owner:** Data-platform team  
**Last reviewed:** 2026-10-12

The implementation model, seeds, and schema-hardening record are linked from the [Security Master notebook implementation plan](../../../security-master-notes/16-database-implementation-plan.md), [schema hardening checkpoint](../../architecture/schema-hardening.md), and [mock-up data README](../../../data/mockup/README.md). This index must be updated when schema or seed governance changes.

Reviewed code baseline has Alembic through revision 83. The shared SQLAlchemy metadata registers separate valuation and access tables; migrations retain additional immutability/scope/trigger controls, so `create_all()` alone is not the full deployed schema contract. Historical bootstrap stamping was a verified local exception, not a normal upgrade procedure.

Use [safe isolated verification](../../delivery/README.md#safe-postgresql-verification). Never point pytest at operating `fortem_secm`; CI and the local wrapper migrate/seed owned test databases. Forward-only/populated-history downgrade guards must not be bypassed. The [public universe](../../delivery/index-universe-seed-2026-10-06.md) is an opt-in maintained seed, not automatically part of every synthetic fixture. Current schema presence does not certify all workflows in the [feature register](../../product/feature-register.md).
