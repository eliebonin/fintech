# Structured-product informational notifications

**User-authorised scope:** Informational notifications only. No outcome recording, barrier evaluation, expected payable amounts, financial preparation/booking or valuation effects. Continue sequentially in the current checkout; preserve earlier changes.

## Design
Reuse `/lifecycle` and its source-bound, focus-preserving drawer. Add independent `STRUCTURED_OBSERVATION` strategy manual0/notification1 selection, protected by the existing subscription and scoped read/configure actions. Extend only the retained event CHECK through migration115. No grants, positive defaults or financial handlers.

Use sourced coupon/autocall observations, final valuation and contractual maturity. Related payment dates are conditional source information, not payable tasks. Respect explicit first-autocall eligibility; missing eligibility stays unassessed. All rows have INFORMATION relevance. Dates before/on/after today are upcoming/scheduled-today/date-passed; no overdue, unpaid, triggered or confirmed-outcome inference. Earlier-overdue expansion does not apply; only the requested date window is used. Missing sources can produce quiet information-unavailable rows, never financial blockers or assumed zero holdings.

Cover directly held structured products and structured performance references of held swaps, using current approved dependency-aware terms. Reuse the existing terms/schedules projection below the API through a contract-preserving extraction. Distinguish the held instrument/quantity from the observed structured contract. Check frozen swap performance references against current sources; conflicts make relevance unassessed rather than displaying a new reference as the booked contract. No swap termination is inferred from underlying schedule dates.

Only schedules linked to current condition groups, coupon periods/programmes or component terms are current evidence; historical owner-only schedules are not silently reused. Retired/cancelled child links and actions are excluded. Payment/reset rows are not relabelled as observations. Continuous barriers are shown as terms, not invented daily observations. Current approved schedules applied to historical windows are not historical knowledge snapshots or assessed outcomes.

Use existing immutable ledger/allocation reconstruction: past observations get the known position at the event date (bounded by current knowledge); future dates use current holdings. Preserve shorts, cancellations and separate nonzero allocations at net0. No current/future notice for a flat holding, and no historical notice before holding began. Cache source projections by canonical root within a request; combine/filter/count/page over the full scoped population. Search visible held/observed names and identifiers without widening authority.

Inspection shows event/date/purpose, observed contract, held position context/date, issuer/currency/source version, first-autocall eligibility, related conditional payment date and source-defined conditions/actions. Technical IDs remain collapsed. Values stay decimal strings; thresholds are displayed in their stored basis without a new payoff/percentage conversion. Missing/inaccessible dependencies never leak IDs/names. GET-only inspection rechecks source fingerprint/context and aborts obsolete reads.

## Research already opened/read on 11 November 2026
[Issuer terms filed with SEC](https://www.sec.gov/Archives/edgar/data/70858/000191870425013392/form424b2.htm) distinguish coupon observation/payment, eligible call observation/call payment and final valuation/maturity. The example is product-specific, not a universal formula.
[LSEG autocallables explanation](https://www.lseg.com/en/insights/ftse-russell/autocallables-q-and-a) distinguishes coupon/autocall/maturity barriers and conditional outcomes. No example threshold is hardcoded.
[WAI modal guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) continues to apply through the existing native drawer.

The information-only rollout and independent selection are project choices. Actual fixings, outcome confirmation, suppressed future schedules after confirmed termination, cash/payment matching and financial processing remain follow-up work.
