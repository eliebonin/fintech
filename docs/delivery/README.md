# Delivery records

**Status:** Accepted  
**Content type:** Delivery index  
**Owner:** Engineering delivery team  
**Last reviewed:** 2026-09-10

Use [specifications](specifications/README.md) for approved design intent, [implementation plans](implementation-plans/README.md) for execution sequences, and [quality reviews](quality-reviews/README.md) for dated evidence. None is automatically current architecture without a link from a canonical page.
# Delivery documentation

- [API error responses](api-problems.md)
- [API contract delivery and dependency policy](api-contracts.md)
- [Tenant workspace and strategy alpha](tenant-workspace-strategy-alpha.md)

## PostgreSQL quality-check contract

PostgreSQL-backed migrations and integration tests are mandatory quality checks locally and in GitHub Actions. Both environments use the sole `DATABASE_URL` setting, conventionally `postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm`.

To check the migration boundary against a running local service, run:

```powershell
$env:DATABASE_URL='postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm'
.venv\Scripts\python.exe -m pytest tests/test_migrations.py -v
```
