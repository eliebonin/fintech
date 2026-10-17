# FX-forward end-to-end acceptance — 14 October 2026

Later same-day follow-up: the historical cancellation/rebooking limitation recorded below is addressed by [trade corrections and valuation reassessment](trade-corrections-valuation-reassessment-20261014.md). Its disposable browser acceptance stages/publishes the corrected 15,000 USD result and preserves the original 10,000 USD evidence. This original report remains a record of the earlier test state; operating migration 92 activation is still pending.

## Outcome and scope

The normal deliverable-forward rate-P&L and maturity paths passed in disposable
databases. This is bounded alpha acceptance, not discounted MTM, payment processing,
all-instrument sign-off or production readiness. Operating data and permissions
were not changed. See [calculation contract](fx-forward-rate-pnl-20261014.md).

The original mock forward was booked through the actual product booking service
by the fixture, including frozen contractual evidence. Instrument creation and
original ticket submission were **not** repeated through the browser in this run.
Calculation, rate evidence inspection, maturity preview, edited-rate checking,
direct maturity booking, result inspection and history were exercised in the
browser. Amendment approval and independent publication used real HTTP endpoints
with a distinct synthetic reviewer and real operator, not an impersonation bypass.

## Verified cases

| Check | Evidence / outcome |
| --- | --- |
| Ordinary holding | BUY 1,000,000 GBP; agreed GBP/USD rate 1.10; 30 September rate 1.11 and 1 October rate 1.12. Browser calculation staged 10,000 USD P&L. |
| Frozen rate evidence | Browser displayed opening/closing contract rates, actual market dates, policy rule, source dataset and `FX_FORWARD_RATE_PNL`. Contract marks were not substituted by spot. |
| Publication controls | Creator's browser Publish button disabled; HTTP self-publication rejected (409); self-approval of amendment rejected (403). |
| Reviewed amendment | OTHER_COST -10 approved independently; revised batch published with net P&L 9,990 USD. Original candidate remained retained. |
| Accurate maturity override | Spot suggestion 1.12 retained separately from sourced actual closing rate 1.125. HTTP closure generated -1,000,000 GBP; same idempotency key returned the same trade IDs. Daily P&L 15,000 USD and closing value zero. |
| Browser override | Editing rate/source/reason disabled booking until Check entered rate succeeded; browser booked 1.125 and retained its source/reason and original suggestion. |
| Clean one-click browser maturity | In a fresh fixture, Ops clicked Book now using the explicit spot suggestion 1.12. Browser calculation then staged 10,000 USD with closing value zero; independent HTTP publication succeeded and browser history/result showed Completed · Published. |
| No cash side effects | First fixture DB inspection confirmed original investment quantity +1,000,000 unchanged, opposite maturity entry -1,000,000, zero exposure and no cash-balance rows for the synthetic strategy. |
| Focused safety regression | `tests/test_fx_forward_valuation.py` and `tests/test_fx_maturity_service.py`: **11 passed in 6.03 seconds**. Includes reporting FX conversion, wrong maturity proof, missing rates, independent maturity review and sourced overrides. Not a full regression run. |

## Remaining gap discovered

Cancelling an already-booked maturity closure and rebooking it is accepted by the
ledger workflow, but recalculating the period containing that closure/removal
blocks with `Unsupported in-period removal requires economic lifecycle treatment`.
Observed failed attempt: `01a13b09-3344-7831-a3b0-07fc56f744cd` in the first
disposable fixture. No staged result was fabricated or safety guard removed.

This is the existing unsupported in-period correction boundary, now demonstrated
in an FX maturity journey. Normal maturity closure does work; **cancel/rebook
valuation is not signed off**. Follow-up should define consistent corrected-ledger
reconstruction and its effect on staged versus previously published results, then
add a focused cancellation/rebooking valuation regression before enabling it.

## Repeatability and local test environment

- Start `scripts/run_fx_forward_e2e.py` with the repository Python runtime. It
  creates/migrates/seeds an owned `platform_isolated_tests_browser_<uuid>` database,
  prints synthetic IDs and serves API 8009. Its `finally` block cleans the owned
  DB after graceful exit; Windows process termination can skip that block. Always
  verify cleanup. In this run, after stopping the servers and verifying zero DB
  connections, only the two exact owned database names were explicitly dropped.
- Start `scripts/run_fx_forward_e2e_ui.cjs` with `REFERENCE_API_URL` pointing to
  `http://127.0.0.1:8009` and a separate `NEXT_DIST_DIR`; UI uses
  `http://fx-e2e.localhost:3009`. Its custom server binds only 127.0.0.1.
- Separate hostname prevents operating-cookie sharing. Binding the usual Next
  CLI to 127.0.0.1 caused its normalized server URL to disagree with browser
  Origin and correctly trigger the existing same-origin guard. The companion
  server supplies the matching hostname; security checks were not weakened.
- After the first browser holding calculation, run
  `scripts/check_fx_forward_e2e.py <strategy-id> <reviewer-id>` for the HTTP
  amendment/publication/override/idempotency assertions. It refuses a strategy
  unless options expose the exact synthetic label.
- Recreate the fixture before clean maturity acceptance if cancellation/rebooking
  has been exercised. Do not delete retained events to force calculation to pass.

Two disposable browser fixtures were used; the second established the clean
maturity/publication path separately from the correction blocker. Test UI/API
processes are stopped afterward; temporary Next-generated config changes are
removed. Browser screenshot evidence is retained outside the repository in the
task visualization directory.
