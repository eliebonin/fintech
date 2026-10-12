# Execution ledger — daily valuation recognition

Plan: docs/superpowers/plans/2026-10-08-daily-valuation-recognition.md
Spec: docs/superpowers/specs/2026-10-08-daily-valuation-recognition.md

- User approved implementation. Ruling: continue existing feature checkout; preserve unrelated frontend recovery and revision 71 work. Sequential author review and scoped tests replace subagents/full-suite runs as requested. No automatic commit/push or operating migration.
- Ruling: explicitly UTC business-date convention for this alpha; do not introduce unconfigured strategy timezone assumptions. Cost: non-UTC business-date policies remain a future extension.
- Pre-flight: booking fields -> immutable BOOKED metadata/indexed columns -> projection recognition -> daily valuation request/evidence -> UI. All layers must preserve actual execution separately; market policy is not a trade-recognition clock.

## Implemented

- Platform-wide optional `valuationEffectiveDate` and `valuationOverrideReason` on cash, FX forward, option and product bookings. These are ordinary built-in booking fields, not tenant property definitions. Blank dates resolve to the UTC execution date; later dates require a reason and earlier dates are rejected.
- New bookings freeze recognition in original BOOKED evidence and indexed trade columns. Legacy rows remain untouched and resolve through `LEGACY_UTC_TRADE_DATE`. Trade responses, all booking review screens and trade detail display the date. In-place changes are rejected by revision 72; cancel/rebook records preserve the original evidence.
- Daily position selection uses recognition dates for both quantity and signed execution contributions. Original execution chronology still drives corporate-action safety and reference-definition checks. Late recording remains governed by the information cutoff.
- Daily P&L uses `openingDate`/`closingDate` inputs. The position clock resolves to UTC end-of-day; market targets still come from pricing policies. Timestamp API requests remain supported. Rejected request validation is editable; uncertain failures keep the frozen request and information cutoff.
- Generated OpenAPI and TypeScript contracts updated. Omitted new fields preserve existing booking retry identities; timestamp valuation retry keys also remain compatible.

## Verification, 2026-10-08

Lightweight tests ran first. Recognition defaults/validation, projection/date contracts and retry-identity tests had observed RED failures followed by GREEN. Additional storage, API and adapter checks were green-only integration regressions, not claimed as red/green.

- Pure Python focused bundle: **44 passed**, including date ordering, default UTC midnight crossing, deferred quantities/execution P&L, round trips, cancellation, late recording, corporate-action exposure and retry compatibility.
- Isolated backend bundle: **191 passed** (storage, position repository, valuation service, corrections, bonds, options, FX forwards and generic swaps). Additive revisions 71/72 upgraded successfully in the disposable database. After retry compatibility and API additions, final isolated storage/API bundle: **12 passed**, including actual booking default/cancel-rebook evidence and date transport/frozen attempt payloads.
- Focused frontend bundle: **58 passed across eight files**, covering the common field helper, date request/errors, valuation console, booking review and cash/FX/option/product adapters.
- `pnpm --filter ops-console typecheck`: passed. OpenAPI export `--check`: passed. `git diff --check`: passed (line-ending warnings only).
- No full suite, browser acceptance, production build, migration downgrade test, operating financial writes, commit or push was performed for this task. Author review covered frozen evidence/row consistency, recognition versus execution chronology, shared ticket paths, date/request exclusivity and compatibility of old retry keys.

## Activation and limits

**Operating activation completed on explicit user request, 2026-10-08:** verified the operating database was at revision 71, then applied revision `20261008_72` and confirmed it is head. Restarted the API on 8000, rebuilt the production console successfully, and restarted it on 3000. Live read-only checks returned HTTP 200 for API health and tenant selection; trade reads succeeded and exposed `valuationEffectiveDate`. No trades or valuation results were created during activation. Original `next-env.d.ts` content was restored after build generation. The process-only signed-session key rotated, so existing browser sessions may require tenant selection again.

The UTC convention is explicit alpha behavior, not an assertion that every fund uses UTC business dates. A future governed strategy-timezone configuration may replace it. Current-day runs require the completed UTC closing boundary to be within the information cutoff; use a completed date. No holiday auto-roll, derivatives valuation, accounting, settlement processing or corporate-action replay was added. Recognition changes do not eliminate real market exposure and do not bypass existing valuation blockers.

Design and research references: [approved recognition specification](../superpowers/specs/2026-10-08-daily-valuation-recognition.md). The recognition field is a project governance design, not a mandated accounting standard.
