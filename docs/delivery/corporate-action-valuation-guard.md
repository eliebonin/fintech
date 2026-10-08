# Historical corporate-action valuation guard

Date: 2026-10-07. Scope: fail-closed safety correction, not corporate-action position replay.

## Behaviour

Original trades and their booked quantities remain unchanged. A calculation now checks every retained booking from execution through the closing cutoff, rather than checking only the opening-to-closing P&L interval. Thus a split before the opening cutoff cannot silently leave a carried holding at its original quantity.

The guard resolves listings to canonical instruments and batch-loads known non-cancelled STOCK_SPLIT, BONUS_ISSUE, SPIN_OFF, MERGER and SECURITY_REPLACEMENT records. Events recorded after the requested information cutoff are excluded. Either EX or EFFECTIVE evidence may require replay; neither is silently preferred. Trades demonstrably after an action, actions after close and actions on unrelated instruments do not block.

Exact timestamp ordering is used where supplied. Equal execution/event timestamps, date-only execution-day or closing-day ordering, missing effective-date evidence, unknown timezone and contradictory date/time evidence block conservatively. Business dates use the source timezone when supplied, otherwise the listing venue timezone. No UTC-midnight assumption is invented.

Blocking happens before price selection, snapshot persistence or financial staging. A safe diagnostic identifies the corporate action, canonical instrument, trade and event date. The existing runner retains that diagnostic in the independently committed failure log after rollback. There is no override that silently declares the action applied.

## Limits and follow-up

This delivery prevents unsafe results; it does not transform 10 booked shares into 20 derived shares. Future replay must apply recorded economic effects to reconstructed positions at each cutoff, preserving trades and frozen evidence. Fractional entitlements, mergers/spin-offs, cash/income and corporate-action review workflows are not introduced.

The current corporate-action date table has no separate recording timestamp. This guard respects the action record's information cutoff, but does not claim full bitemporal governance for later date edits or inferred event-version cancellation chains. Those require explicit event identity/version/date governance before reproducible replay can be signed off. Unknown/unrecorded actions cannot be discovered by this guard. Opposite retained bookings are not compressed into tax lots or net-position checkpoints.

No schema migration, operating trade/price/action mutation, permissions change, automatic commit or push. Sequential author review only.

## Verification

The pre-opening split regression failed before implementation because valuation incorrectly succeeded (logs/corporate-action-guard-red.log). Sixteen lightweight guard cases failed before the module existed. After implementation, 43 lightweight guard/economics/replay tests passed in 0.90s. PostgreSQL-backed service/storage/API/HTTP acceptance: 34 passed, eight existing SQLAlchemy warnings, 106.95s; runner exit 0 and disposable database cleanup (logs/corporate-action-guard-green.log). Tests verify diagnostic identifiers, unchanged original trade records, post-action execution, future/cancelled/unknown-at-cutoff actions, unrelated instruments and missing/same-day date evidence.

The full isolated Python run was stopped at the owner's explicit request to finish using the passed focused checks. Last retained completed progress line was 24%, without failure output; this is not a completed full-suite pass (logs/corporate-action-guard-full.log). The two verified runner processes were stopped and their exact disposable database was removed after confirming zero remaining connections. Operating databases were untouched. Full regression remains a later integration/release checkpoint, not a prerequisite repeated for every bounded fix. A final lightweight rerun passed all 43 tests in 1.18s.

See [implementation plan and ledger](../superpowers/plans/2026-10-07-corporate-action-valuation-guard.md).
