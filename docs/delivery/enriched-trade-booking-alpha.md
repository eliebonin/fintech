# Enriched listed-cash booking alpha — 2026-09-30

UI update 2026-10-01: [Trade booking property section refresh](trade-booking-properties-ui-alpha.md)
documents required/optional grouping, separate tags and the improved governed
catalogue selector. Existing financial payload and validation rules are unchanged.

Update 2026-10-01: [Governed trade configuration](governed-trade-configuration-alpha.md)
extends this baseline with integer/reference fields, tenant-curated party
eligibility and immutable catalogue versions. The shared-catalogue defaults and
100-item limits and embedded CHOICE provisioning below describe the original
delivery, not the updated controls. Migration 53 replaces active legacy dropdowns
with governed catalogues while preserving historical trade evidence.

## Delivered scope

The menu's **Book trade** page remains the dedicated entry point. Search an
active listing, then enter a sectioned ticket: execution, parties/responsibility,
classification, tenant properties/tags, references/notes, and review/confirm.
This records an already-executed cash trade; it does not route an order.

Counterparty and executing broker are independent optional organisation roles.
Search uses the shared active catalogue, **not** a tenant credit-approved list.
Responsible trader is an active person linked to an active account with effective
membership in the current tenant. The server assigns the authenticated booker
separately. Purpose supports INVESTMENT, REBALANCING, HEDGING and OTHER; OTHER
requires a comment. Market activity is optional PRIMARY/SECONDARY. Trade type
remains INVESTMENT.

Tenant-owned properties support TEXT, DECIMAL, DATE, BOOLEAN and CHOICE.
Requiredness and selected IDs are rechecked at confirmation. False and zero are
real values. Decimals use canonical strings (18 integer/12 fractional digits),
text is bounded to 2,000 characters, and choice values cannot contain surrounding
whitespace. Each tenant has at most 100 active definitions and 100 active tags.
Definitions and assigned annotations are immutable; retirement retains historical
readability. Detail readback includes labels/types, values, tags and named trader.

## Safety and persistence

Migration `20260930_50` adds four annotation tables and database guards for
ownership, active selection, immutable values and immutable catalogue meaning.
The API saves the trade and children atomically inside a savepoint. The browser
sends an expected-tenant consistency header; session-derived tenant and actor
remain the authority. Lookup endpoints are authorised and bounded.

Review/edit preserves the draft. Gross consideration multiplies decimal strings
without binary floating-point rounding. Duplicate confirmation has an immediate
in-flight latch. An uncertain result retains a copied original payload, key and
expected tenant; retries do not silently become a second booking. Known field
rejections return to editing; key/tenant conflicts block confirmation.
Draft navigation is guarded, with stronger restrictions while the result is
unresolved. Browser unload still provides its native warning.

The existing external-reference identity policy is intentionally preserved:
`sourceSystemId + referenceType + referenceValue` is globally unique, not a
tenant-local free-text label. Use an actual source namespace; qualify a
tenant-local namespace explicitly. Without a namespace the value is an annotation,
not a global deduplication identity. Duplicate namespaced references now produce
a safe field rejection, not an HTTP 500/unchanged-retry loop. Sorted advisory
locks serialize API contenders; the unique constraint remains the final guard.
No other tenant's trade identity or details are disclosed.

## Provisioning and running app

Provisioning is intentionally a small authorised CLI, not a configuration editor.
Run from the repository root with an authorised tenant writer:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe scripts/provision_trade_properties.py --tenant <tenant-uuid> --actor <account-uuid> --config docs/examples/trade-properties-demo.json
```

Provisioning is idempotent and rejects changes to existing definition meaning.
The supplied example contains five **optional** fields and two tags. It has been
provisioned for the local Fortem Demo Tenant; no required fields were imposed on
existing bookings. Migration 50 is applied locally. Console: localhost:3000;
reference API: localhost:8000. Open `/trades/new` after selecting the demo tenant.

To replace a definition, retire it with account/timestamp audit and provision a
new version; do not edit its label/type/choices or delete historical values.
A general retirement/settings UI is deferred.

## Verification evidence

- Complete Python suite: **314 passed**, 414 existing SQLAlchemy/Starlette
  deprecation warnings, 334.45 seconds. Includes all five property types,
  BUY/SELL, false/zero, actual other-tenant IDs, named trader vs booker, revoked
  membership, required fields, immutable annotations, duplicate references,
  ordered/canonical replay, and history after definition retirement.
- Frontend suite: **191 passed** across 56 files. Retry snapshot and failure-mode
  tests exercise the helpers used by the live component. Rendered detail tests
  cover false/zero/precision/types and named trader; navigation-handler tests
  cover declined sidebar and browser-back discards.
- TypeScript and production build verified; OpenAPI export check passed.
- Generated TypeScript reproducibility verified by equal SHA-256 hashes before
  and after regeneration. The HEAD-diff generation check is unsuitable here:
  generated files already contain approved uncommitted contract changes.
- Live non-submitting browser exercise: listing search, party search/select,
  sectioned typed fields, review with false/zero/exact `0.02 GBP`, return to edit
  with original values. No financial trade was submitted in the browser.
- Fresh read-only review found choice normalization, source-reference rejection,
  navigation and test-coverage gaps; fixes and realistic regressions were added.

## Research and boundaries

The approved [design](../superpowers/specs/2026-09-30-enriched-trade-booking-design.md)
records source applicability. [Cloudscape single-page creation](https://cloudscape.design/patterns/resource-management/create/single-page-create/)
informed grouping. [WCAG error prevention](https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html)
informed review/edit/confirm; [W3C form notifications](https://www.w3.org/WAI/tutorials/forms/notifications/)
informed error summaries and field feedback. [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
informed per-request object-level checks. These sources do not prescribe the
financial fields, shared-organisation eligibility or typed registry architecture;
those are documented project choices.

Still alpha: T+2 uses Monday–Friday only, not holiday/venue calendars. Fees,
net-settlement calculations, OTC/FX/options/fund-specific booking, arbitrary
property reporting, corrections, durable draft recovery, and valuation/P&L are
outside this increment. The browser draft is not durable across forced closure.
No merge, push, or unrelated dirty-file staging was performed. Implementation
changes remain uncommitted in the approved current checkout on
`codex/enriched-trade-booking`; committing mixed previously dirty files is
deliberately deferred to integration rather than staging unrelated work.
