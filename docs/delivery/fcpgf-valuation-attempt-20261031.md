# FCPGF daily valuation attempt — 31 October 2026

**Status:** Attempt retained as FAILED / VALUATION_BLOCKED; missing source marks  
**Scope:** Owner-requested local reconciliation, not publication or financial sign-off

## Request and configuration

The owner requested FCPGF for **20 October 2026** using the configuration from
the successful FCAGF run. The retained FCAGF request used GBP reporting, daily
19→20 October cutoffs, strict same-day RAW imported prices/FX and optional complete
accrual coverage. FCPGF now has the equivalent strategy-specific policy against
its own retained datasets; FCAGF's policy and historical results are unchanged.
Information availability is frozen at this new submission time so the later
FCPGF imports are eligible. No predecessor from a different strategy is reused.

Fund holdings additionally need a NAV_DATE rule. A rollback rehearsal caught the
native requirement for a sealed tenant VALUATION calendar, rather than a platform
reference calendar. The optional reconciliation helper now publishes that
calendar through the existing authorized service and pins it only to the NAV
rule. It derives explicit source-date buckets from the shared UTC partition over
the supplied observation interval. Its name and source reference explicitly
disclaim contractual fund holidays, dealing eligibility and publication timing;
same-day freshness remains strict. Other product rules retain the FCAGF-style
reference calendar and end-of-day cut.

Existing guarded setup records the owner's personal-file valuation instruction
and the tenant's scoped dataset coverage. It adds eight identity-normalized
FX_FORWARD series from retained FORWARD_RATE observations with exact currencies,
maturity and lineage. Original observations, execution prices, quantities,
rights evidence and price dates are preserved. This is not commercial clearance,
spot substitution or a relaxed product validator. All source-specific work stays
under optional tooling and ignored private evidence.

## Attempt and input diagnosis

The request went through the normal authenticated local API and retained its
operator/selected-user identities. The attempt failed during input selection in
about **16 seconds**, with `Forward contract-rate input blocked:
NO_ELIGIBLE_OBSERVATION`. No financial batch was staged or published.

A separate native mark preflight used a repeatable-read snapshot and was rolled
back. It assessed **125 position buckets / 250 opening-and-closing mark requests**:
**248 selected**, with **two missing 19 October EUR/GBP contract-forward marks**.
The original CSV has only 20 October observations for these two contracts.
Both trades were booked on 19 October; an execution rate is not that day's EoD
mark. Spot rates, another contract's mark, a prior date, zero or execution cost
were not fabricated as substitutes. Their exact identities and supplied values
remain in private evidence rather than this maintained product documentation.

This preflight covers position marks, not a completed downstream FX, cash,
accrued-stock, staging or publication acceptance. After the two missing contract
marks are supplied and retained through normal ingestion, a **new attempt key and
new information cutoff** are required. The failed request remains immutable.

## Verification and retained evidence

- One lightweight policy regression passed, pinning the dedicated NAV calendar
  without changing the other product rules.
- Four owned-disposable eligibility tests passed, including native calendar/
  policy activation, unchanged source observations, replay and forward lineage.
- The setup rehearsal rolled back, then activation committed successfully.
  The temporary local API session was ended after the attempted calculation.
- No migration, product runtime import of reconciliation tooling, trade mutation,
  source-price rewrite, publication or full-suite run was needed.

Ignored private evidence beside the retained bundle includes
`valuation-config-20261031.json`, `valuation-request-20261031.json`,
`valuation-response-20261031.json`, `valuation-failure-detail-20261031.json` and
`valuation-input-check-20261031.json`. Request/response files contain no session
token or operator credential. See the [import record](fcpgf-reconciliation-import-20261030.md)
for posting completeness and separately disclosed contractual assumptions.

## Subsequent partial-review activation — 31 October

The later [incomplete-price delivery](incomplete-price-review-20261031.md)
adds a new v2 WARN policy and a fresh calculation. FCPGF now completes into
staging with 123 priced / two unpriced investment positions and one cash scope
missing SGD/GBP rates. Four required observations still block publication;
unknown contributions are unavailable and displayed amounts are calculated
subtotals. The initial failed requests described above are unchanged. See the
linked delivery for exact achieved scope and verification, not a full financial
or publication sign-off.

## Fund NAV-date correction — 31 October

The [fund NAV follow-up](fund-nav-lag-20261031.md) creates pricing policy v3 and
valuation-calendar v2. All ten fund positions now use 19/16 October NAVs with
20/19 October FX. The new run stages a 56,247.558719743611 GBP net calculated
subtotal; four required marks, accrued-stock evidence, inactive imported sales
and additional production positions remain separate findings. Other instrument
components and cash FX are unchanged; no valuation was published.
