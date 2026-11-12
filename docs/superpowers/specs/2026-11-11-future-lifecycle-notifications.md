# Futures lifecycle notifications and inspection

**Approved direction:** User requested the next read-only futures milestone slice after bond/FX maturity and coupon notices. Existing current checkout and sequential execution remain authorised; preserve unrelated work.

## Scope and approach
Extend the existing `/lifecycle` worklist, full-population filters and modal drawer. Use an independent strategy `FUTURE_EXPIRY` selection (manual0 or notifications1) under the current commercial ceiling. No new permissions, automatic grants, financial handlers, trades, cash, delivery, valuation or operating strategy configuration.

Separate source milestones: exact approved last-trading instant; explicitly stored expiry date; final settlement date; physical delivery start/end. Dates on the same day remain distinguishable. Do not infer expiry from contract month, delivery from expiry, settlement completion from a date, or exchange dates from a generic calendar. First notice is not stored in current conventions and remains an explicit inspection limitation, not a fabricated date/event. A future governed first-notice extension is separate work.

Alternatives considered: a separate futures dashboard duplicates access/navigation; sharing bond visibility misrepresents the requested per-type choices. Reusing the general dashboard with an explicit futures selection preserves existing boundaries. Notifications1 is the only positive supported futures tier; no hidden preparation authority is created. Downgrade preview retains or explicitly replaces choices and respects the supported event ceiling.

## Read model and UX
Query authorised tenant/strategy candidates before counts/page selection; resolve listings to canonical expiry and reconstruct current signed contracts using existing immutable ledger and joint allocation rules. Opposing allocations at aggregate zero remain visible; flat positions disappear without claiming settlement. Missing evidence is blocked/unknown, never zero. Preserve short positions. Approved-source changes and mismatched frozen booking terms are disclosed.

Futures event rows show milestone label/date (exact cutoff in inspection), signed contract quantity and cash/physical settlement. Due/overdue means an open ledger position needs review, not an unpaid obligation. Earlier-overdue expansion applies only to open dated milestones. GET-only lazy inspection rechecks current scope/source/event identity and aborts obsolete requests. Native modal preserves focus, mobile layout and filters. No financial console mounts for a future.

## Data and assurance
Migration113 extends only the retained strategy-assistance event constraint; no existing rows are rewritten. Futures selection remains explicit/default0. Existing approved convention payload and common instrument dates are read without mutation.

Focused tests: exact cutoff boundaries, missing dates, cash/physical, net/short/zero allocations, cancellation and canonical/listing identity, tenant/strategy isolation, literal identifier search, filter/count/pagination ordering, read-only route, new selection and downgrade behavior, modal context/focus/mobile and stale-source responses. Use disposable databases and synthetic data only. No broad regression suite unless failures justify it.

## Research (reviewed 11 November 2026)
- [CME expiration and settlement](https://www.cmegroup.com/education/courses/introduction-to-futures/get-to-know-futures-expiration-and-settlement): cash and physical delivery are distinct contract outcomes. Applies to the separation of notices from financial effects.
- [ICE WTI expiry calendar](https://www.ice.com/products/213/WTI-Crude-Futures/expiry): lists last trade, first/last notice, first/last delivery and final settlement separately. Product-specific example, not a universal date formula.
- [CFTC futures glossary](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CFTCGlossary/index.htm): first notice can vary by commodity/exchange; do not infer it from delivery start.
- [WAI modal-dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/): contained focus, Escape and focus restoration support reuse of the existing native drawer.

These sources establish terminology and interaction guidance; independent notifications-only selection and this rollout boundary are project choices, not regulatory requirements.
