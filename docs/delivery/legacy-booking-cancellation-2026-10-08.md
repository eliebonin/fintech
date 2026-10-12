# Legacy booking cancellation and valuation exclusion

## Reported cause

Run correlation `a4834c0c-d132-4b28-bcbf-6e2d78d349ac` failed because trade `c96bdbc3-6034-4f06-b5b8-341243d1813a` (ETP-TEST-1 / ETP-TEST, execution 2026-09-30) has an empty original BOOKED snapshot. The active trade cannot safely be valued from current instrument terms. Separately, both UI correction eligibility and the cancellation API required newer snapshot evidence, making the advised cancellation path unavailable.

## Fix

- A legacy investment booking with one valid original BOOKED event and an empty/null snapshot can be **cancelled only**, under existing tenant/TRADING authority, mandatory reason, expected lifecycle sequence, idempotency and locking. Actual execution must match the original event and no new-format frozen recognition columns may be present. Malformed/nonempty unsupported snapshots and absent history remain blocked. Legacy records cannot be replaced using guessed economics.
- The trade detail UI shows **Cancel erroneous booking** and a legacy explanation, without a replacement link. Derived `LEGACY_UTC_TRADE_DATE` display fields are not mistaken for new-format stored evidence. Existing permission gating is unchanged.
- The reader validates the eligible lifecycle chain before requiring economic snapshots. A cancellation/supersession known at the frozen information cutoff and effective by the opening boundary removes the entire erroneous record; AS_OF uses its closing boundary. The projection retains original and removal facts in its audit/hash but requires no missing economics for that removed record. Active/malformed chains, unknown lifecycle effects and in-period removals still block safely. Current row status alone never determines historical exclusion.
- This is record correction, not sale, settlement, delivery or accounting. No market-price or corporate-action guard was relaxed. No migration needed.

## Verification and activation

Observed failing pure projection, UI-control and isolated backend regressions before implementing their respective fixes. A real-shape UI test additionally caught derived legacy date fields hiding the button; fixed and reverified. The first integration run found a missing-history diagnostic mismatch and a test relying on distinct PostgreSQL `now()` values within one transaction; the diagnostic and historical fixture were corrected, without relaxing cutoff logic.

- **40 focused pure Python tests passed.**
- **59 isolated backend tests passed**, covering legacy cancellation/replay, preserved original snapshot, full valuation P&L with a cancelled legacy record, information cutoffs, chunked reads, recognition evidence, existing corrections/permissions and valuation guards. Eight existing deprecation warnings remain; no full suite was run.
- **17 focused frontend tests passed**, plus TypeScript checking and production frontend build.
- Rebuilt/restarted console on 3000 and restarted API on 8000. Operating HTTP page acceptance on the reported trade returned 200, with the cancellation button and legacy explanation present and replacement link absent. No operating trade was cancelled, replaced or deleted by this work. Process-only console signing key rotated; tenant reselection may be needed.

## User workflow

Open the trade detail, use **Cancel erroneous booking**, enter a reason, review and confirm. Original facts stay in history. Then start a **new valuation request** with a fresh information cutoff after cancellation. Retrying the old frozen failed request must continue to see the booking as it was known before cancellation. Other independent valuation blockers (currency, pricing policy, calendars, missing prices) may still apply.
