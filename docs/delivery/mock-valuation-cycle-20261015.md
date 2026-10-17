# Mock valuation-cycle acceptance — 15 October 2026

**Scope:** Real API handlers, calculator, PostgreSQL, lifecycle and review workflow in owned disposable databases. Not a browser walkthrough, independent custodian reconciliation or full NAV sign-off.

## Connected scenario

Later user-authorized [app-database fixture](mock-bond-strategy-app-seed-20261015.md)
creates a visible strategy and two opening fills. It is separate from this deleted
disposable test population and does not yet include valuation inputs or publications.

[Executable acceptance test](../../tests/test_mock_bond_valuation_cycle.py): one dedicated synthetic GBP strategy, sourced fixed bond terms, retained as-booked nominal 100,000, clean execution amount 98,500, mark 99 and contractual maturity redemption 100. Source data/initial booking evidence are fixture-seeded; subsequent schedule, accrual, payment, cash, maturity, calculation, amendment, publication and recalculation actions use HTTP handlers.

| Check | Independently expected result |
| --- | --- |
| Before coupon/maturity, 30 September | Market P&L 500; daily interest 10; gross 510 |
| Record coupon receipt 1,000 on 1 October | No new trade/cash snapshot or interest income; prior gross remains 510 |
| Maturity booking on 1 October | Close nominal −100,000 at sourced 100; closing exposure/value zero |
| Maturity-day valuation | Market 1,000 + daily interest 10 = gross/net 1,010; coupon is not added again |
| Assessed accrued-stock bridge | Opening 990 + earned 10 − coupon movement 1,000 = closing zero; Ops supplies this explicitly |
| Cash snapshot | Separate company/account/date/currency record and preview; not automatically included as cash P&L/NAV |
| Ops attempts self-publication | Denied; independent-review authority is not waived |
| Pending −5 adjustment | Publication blocked until independently reviewed |
| Approved amendment | New staged candidate and its own attempt; gross 1,010, net 1,005 |
| Independent publish | Candidate becomes PUBLISHED with retained evidence |
| Cancel closure | Published values/items remain identical; source health becomes REASSESSMENT_REQUIRED |
| Rebook and explicitly recalculate | New STAGED successor: zero closing value, gross/net 1,010. Manual −5 is not automatically reapplied |
| Publish successor | Prior result becomes SUPERSEDED; its stored values/items remain identical |

The connected scenario uses GBP throughout. Foreign conversion is covered by separate focused tests in the same exercise, not falsely represented as a foreign bond in this strategy.

## Verification

Supporting run: **32 passed** in 35.06 seconds of pytest execution, across:

- `test_bond_coupons.py`, `test_bond_coupons_api.py`;
- `test_bond_redemption_journey.py`, `test_bond_redemption_valuation.py`;
- `test_valuation_amendments.py`, `test_valuation_reassessment_api.py`;
- `test_valuation_fx.py`, `test_cash_snapshot_api.py`.

These check coupon immutability/scopes, maturity review/direct/correction flows, final-day interest, pending amendments, retained publications/recalculation retries, real policy-selected FX including execution-date conversion, and exact-date cash uploads/corrections/previews.

The connected scenario subsequently passed once in 6.08 seconds, then **three independent repeat runs passed** (10.72, 7.04 and 7.42 seconds of pytest execution). Repeats are not additional unique test cases: there are 32 supporting cases plus one connected scenario. All runs use `scripts/run_isolated_python_tests.py`; the operating database is not a pytest target. No production code, operating permissions, trades, receipts or valuations were changed by this exercise. Owned test databases are dropped by the runner. The connected fixture restores its own shared bond-date/policy setup. No full regression suite was run. Existing Starlette/httpx deprecation warning remains.

Final fixture-composability check: connected cycle followed by `test_direct_maturity_books_current_nominal_once_and_replays_to_zero`: **2 passed in 4.56 seconds**. The connected test now owns a separate strategy-specific policy, retaining audited rules rather than deleting them. An initial cleanup attempt correctly failed on `market_data_resolution_snapshot_item_policy_rule_id_fkey` and left shared sequence 90 occupied, making the following fixture fail with `uq_valuation_policy_rule_sequence`; both test-fixture failures were resolved by policy ownership, without disabling constraints or changing production code. The retained synthetic policy/evidence lasts only until the disposable database is dropped.

## Findings and limits

1. **Test correction, not an application defect:** the initial connected test incorrectly expected the original calculation attempt to point to an amended result. Approval deliberately creates a separate amendment attempt and cancels its predecessor candidate. The test now follows that returned attempt ID.
2. **Intermittent maturity rebooking rejection:** one subsequent connected run rejected the second closure with HTTP 409, `Closing entry did not bring exposure to zero`. Its transaction rolled back; published evidence remained intact. Later runs passed. The current post-insert verification reuses the candidate's pre-insert information cutoff; host/database timestamp alignment is a suspected cause, not established by the passing runs. The test retains bounded real ledger-query diagnostics for recurrence. See [FIX-VAL-004](../../FIX.md#fix-val-004--p2--intermittent-maturity-rebooking-rejection). Do not hide this failure behind later green runs or weaken the zero-exposure check.
3. API/database acceptance is stronger than isolated arithmetic tests but does not replace browser interaction checks, external reconciliation, automatic entitlement/accounting, full cash P&L or coverage of currently unsupported valuation products.

## Reproduce

```powershell
.venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/test_mock_bond_valuation_cycle.py -q -s --tb=short -p no:cacheprovider
```

No operating migration/restart is required for these new tests. This is acceptance evidence for the existing [coupon implementation](bond-coupons-20261015.md), not a new pricing methodology.
