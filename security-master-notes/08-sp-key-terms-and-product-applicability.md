# SP key terms and product applicability

## Evidence status

The term-definition catalogue is a deliberately generic reporting and
extraction layer. It does not replace contractual payoff terms, barriers,
schedules, or composition. The term codes and applicability rules are internal
governance choices and should be validated against product documentation and
legal terms for each live product; see the [external evidence and research register](24-external-evidence-and-research.md).

## Purpose

Structured products need a concise, governed layer of key terms and metrics for term-sheet extraction, textual product descriptions, comparison screens, data-quality checks, and reporting.

This layer is a projection over the canonical structured-product model. It does not replace barrier rules, schedules, composition, or dedicated terms tables as the source of contractual truth.

## Term-definition catalogue

```text
structured_product_term_definition
  term_definition_id
  term_code
  display_name
  description
  value_type
  unit_type
  applicable_product_category
  status
```

Typical definitions include:

```text
COUPON_RATE_PER_PERIOD
COUPON_RATE_PER_ANNUM
COUPON_FREQUENCY_PER_YEAR
AUTOCALL_FREQUENCY_PER_YEAR
KIP_BARRIER_LEVEL
CAPITAL_PROTECTION_LEVEL
ACCRUAL_RANGE_LOW
ACCRUAL_RANGE_HIGH
PARTICIPATION_RATE
BASKET_SIZE
```

Values are stored separately with source and lifecycle metadata:

```text
structured_product_term_value
  term_value_id
  parent_instrument_node_id
  term_definition_id
  numeric_value
  currency
  value_status                 -- EXTRACTED / VALIDATED / DERIVED / OVERRIDE
  source_document_id
  source_locator
  effective_from
  effective_to
  derivation_method
```

## Meaning of term values

The stored number is never implicitly rescaled. Its meaning is determined by the declared unit.

| Unit | Stored value | Meaning |
|---|---:|---|
| `PCT` | `12` | 12% |
| `VALUE` | `6` | Literal value 6 |
| `VALUE` | `1.20` | A 1.20 multiplier, for example 120% participation |
| `BPS` | `125` | 125 basis points = 1.25% |
| `COUNT` | `4` | Four items/underlyings/periods as defined by the term |

Use `NUMERIC` for values. Calculation services convert values only when a declared unit requires it; for example `12 PCT` becomes `0.12` for a pricing formula.

## Canonical data versus registry values

Classify a registry value by origin:

| Origin | Meaning |
|---|---|
| `EXTRACTED` | Captured from a source document or vendor feed. |
| `VALIDATED` | Reviewed/approved reference-data fact. |
| `DERIVED` | Calculated from canonical terms, schedules, barriers, or composition. |
| `OVERRIDE` | A governed correction/override. |

Examples:

* `KIP_BARRIER_LEVEL` is canonically represented by a KIP barrier rule; the registry exposes it as a key term.
* `BASKET_SIZE` is derived from basket/underlying constituent rows.
* `COUPON_FREQUENCY_PER_YEAR` is derived from the coupon schedule.

Do not allow a registry value silently to contradict a canonical term. Provenance and validation status must make clear whether it is extracted, derived, or an approved override.

## Scenario metrics

Best-case payout, maximum payout, annualised yield, and IRR are scenario-dependent, not absolute contractual terms. Store them separately with their assumptions and methodology.

```text
structured_product_scenario
  scenario_id
  scenario_name                -- BEST_CASE / BASE_CASE / WORST_CASE
  assumptions
  methodology

structured_product_scenario_metric
  parent_instrument_node_id
  scenario_id
  metric_code
  numeric_value
  unit_type
```

## Lightweight product-type applicability framework

The first implementation should use a simple mapping, not profile inheritance or a generic rules engine.

Use the generic security-master taxonomy catalogue for the structured-product archetype rather than a parallel product-type table:

```text
taxonomy
  taxonomy_code                -- STRUCTURED_PRODUCT_ARCHETYPE

taxonomy_value
  value_code                   -- AUTOCALL / AUTOCALL_CONSOLATION / PHOENIX / ATHENA / SUPERTRACKER / RANGE_ACCRUAL / VANILLA_SPREAD_KIP / VANILLA_KIP / DIGITAL_KIP
  parent_taxonomy_value_id     -- e.g. PHOENIX is an AUTOCALL child
```

`AUTOCALL_CONSOLATION` is a dedicated governed subtype under `AUTOCALL`. It
is not a new structural node type and does not replace the economic
instrument type `STRUCTURED_PRODUCT`; it is a product-archetype value used
for onboarding, applicability rules, search, and reporting. Selecting the
subtype requires a maturity `PAY_CONSOLATION` parent action in the
contractual graph. The action, its bounded KIP-to-final-payoff condition, and
its payout basis are the source of contractual truth; the taxonomy value is
only the classification.

```text
structured_product_taxonomy_term
  taxonomy_value_id
  term_definition_id
  requirement                  -- REQUIRED / OPTIONAL / DERIVED
```

Examples:

| Product type | Term | Requirement |
|---|---|---|
| `PHOENIX` | `COUPON_RATE_PER_PERIOD` | Required |
| `PHOENIX` | `AUTOCALL_FREQUENCY_PER_YEAR` | Required |
| `PHOENIX` | `KIP_BARRIER_LEVEL` | Optional |
| `PHOENIX` | `MEMORY_MODE` | Optional |
| `ATHENA` | `AUTOCALL_FREQUENCY_PER_YEAR` | Required |
| `AUTOCALL_CONSOLATION` | `CONSOLATION_RATE_PAYOFF` | Required |
| `AUTOCALL_CONSOLATION` | `KIP_BARRIER_LEVEL` | Required |
| `AUTOCALL_CONSOLATION` | `AUTOCALL_FREQUENCY_PER_YEAR` | Required |
| `SUPERTRACKER` | `PARTICIPATION_RATE` | Required |
| `RANGE_ACCRUAL` | `ACCRUAL_RANGE_LOW` | Required |
| `RANGE_ACCRUAL` | `ACCRUAL_RANGE_HIGH` | Required |
| `VANILLA_SPREAD_KIP` | Two signed vanilla payoff legs and `KIP_BARRIER_LEVEL` | Required |
| `VANILLA_KIP` | One vanilla payoff leg and `KIP_BARRIER_LEVEL` | Required |
| `DIGITAL_KIP` | Digital payout rate and `KIP_BARRIER_LEVEL` | Required |

An instrument is allowed to remain incomplete while in draft. On validation or activation, enforce that required terms are present, values use their correct units, and relevant canonical barriers, schedules, and composition are present.

## Deferred complexity

Defer profile inheritance, profile versioning, conditional term dependencies, multi-value/cardinality rules, and a generic rules engine until real product variations prove they are necessary.
