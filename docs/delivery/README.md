# Delivery records

**Status:** Accepted  
**Content type:** Delivery index  
**Owner:** Engineering delivery team  
**Last reviewed:** 2026-10-02

Use [specifications](specifications/README.md) for approved design intent, [implementation plans](implementation-plans/README.md) for execution sequences, and [quality reviews](quality-reviews/README.md) for dated evidence. None is automatically current architecture without a link from a canonical page.
# Delivery documentation

- [API error responses](api-problems.md)
- [API contract delivery and dependency policy](api-contracts.md)
- [Tenant workspace and strategy alpha](tenant-workspace-strategy-alpha.md)
- [Enriched trade booking alpha](enriched-trade-booking-alpha.md)
- [Deliverable FX-forward booking alpha](fx-forward-booking-alpha.md)
- [Listed option booking alpha](listed-option-booking-alpha.md)
- [Structured security and futures booking alpha](structured-security-and-futures-booking-alpha.md)
- [Futures creation and contract conventions alpha — delivered scope, local seed, multiplier semantics and remaining gaps](futures-creation-and-contract-conventions-alpha.md)
- [Bond booking alpha](bond-booking-alpha.md)
- [Listed option booking quality review](quality-reviews/2026-10-01-option-booking-alpha.md)
- [Agreed booking and lifecycle scope and next option slice](booking-and-lifecycle-scope.md)
- [FX-forward booking quality review and alpha acceptance](quality-reviews/2026-10-01-fx-forward-booking-alpha.md)
- [Trade booking property section refresh](trade-booking-properties-ui-alpha.md)
- [Browser trade-configuration cycle acceptance](quality-reviews/2026-10-01-browser-trade-configuration-cycle.md)
- [Trade booking browser fixes, reusable regression and density findings](quality-reviews/2026-10-01-trade-booking-browser-follow-up.md)
- [Trade history alpha](trade-history-alpha.md)
- [Governed trade configuration and legacy cleanup](governed-trade-configuration-alpha.md)
- [Trade configuration UI refresh and acceptance checklist](trade-configuration-ui-alpha.md)

## PostgreSQL quality-check contract

PostgreSQL-backed migrations and integration tests are mandatory quality checks locally and in GitHub Actions. Both environments use the sole `DATABASE_URL` setting, conventionally `postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm`.

To check the migration boundary against a running local service, run:

```powershell
$env:DATABASE_URL='postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm'
.venv\Scripts\python.exe -m pytest tests/test_migrations.py -v
```
