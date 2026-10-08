# Valuation follow-up hardening

Approved scope: leave corporate-action safety unchanged; fix timestamp semantics,
calendar history, evidence permissions, unnecessary opening marks, then operational safety.

## Execution order and acceptance

1. Recognise both stored daily-bar timestamp labels; neither is eligible for intraday/fixing selection. Test real resolver with Yahoo's label.
2. Enforce calendar/session/holiday recording cutoffs. Valuation requires a sealed reference calendar, using existing database immutability triggers. Provide an explicit copy-and-publish reference calendar operation; never pretend a calendar published today was known historically. Test late reference dates and immutable publication.
3. Apply current tenant entitlement and DISPLAY permission to all valuation evidence responses, including create and review; no publication without access to review inputs. Test revoked rights and opaque foreign resources.
4. Resolve opening prices only for opening holdings, closing prices for all closing lots. Test a new holding with no opening observation and preserve exact execution bridge.
5. Calculate under REPEATABLE READ, batch lifecycle loading, and provide locked stale-attempt recovery with a retained audit explanation. Test isolation and rejection of active/non-stale recovery. Background workers, checkpoints and evidence pagination remain a separate scaling project, not silently included here.

## Rulings / constraints

- Continue in the existing approved dirty feature checkout; preserve unrelated work. No automatic commit, push, operating-data edits or subagents.
- Focused tests first, then grouped disposable-database/API regression; no full-suite run by default, per owner direction.
- Existing sealed-calendar database triggers suffice: no new schema required to publish a reference copy. Mutable legacy calendars remain inspectable, but are not valuation-ready.
- Existing unprofiled datasets retain their legacy entitlement model; profiled datasets require reviewed DISPLAY rights. NON_DISPLAY does not imply DISPLAY.
- A current read restriction does not rewrite retained financial evidence or its historic calculation rights.

## Progress

- Tasks 1–4 complete: timestamp vocabulary, recorded-time and sealed calendar checks, current evidence access, and execution-only closing marks. Focused unit and database coverage passed.
- Task 5 complete: stable snapshot, bounded SQLSTATE 40001 retry, batch lifecycle loading, guarded failure recording and audited recovery command. Grouped valuation signoff: 52 passed, 8 existing warnings, 93.59 seconds; exit 0 and owned database cleanup (`logs/valuation-follow-up-signoff.log`).
- Ruling: simultaneous duplicate POST while RUNNING returns 409 `valuation.in_progress`, not a blocking wait — the configured lock timeout previously allowed the duplicate to fail the live worker's shared attempt. Retry unchanged with the same key; cost is a transient explicit conflict for that caller.
- Ruling: preserve existing sealed-calendar triggers and publish reference copies instead of adding a second calendar schema — source drafts remain editable, valuation references do not. Historical pre-publication availability cannot be invented.
- Ruling: conservatively withhold the whole financial batch when any source is currently undisplayable — this prevents inferred-price leakage via attribution components; cost is less granular evidence access until a licensed derived-output model is defined.
- Final self-review (sequential per owner direction) found that price-only attribution identity could reuse old calendar evidence. Identity now includes source and pricing/calendar provenance, excluding information-query-time-only changes. Pure regression RED→GREEN; storage regression included in signoff run.
- Lightweight checks: 50 passed; focused UI: 9 passed (an existing cold page-import timeout passed on rerun with 15-second test timeout); TypeScript exit 0. No assertion or test skip was weakened to pass.
- Follow-up concurrency root cause verified: SQLSTATE 55P03 from a duplicate wait led its failure handler to mark the active shared attempt FAILED; winner then encountered SQLSTATE 40001. Nonblocking duplicate handling and guarded failure recording passed the real simultaneous HTTP regression and active-worker state regression.
- Broader market-data/calendar run: 94 passed with one concurrency failure (`logs/valuation-follow-up-final.log`); that failure is fixed and passed in the 52-check signoff above. The earlier failed run is not reported as a wholly green run. No full Python suite was rerun.
- No subagent review, operating-data writes, calendar/policy reassignment, new schema migration, commit or push. Remaining scalability work is explicitly documented in the delivery report.
- Final Yahoo real-resolver control passed after strengthening the baseline selection assertion: 1 passed, 15 deselected, 23.54 seconds; exit 0 and owned database cleanup. Implementation and focused verification complete.
