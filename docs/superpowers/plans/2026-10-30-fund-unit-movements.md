# Fund unit movements and FCPGF completion

**Goal:** Record the owner-approved interpretation of the 28 zero-source-price entries: 12 transfers (initial allocations, offsetting entries, reductions) and 16 recurring reinvestment unit credits. Source classification remains a disclosed assumption, not a confirmed broker event type.

**Design:** Add an HTTP-independent native fund-unit movement command under `trading`, reusing existing authority, locked approved listing, annotations, idempotency and immutable BOOKED evidence. Ordinary purchases continue to require a positive execution price. Movement records explicitly have no execution price/cash consideration, retain the source zero and carry a TRANSFER or REINVESTMENT type. The source-specific mapping/operator stays under optional reconciliation tooling.

**Financial treatment:** Both kinds change holdings. A daily movement's policy-selected closing NAV supplies its recognition value for the market bridge, excluding the introduced/removed principal from price gains. Reinvested distribution income is recorded separately: an unassessed income source produces a retained partial-coverage warning, not fabricated zero or duplicate income. No cash balance or dividend payment is generated. Multi-day daily calculations use each movement's economic day's NAV/FX, never a later period-end mark. Intraday movement recognition is outside this first daily convention.

## Steps

- [x] Pin positive-price purchase behaviour, typed movement proof, signed transfer quantities, positive reinvestments and source precision with focused tests.
- [x] Implement native movement command and immutable quantity/type proof; preserve tenant/action/strategy and reference checks on writes/retries.
- [x] Integrate position normalization, daily market bridge, retained decisions and review warning; test transfers in/out, net-flat movement days, historic holdings, FX and missing marks.
- [x] Use the isolated source adapter to classify/book the 28 owner-authorised rows. Retain original source values, per-row assumptions and idempotent native identities. All ten fund quantities/200 rows reconcile; keep the four unsupported rate-leg swaps explicit.
- [x] Update maintained documentation, verify focused regressions and restart the local API. No operating valuation publication.

## Guidance

In-kind assets entering/leaving a portfolio are distinct from investment return;
see the [GIPS firms handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/).
Reinvestment purchases additional shares using a distribution; the movement and
the underlying distribution must remain distinguishable, as described in the
[SEC mutual fund explanation](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-funds-etfs/mutual-funds).
These references guide this bounded design, not a GIPS compliance claim or tax/accounting implementation.
