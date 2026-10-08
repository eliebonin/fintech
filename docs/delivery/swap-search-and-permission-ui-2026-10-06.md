# Swap identifier search and permission-aware UI

**Date:** 2026-10-06. **Status:** Implementation and isolated regression/browser verification complete.

## Scope and approach

Two bounded follow-ups from [trade-side acceptance](trade-side-acceptance-2026-10-06.md): find swaps using their tenant confirmation identifiers, and make instrument/trade write affordances reflect current tenant permissions. Sequential implementation, lightweight failed-first tests, then broader regressions. No new permissions, authentication model, identifier migration/backfill, settlement, accounting or valuation work.

The prior acceptance research remains applicable: [OWASP authorization regression testing](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Regression_Testing_Cheat_Sheet.html) for actor/resource/action boundaries and [Playwright best practices](https://playwright.dev/docs/best-practices) for user-visible isolated outcomes. These sources were reviewed on 2026-10-06 during acceptance; this follow-up uses that documented guidance rather than claiming new financial standards. UI visibility is not security enforcement: every API write remains independently authorized.

## Swap identifier lookup

- Root cause: `tenantIdentifier` is persisted in approved swap economics JSON, not in the shared scheme-based general identifier table. Booking search checked canonical name, internal code, general identifiers and listing symbols, missing this authoritative field.
- Booking search and instrument catalogue now also search the current APPROVED swap definition's `tenantIdentifier`, case-insensitively, with partial matches and literal `%`, `_` and backslash handling for this alias. Existing name/code/general-identifier search remains unchanged.
- A correlated EXISTS predicate avoids multiplying matches or changing pagination. Existing outer tenant visibility remains mandatory. Noncurrent or unapproved swap terms are not aliases; a pending proposal is not a bookable reference.
- No duplicate identifier store or guessed ISIN is introduced. Identical tenant labels need not become globally unique. Existing contracts work without rewriting economics, approvals or booked snapshots.
- UTC search dates, readiness revalidation and execution-date restrictions are unchanged. This does not add historical reconstruction of retired definition aliases.

## Permission-aware UI

| Action | Required membership/module |
| --- | --- |
| Create/configure instruments, families, listings and booking conventions | TENANT_ADMIN + SECURITY_MASTER |
| Book trades | TENANT_ADMIN + TRADING |
| Existing inspection/history | Unchanged API read authority; not made admin-only |

- Sidebar booking navigation, history booking/first-booking links, catalogue/request creation buttons and detail listing/convention write actions are hidden from unqualified users. Server-resolved workspace permissions drive catalogue/detail affordances; the shared shell uses explicit verified context or its selected-session lookup.
- Direct instrument-create/configuration and booking URLs show the required role/module, advice to contact the tenant administrator, and read-only/change-tenant exits. Existing server-gated option/future/family/swap/convention/booking routes no longer silently redirect denied users to another page. Missing sessions still go to tenant selection.
- While workspace permissions are unknown or unavailable, legacy write forms remain hidden with an explanation and retry/tenant-selection guidance. Failed lookup never grants demo permissions. This client presentation guard does not replace server/API authorization and is not a claim that legacy pages avoid all read-only catalogue requests.
- Browser BFF401/403 messages now explain session selection or tenant-role/module denial. Status, machine code, correlation ID and field errors are retained; those denials are never marked retryable. Other validation/conflict/service messages remain actionable rather than being replaced by permission prose. Existing blocked/uncertain booking handling is unchanged.
- This covers instrument management and booking affordances, not a general redesign of every strategy, market-data or trade-configuration screen.

## Verification ledger

- Initial lightweight UI checks reproduced visible unauthorized actions/forms and opaque errors. Subsequent server-page cases reproduced silent redirects. After the fixes: **32 focused permission checks passed**.
- Initial search regressions reproduced empty identifier lookup. One historical fixture attempted to update immutable approved definitions; corrected it to append a noncurrent version with a nonoverlapping effective period. The catalogue test URL was also corrected to the existing `/v1/instruments/search` endpoint. Neither fixture mistake was treated as a product defect or bypassed with disabled database protections.
- Search plus existing generic swap booking: **56 passed**,67.55s, exit0, in a newly generated disposable database.
- Full frontend: **579 passed in119 files**,27.12s, exit0. TypeScript exit0.
- Browser PASS: lowercase `accept_swap_261006` returns exactly one Ready-to-book swap, `Acceptance Funded Swap 20261006`, in the booking UI. Catalogue query `ACCEPT_SWAP_261006` also returns exactly that canonical reference. Existing contract `01a1119b-9be0-7671-8015-f6ecc93f1b0e` was used; no new trade or reference was created.
- Browser PASS: Second Tenant/OPERATIONS directly opening bond creation first sees no form while permissions load, then the explicit TENANT_ADMIN + SECURITY_MASTER requirement and administrator/read-only/change-tenant guidance. Direct booking shows the analogous TENANT_ADMIN + TRADING requirement, not a silent redirect. Default and All history remain inspectable with0 records and no booking/first-booking link. Catalogue and Requests show no Create instrument action; visible global bond detail shows facts without Add listing or convention-configuration actions.
- Full isolated Python suite: **934 passed**, 490 warnings, 665.14s (11:05), exit 0. Warnings concern deprecated Starlette status naming, SQLAlchemy `Result.tuples()` and Pydantic field-attribute metadata; no failures were reported. The disposable test database is separate from operating data.
- Verification commands: `.venv/Scripts/python.exe scripts/run_isolated_python_tests.py -q --tb=short`; full frontend Vitest suite; `node node_modules/typescript/bin/tsc --noEmit --incremental false -p tsconfig.json` from `apps/ops-console`. Final whitespace/diff check passed.
- Sequential author review checked shared-predicate tenant scoping, current/approved definition filtering, read-only inspection preservation, unknown-context refusal, direct-page denial and API authority. No independent/subagent review or production signoff is claimed. Browser context was restored to Demo Tenant/TENANT_ADMIN for the walkthrough.

## Activation and limits

Only the isolated UI3007/API8007 preview was activated against `fortem_fx_signoff_722336f2caf94ffca0fd6f9ca3f08701`. Operating data/builds were not restarted or changed. No commits, GitHub push or production deployment. The previously documented contractual-lifecycle/settlement/accounting/valuation deferrals remain in force.
