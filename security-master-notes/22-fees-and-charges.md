# Fees and charges

## Evidence status

The generic, effective-dated fee model is an internal product and calculation
boundary. It is not a claim that every fund, AMC, or share class follows the
same legal fee rule. The first research pass did not complete jurisdiction- and
vehicle-specific fee, disclosure, tax, or UCITS requirements; see the
[external evidence register](24-external-evidence-and-research.md).

## Purpose

Fees are contractual or operational charges that can affect an AMC,
structured product, fund, fund share class, strategy, mandate, trade, or
valuation result. They need a common vocabulary and effective-dated rules,
but contractual rules must remain separate from realised amounts.

This design deliberately avoids product-specific tables such as
`amc_fee`, `fund_fee`, and `share_class_fee`. The same fee framework is used
for every fee-bearing object.

## Boundary and schemas

The contractual fee model is centralised in one `fee` schema:

```text
fee.fee_type
fee.fee_rule
fee.fee_rule_target
```

The existing `trd.trade_fee` table remains in `trd` because a realised fee
attached to a trade is a trade-domain fact. It gains an optional
`fee_rule_id` link to the contractual rule that was used, when one exists.

This is intentionally not a second generic fee-event table in the first
slice. NAV accrual events and non-trade charges can be added later once the
calculation and accounting boundary is agreed.

## Fee types

`fee.fee_type` is a governed catalogue, not free text. Initial values may
include:

```text
MANAGEMENT
PERFORMANCE
ADMINISTRATION
CUSTODY
DISTRIBUTION
ISSUER
REBALANCING
ENTRY
EXIT
REDEMPTION
BROKERAGE
TAX
WAIVER
REIMBURSEMENT
```

The catalogue identifies the business role of a charge. It does not encode
how the charge is calculated.

## Versioned fee rules

`fee.fee_rule` stores one immutable version of a calculation rule. It
contains the calculation basis and unit-aware parameters:

```text
fee_rule_id
fee_type_id
rule_code
display_name
calculation_method       -- RATE, FIXED, TIERED, PERFORMANCE, WAIVER, ...
calculation_basis        -- NAV, AUM, NOTIONAL, PERFORMANCE, TRANSACTION_VALUE
rate_value
rate_unit                -- PCT, BPS, AMOUNT, MULTIPLIER
currency_id
accrual_frequency
payment_frequency
day_count_convention
minimum_amount
maximum_amount
parameters_json
tenant_id
valid_from
valid_to
version_no
is_current
supersedes_fee_rule_id
source_payload_id
source_reference
approved_by_user_account_id
approved_at_utc
created_at_utc
```

The stored rate follows the platform unit convention:

| `rate_unit` | Stored value | Meaning |
|---|---:|---|
| `PCT` | `12` | 12 percent |
| `BPS` | `125` | 125 basis points |
| `AMOUNT` | `1000` | Literal monetary amount in `currency_id` |

`NUMERIC` is used for all monetary and rate values. A fee rule with
`valid_from = 2026-01-01` and `valid_to = NULL` is the rule used from that
date forward, subject to status and target assignment.

`is_current` is a convenience projection for operational screens. A resolver
must use effective dates and status, not the flag alone.

## Generic target assignment

`fee.fee_rule_target` assigns a rule to exactly one fee-bearing target:

```text
fee_rule_target_id
fee_rule_id
target_reference_node_id
target_strategy_id
application_mode          -- ADDITIVE, REPLACE, DEFAULT, WAIVE
priority
payer_organisation_id
recipient_organisation_id
effective_from
effective_to
status
created_at_utc
```

The target check requires exactly one of `target_reference_node_id` and
`target_strategy_id`.

`target_reference_node_id` covers canonical or private reference objects such
as:

* an AMC certificate;
* a fund vehicle;
* a fund share-class instrument;
* a bond or structured product.

`target_strategy_id` covers:

* a fund or mandate book;
* a managed AMC reference portfolio;
* a prop-trading or house book;
* a client portfolio or other operational ledger.

The target table uses typed foreign-key columns rather than a free-form
`target_type`/`target_id` pair. This keeps the model generic while allowing
PostgreSQL to enforce that the target exists.

## Examples

```text
Fund-level management fee:
  fee_type = MANAGEMENT
  basis = NAV
  rate = 0.50 PCT
  target = fund reference node

Share-class distribution fee:
  fee_type = DISTRIBUTION
  basis = NAV
  rate = 0.25 PCT
  target = share-class instrument node

AMC management fee:
  fee_type = MANAGEMENT
  basis = NAV
  rate = 1.25 PCT
  target = AMC instrument node

Reference-portfolio performance fee:
  fee_type = PERFORMANCE
  basis = PERFORMANCE
  rate = 20 PCT
  target = managed reference-portfolio strategy
```

Fund-level charges and share-class-specific charges are both supported. The
resolver applies the explicit `application_mode` and `priority` rules rather
than assuming that every specific fee replaces a parent fee. This is needed
because some charges stack while others are waived or replaced.

## Contractual rule versus realised charge

The fee model is deliberately split into two concepts:

```text
fee_rule                  contractual calculation rule
trade_fee                 realised fee attached to one trade
```

`trd.trade_fee` keeps the realised amount, currency, payer, recipient,
accrual date, settlement date and status. Its optional `fee_rule_id` points
back to the rule used to calculate it. A trade fee must remain meaningful even
when no contractual rule was available, for example when imported from a
custodian statement.

For Soft NAV, the calculation run must retain the fee-rule UUID/version used
for each fee deduction. Changing a fee rule later must not change a historic
NAV result; a corrected fee requires a new calculation run and the normal
supersession/reconciliation process.

## Performance and tiered fees

The first schema supports complex calculations through:

* `calculation_method`;
* `parameters_json` for versioned model parameters;
* `minimum_amount` and `maximum_amount`;
* explicit accrual/payment frequencies and day-count conventions.

This is a storage boundary, not a generic formula interpreter. A calculation
service must version its implementation and validate the parameter shape for
each `calculation_method`.

High-water marks, hurdle rates, crystallisation dates, breakpoints, fee
waivers and expense caps remain calculation-policy details. They should be
added as typed structures only when the first real products require them.

## Governance and effective dating

Fee rules are append-only versions:

1. create a new rule version;
2. link it to the prior version with `supersedes_fee_rule_id`;
3. close the previous validity period;
4. approve the new version;
5. resolve by valuation date and target;
6. persist the selected rule in the NAV or fee calculation evidence.

The rule's validity and the target assignment's validity intersect. A target
assignment cannot make a rule valid outside the rule's own validity window;
that invariant is enforced by the fee resolver until a cross-row database
constraint is introduced.

## Deferred decisions

The following are intentionally deferred:

1. Whether NAV accruals and non-trade charges need a central `fee_event`
   table, or should remain in NAV/accounting-specific output tables.
2. Typed tier/breakpoint rows for asset-based fee schedules.
3. A dedicated performance-fee state model for high-water marks, hurdles,
   crystallisation and equalisation.
4. Automatic inheritance from fund to share class; the V1 resolver requires
   explicit assignment plus `application_mode`.
5. Database enforcement that assignment dates remain inside rule validity;
   the current service boundary validates this cross-row rule.
6. Tenant-specific fee-rule approval and override policy beyond the nullable
   `tenant_id` boundary.

## Research basis

The design reflects the way regulated fund documentation and controls treat
fees: charges are allocated to the relevant vehicle or share class, may be
based on NAV or other measurable bases, and must remain explainable in the
valuation and investor-reporting record.

* [FCA COLL 4](https://handbook.fca.org.uk/handbook/coll4) — UCITS operating
  charges, performance-related fees, and transaction-cost disclosure.
* [SEC mutual-fund prospectus example](https://www.sec.gov/Archives/edgar/data/722574/000072257424000292/filing7987.htm)
  — class-specific management rates, NAV-based calculations, tiers, and
  waivers.
* [ESMA performance-fee guidance](https://www.esma.europa.eu/press-news/esma-news/esma-publishes-guidance-performance-fees-in-ucits-and-certain-aifs)
  and [ESMA Q&A](https://www.esma.europa.eu/publications-data/questions-answers/966)
  — crystallisation and performance-fee governance considerations.
* [IOSCO good practices on NAV errors](https://www.iosco.org/library/pubdocs/pdf/IOSCOPD811.pdf)
  — reproducible records, correction handling, and investor-impact analysis.
