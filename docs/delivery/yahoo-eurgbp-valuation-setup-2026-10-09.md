# EUR/GBP FX valuation setup — 6–7 October 2026

**Status:** Activated locally after explicit owner approval on 2026-10-09  
**Content type:** Delivery report  
**Owner:** Market-data and valuation team  
**Last reviewed:** 2026-10-09

## Findings

The existing Yahoo FX dataset already contains EUR/GBP completed five-minute
samples ending at 16:00 Europe/London:

| Economic date | GBP per EUR | Completed time UTC |
| --- | --- | --- |
| 2026-10-06 | 0.847790002823 | 15:00 |
| 2026-10-07 | 0.846759974957 | 15:00 |

Both are RAW FX_RATE observations, not equity prices or official benchmark
fixings. Daily-bar, US-cutoff and hourly series also exist but are not substituted.
The DEFAULT_EOD versions used in failed attempts have no matching FX rule. Current
personal NON_DISPLAY rights are active, but the dataset and tenant business-date
coverage start October 8. Existing FX calendars are unsealed synthetic weekday
references, not sufficient dated evidence for the new calculator.

## Implemented fix and live effects

`scripts/prepare_yahoo_fx_valuation.py` is local/test-only, dry-run by default,
and calls the governed operator setup in `apps/market_data_ingestor/yahoo_fx_valuation_setup.py`.
One caller-owned transaction performs and verifies the changes:

1. Record today's owner personal declaration, actor and authorization reference
   for use of the existing historical samples. This is not a backdated licence,
   provider consent or commercial clearance.
2. Append a **SCOPED VALUATION entitlement ending October 7**, with a coverage
   package classifying only EUR/GBP UK five-minute samples for October 6–7.
   No USD, other tenant, redistribution or commercial grant is added. Existing
   current grants remain unchanged.
3. Move only the personal FX dataset's business-date metadata start from October 8
   to October 6, preserving its previous value in the declaration. Activity grant
   and licence authorization dates remain today; receipt/source timestamps remain
   unchanged. Other-purpose entitlements are not broadened.
4. Publish a sealed, explicitly two-day **research sample calendar**, sourced to
   the observation IDs. It is not represented as an authoritative exchange holiday
   calendar. Outside coverage remains unknown, not assumed open.
5. Following the owner's subsequent EoD-default approval, create **FLEXIBLE_EOD v1**
   (`Latest available EoD`) with no explicit rules and one LISTING/CLOSE/AS_TRADED
   session-close default. It follows each venue calendar, permits only evidenced
   split conversion, and requires SAME_DAY, zero staleness and FAIL. Then derive
   **FLEXIBLE_EOD v2** with a pinned EUR/GBP EXPLICIT_TIME rule: London 16:00, RAW,
   SAME_DAY, zero staleness, no inverse conversion. Both are tenant-shared immutable
   versions effective October 6. DEFAULT_EOD and all original versions are unchanged.
   Final policy name: `Latest available EoD + EUR/GBP UK research FX`.
   No financial attempt or publication is created.

The original candidate query used one joined entitlement row for both historical
and current dates, incorrectly rejecting separate bounded historical and current
grants. The current-access predicate now uses its own EXISTS query for the same
dataset/series/tenant/purpose. Historical coverage still uses the joined historical
grant; activity rights remain current and conjunctive. Suspending the current
grant still blocks resolution even when historical permission exists.

## Verification

- RED: missing setup implementation, then legitimate bounded grants failed with
  NO_VALID_ENTITLEMENT. Both rates resolve after the candidate-query fix.
- 16 focused setup, personal-valuation permission, FX and resolution-repository
  tests passed in a disposable DB.
- 40 dataset coverage SQL, resolver and rights tests passed in a separate disposable
  DB. Each group reported eight existing SQLAlchemy Result.tuples deprecation
  warnings in seed fixtures, not new failures. No full suite was run.
- Setup regression verifies exact rates/dates, sealed evidence, idempotency,
  unchanged observations and original policy, denied commercial/foreign access,
  finite historical grant and current-access revocation.
- Initial local rollback-only preview selected both real rates through `resolve_fx`.
  The safety reviewer initially blocked activation pending explicit approval.
- Owner subsequently requested "create new policy and activated pending bits".
  A single transaction created the flexible policy and scoped FX setup, verified
  both rates through `resolve_fx`, and committed to the operating DB.
- Active final policy ID: `01a1207b-e65d-7fc0-b19a-7e1ae0987c45`, code
  `FLEXIBLE_EOD`, version **2**, one explicit FX rule and one listed-close default.
- API restarted on port 8000 (launcher PID 4344, serving PID 49364); health returned
  OK. Authenticated live policy-detail GET returned ACTIVE/FLEXIBLE/v2. Two live
  read-only resolution previews returned SELECTED, the exact rates above, matching
  economic dates and no exception. No valuation or snapshot was written by previews.
- The frontend remains running on port 3000 with development reload. Refresh the
  policy/valuation page and select FLEXIBLE_EOD v2; earlier frozen requests are not
  changed or automatically retried.

## Limits and rollback

This fixes FX readiness for the requested two dates only. TTE's equity price-basis
proof remains a separate blocker; successful FX preview is not a successful P&L
run. Other historical periods and currencies need their own reviewed coverage.
The setup refuses missing exact samples or conflicting existing classifications.
It does not fabricate observations or allow stale/fallback FX.

Before activation a recent backup exists from the approved economic P&L migration.
If a configured source becomes unsuitable, suspend the new entitlement/policy and
retain its declaration/calendar history; do not erase provenance or extend an
expired historical grant to bypass the two-date requirement. No commit/push.
