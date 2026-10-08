# Yahoo daily equities and layered data rights

**Status:** Live adapter verified; owner-approved personal research exception activated; available five-year history imported for all 543 listings (documented source gaps)  
**Owner:** Market-data engineering  
**Reviewed:** 2026-10-07

## Delivered scope

An operator-only local adapter can onboard the 543 seeded S&P 500/CAC 40 listings, verify Yahoo symbols against the exact listing's exchange, currency, timezone and equity type, and import bounded daily history. It reuses existing providers, datasets, mappings, vintages, series and observations. No valuation, P&L, settlement or accounting functionality is introduced.

The 7 October [boundary refactor](market-data-ingestion-boundary.md) places Yahoo code under `market_data/providers/yahoo`, generic publication/storage under `market_data`, and the operator app under `apps/market_data_ingestor`. The script command remains valid. Acquisition/licensing blocks are unchanged. Yahoo remains EoD-only; reference metadata validates mappings, not a complete market-reference ingestion pipeline.

Four additive tables record dataset access profiles, activity grants, layered prerequisites and immutable ingestion deliveries. Requirements are conjunctive: every required agreement must grant the requested activity to the same dataset and licensee within its effective dates. Provider delivery access alone is insufficient. Valid contractual pass-through rights may cover an upstream prerequisite; a separate direct upstream contract is not universally mandatory.

Acquisition/retention evidence is frozen with exact JSON text, SHA-256, receipt time, source payload and publication report. Equal request identities replay safely; changed content under the same key conflicts. Across deliveries, equal points are duplicates and changed points append linked revisions. A database trigger prevents changing or deleting the retained ingestion record. Database-scale normalization precedes duplicate comparison; original source precision remains in the raw delivery.

Inspection enforces actual observation-dataset rights, tenant scope and current accepted revisions, with bounded history pagination. The catalogue endpoint requires the tenant's MARKET_DATA module. The page uses the selected tenant and a rolling two-week window, distinguishes sources and adjustment bases, and provides catalogue/history pagination. Resolver/legacy calculation readers must reject profiled data without NON_DISPLAY rights; this is an access guard, not a valuation implementation.

## Personal scope is not contractual clearance

The owner declared this a local personal project. The profile records PERSONAL_DECLARATION for ACQUIRE, STORE and DISPLAY only, restricted to one simulated tenant. It does not assert Yahoo endorsement, automated-access permission or commercial clearance. COMMERCIAL scope requires CONTRACT evidence. There are no inferred client-reporting, non-display calculation, derived-data or redistribution grants.

Acquisition additionally requires `AUTOMATED_SOURCE_ACCESS`. Ordinary onboarding leaves it unassigned, and a purpose declaration alone cannot satisfy it. On 7 October, the owner explicitly approved a separate PERSONAL_RESEARCH_EXCEPTION for this local Yahoo dataset. Migration 63 and explicit operator activation now record that exception without relabelling it as CONTRACT or provider permission. It is restricted to PERSONAL ACQUIRE, the Yahoo personal dataset and its declared tenant; commercial use remains CONTRACT-only. Onboarding never auto-fills this layer or overwrites a subsequently reviewed assignment. Unresolved or revoked access still returns `RIGHTS_BLOCKED` before a request. See the [five-year backfill record](yahoo-five-year-backfill.md).

The CLI is restricted to local `fortem_secm`, port 54329. Preview rolls back and never contacts Yahoo. Network use requires explicit acknowledgement. HTTP 401/403 stops immediately. HTTP 429 uses the bounded backoff below, then stops the run if it remains rate-limited. No cookie/crumb harvesting, browser impersonation or proxy bypass is used. An access refusal is a source limitation, not a reason to weaken these controls.

Existing synthetic fixtures retain their legacy entitlement model. This does not certify legacy/commercial production datasets: those need a rights review and explicit profiles before commercial activation. A personal declaration must never be relabelled as a signed licence.

## Price and timestamp semantics

- `Close`: SPLIT_ADJUSTED historical close, not a guaranteed unadjusted exchange tape.
- `Adj Close`: VENDOR_ADJUSTED price, separately stored; no implicit substitution, forward fill or repair.
- Prices are not official. Bar timestamps are not invented session-close/publication timestamps.
- Market dates follow the verified venue timezone; receipt time is actual acquisition time, including backfills.
- The current local market day is rejected conservatively because authoritative session completion is not integrated.
- Authoritative calendars, completeness certification, corporate-action ingestion and historical identifier continuity remain separate work. Current-universe verification does not prove continuity across an issuer/venue change.

## Operator workflow

### Personal research source check on 7 October 2026

The owner reaffirmed that the current project is personal research, not production, and explicitly requested a real Yahoo download rather than a mock licence. One diagnostic public daily-chart request was made through `market_data.providers.yahoo.adapter.fetch_chart` for AAPL, covering 7 October 2025 through 6 October 2026. Yahoo immediately returned HTTP 429. Acquisition stopped without automatic retry, authentication/cookie harvesting, browser impersonation or proxy bypass. No response observations or financial records were written.

This diagnostic was owner-directed personal research, not evidence of provider contractual consent. No mock permission was installed, no licence assignment was fabricated and the persisted rights policy was not changed. Consequently, the operator's full ingestion command still has its recorded acquisition prerequisite. The failed public sample confirms a separate current source-access limitation before any wider import or personal-research policy revision. A fresh web-reader attempt to open Yahoo's terms also failed with HTTP 999; no new terms clearance is asserted.

### Bounded rate-limit backoff on 7 October 2026

At the owner's request, the Yahoo adapter now permits three retries for HTTP 429 (four attempts total), waiting 30, 60 and 120 seconds. The operator processes symbols serially, with five seconds between symbols. Retry progress is emitted as `RATE_LIMIT_BACKOFF` with retry number and delay in seconds. Responses are closed before sleeping; no publication transaction is held while waiting.

`Retry-After` is interpreted as nonnegative integer seconds or a timezone-aware HTTP date. The larger of the server delay and exponential delay is used. A server delay above 600 seconds stops the attempt rather than shortening the requested wait. Malformed headers fall back to exponential delay. HTTP 401/403 and other errors are not retried; an exhausted 429 stops the whole run rather than continuing through the universe. No host rotation or background scheduler is introduced. Licensing decisions remain unchanged.

Reference: [RFC 9110, Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3), which defines both delay-seconds and HTTP-date forms. This retry policy supersedes the initial no-429-retry design; earlier source checks above remain historical records.

The subsequent live AAPL diagnostic for 7 October 2025–6 October 2026 exhausted all four attempts, with actual 30/60/120-second waits, and still returned HTTP 429. No database writes occurred. This confirms persistent rate limiting during that probe, not its exact cause or duration. [RFC 6585 section 4](https://www.rfc-editor.org/rfc/rfc6585#section-4) defines 429 but leaves client identification and request counting to the server; shared IP quotas or automated-client filtering remain hypotheses, not proven Yahoo explanations. Wider acquisition was not attempted.

Offline adapter, operator-entrypoint and dependency-boundary verification: 34 tests passed. Tests cover recovery, exhausted retries, both Retry-After forms, malformed and oversized values, and immediate stop on non-429 errors. The full isolated Python run passed 1,017 tests with 487 warnings in 752.06 seconds (log: `logs/yahoo-backoff-full-python.log`). That run collected before two additional extreme-header cases were added; the final 34-test focused run covers those cases and the final adapter code. Compilation and whitespace checks passed. No frontend changes were made or frontend suite results claimed for this patch.

### Explicit request headers verified on 7 October 2026

The owner successfully queried Yahoo from their own Python instance using `User-Agent: PersonalPriceResearch/1.0` and `Accept: application/json`, whereas the earlier ingestor used HTTPX's default headers. A live probe through the actual adapter with these explicit headers succeeded. The adapter now supplies them on every request, including retries, rather than relying on the caller's client configuration. HTTPX continues to manage compression and connection headers. This is an honest project identifier, not browser impersonation; no cookies, authentication harvesting, proxies or host rotation were introduced.

An ordinary default HTTPX client using the final adapter fetched and identity-validated the original one-year AAPL window (7 October 2025–6 October 2026): 251 bars, 502 accepted price points, zero rejected points. The initial 30-day probe returned 21 bars and 42 accepted points. Five-second-spaced European probes also succeeded: AIR.PA and MT.AS each returned 255 bars, 508 accepted points and two rejected points. For both European symbols, CLOSE and ADJ_CLOSE on 6 October 2026 were missing/malformed and remained rejected. Successful retrieval does not establish whole-universe completeness or certify the latest EoD bar.

These were read-only source/parser checks, not database ingestion. No Yahoo observations were published and no proposed mappings promoted. The acquisition licence prerequisite, serial pacing, exponential retries, size limits, identity checks and rejection rules remain unchanged. The tests establish that the configured headers reach the request and the response can be parsed; they do not prove Yahoo's internal reason for rejecting the earlier header configuration. Offline adapter, CLI and dependency-boundary checks passed 35 tests. The full isolated Python suite passed 1,020 tests with 489 warnings in 750.98 seconds; log: `logs/yahoo-personal-headers-full-python.log`. Compilation and whitespace checks passed. No frontend code changed.

### Existing ingestion commands

Run from the repository root:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe scripts/ingest_yahoo_market_data.py --declaration "Owner-declared local personal project" --symbols AAPL AIR.PA MT.AS --limit 3
.venv/Scripts/python.exe scripts/ingest_yahoo_market_data.py --apply --initialize-only --declaration "Owner-declared local personal project"
.venv/Scripts/python.exe scripts/ingest_yahoo_market_data.py --apply --acknowledge-personal-access --declaration "Owner-declared local personal project" --symbols AAPL AIR.PA MT.AS --limit 3
```

The first ingestion command is rollback preview. Before the explicit 7 October exception, the final acquisition command returned RIGHTS_BLOCKED. It may now acquire under the recorded personal research exception, while retaining all STORE/DISPLAY and tenant requirements. Neither `--apply` nor acknowledgement creates an exception: explicit `--personal-research-exception` activation and an attributable approval reference are required. Contractual provider permission, when available, remains a separate evidence path. There is no public rights-administration API or automatic licence acquisition.

Widen to `--limit 543` only after rights and a real sample validate. Default history is 14 calendar days ending yesterday. Explicit symbols must belong to the seed. Each delivery commits atomically. Failed HTTP acquisition is reported to the operator, not manufactured as a successful stored delivery.

## Best-practice review and decisions

Reviewed on 6 October 2026:

| Evidence | Applied decision |
| --- | --- |
| [Yahoo UK-applicable terms](https://legal.yahoo.com/ie/en/yahoo/terms/otos/index.html), updated 8 July 2026; sections 2(d)(ix), 2(e), 2(h), 2(i) | Personal purpose and software/API use do not establish automated-collection permission. Require a distinct access prerequisite, without inventing provider consent. The browser confirmed the current terms after the web reader returned 999. |
| [yfinance maintainer guidance](https://github.com/ranaroussi/yfinance) | Software licensing is distinct from data-use rights; no Yahoo endorsement. |
| [Download documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) and [parsing/adjustment source](https://github.com/ranaroussi/yfinance/blob/main/yfinance/utils.py) | Preserve Close and Adj Close separately, without silent auto-adjustment. A minimal direct HTTP adapter is a project choice. |
| [Yahoo adjusted-close guidance](https://in.help.yahoo.com/kb/adjusted-close-sln28256.html) | Identify dividend/split adjustments; do not claim an official raw-price tape. |
| [Euronext agreement types](https://www.euronext.com/en/data/pricing-specs-agreements/data-agreements-types) | Layered delivery/subscriber/non-display prerequisites depend on contract, activity and delay. |
| [AWS idempotent API guidance](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | Commit request identity and effects together. PostgreSQL implementation and immutable evidence are project choices. |

The reviewed plan is proportionate: a small adapter and operator command with rights prerequisites, not a universal licensing rules engine, commercial feed service or valuation module.

## Verification and activation ledger

Revision `20261006_62` is installed locally. Rollback preview passed without network access, followed by personal configuration activation: 543 proposed mappings, restricted personal ACQUIRE/STORE/DISPLAY grants and a missing MARKET_DATA module grant. An existing denied/expired module grant is never overwritten; activation requires the tenant administrator.

The real three-symbol smoke request (`AAPL`, `AIR.PA`, `MT.AS`) stopped immediately when AAPL returned HTTP 429. The other symbols were not attempted. No retry/bypass or full-universe download was performed. There are **zero real Yahoo observations**, zero retained Yahoo price deliveries and 543 mappings still PROPOSED. Do not confuse existing synthetic Yahoo-labelled fixtures with this new provider. Successful live source identity validation and broader coverage remain unverified.

Final best-practice review tightened the earlier declaration-only acquisition gate: the current Yahoo terms were reread, an unresolved AUTOMATED_SOURCE_ACCESS requirement was added locally, and another operator invocation returned RIGHTS_BLOCKED before network access. The earlier 429 is retained as observed evidence; it does not establish a temporary-only limitation or permission to retry automatically. Resolving commercial rights later is still separate from resolving automated access now.

Financial baseline is unchanged: 9 trades, 9 lifecycle events, 12,469 existing synthetic observations and zero cash balances. The local API/frontend are running on ports 8000/3000. Browser acceptance confirmed selected-tenant navigation, rolling default dates, an honest empty recent window and historical synthetic inspection with 24 series paginated 12 per page. It caught a pre-existing literal entity in the heading, fixed with a rendering regression.

Verification: 84 targeted Python tests passed before final hardening; 28 integrity/API/workspace regressions, 3 onboarding tests and 55 source/rights/inspection regressions passed subsequently. The **full isolated Python suite passed: 998 tests, 489 warnings, 25m49s**. It began before final access-layer hardening; a **fresh final 58-test Python run passed** against those final changes, including three cases added after full-suite collection. All **584 frontend tests** and TypeScript passed after the heading and module-restriction fixes, with two workers and a 30-second test budget after initial import timeouts. OpenAPI export check passed and repeated TypeScript generation is byte-for-byte stable. The project's generate:check compares with Git HEAD, so it reports intentionally uncommitted contract changes rather than generator drift. Whitespace diff check passed. Deprecation/header-metadata warnings remain a separate cleanup item; passing does not mean warning-free.

Commands providing the final evidence:

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py -q --tb=short
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_market_data_rights.py tests/test_yahoo_market_data_onboarding.py tests/test_yahoo_market_data_cli.py tests/test_market_data_ingestion.py tests/test_market_data_display_rights.py tests/test_yahoo_market_data.py tests/test_mvp_market_data_api.py -q --tb=short
pnpm --filter ops-console exec vitest run --maxWorkers=2 --testTimeout=30000
pnpm --filter ops-console typecheck
.venv/Scripts/python.exe scripts/export_openapi_contract.py --check
git diff --check
```

No commits, merge or push were performed; the current feature checkout and unrelated existing changes are preserved. Local servers remain on 8000/3000. The remaining source sign-off requires actual automated-access evidence, a successful permitted real-data sample and subsequent wider-universe coverage verification. Valuation/P&L, authoritative session calendars and commercial licensing remain deferred.

Browser acceptance also verified ACCESS RESTRICTED and administrator guidance for the second tenant without MARKET_DATA, without querying prices from that screen. The personal-project tenant was restored afterward. No financial or approval actions were performed in the browser.

Review was performed sequentially by the implementing agent, following the user's no-subagent instruction. It is not independent reviewer sign-off or commercial deployment approval.

See the [design](../superpowers/specs/2026-10-06-yahoo-market-data.md) and [execution plan](../superpowers/plans/2026-10-06-yahoo-market-data.md).

Subsequent operational changes are recorded in [ingestion hardening](md-ingestion-hardening.md): PARTIAL exits with code 3, jobs/attempts retain execution evidence, --retry-gaps targets explicit missing prices, and --audit-only performs read-only calendar/continuity reconciliation. The earlier verification above is dated evidence, not verification of this later extension.
