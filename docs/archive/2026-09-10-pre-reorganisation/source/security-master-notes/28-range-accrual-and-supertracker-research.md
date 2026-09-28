# Range-accrual and supertracker onboarding

This note records the research and the deliberately small first implementation
slice for the two structured-product archetypes. It is a reference-data
contract, not a pricing engine.

## External evidence reviewed

The reviewed market documents consistently separate contractual observation,
accrual, and payment terms from the final payoff branches:

* The [SEC range-accrual supplement](https://www.sec.gov/Archives/edgar/data/9631/000119312512090184/d300603dsuppl.htm)
  defines the interest rate as the stated rate multiplied by `N / D`, where
  `N` is the number of calendar days on which the reference rate is inside the
  range and `D` is the total number of days. It also explicitly specifies how
  non-business days and the ending reference-rate date are treated.
* The [SEC structured-notes investor bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-76)
  describes range products as depending on the number of days the reference
  stays inside a specified range and separately describes participation rates
  and capped returns.
* A [Barclays Barrier Supertrack pricing supplement](https://www.sec.gov/Archives/edgar/data/312070/000191870426015925/form424b2.htm)
  documents the common least-performing-underlier form: principal plus an
  upside leverage factor when the final underlier is at or above its initial
  value, principal in the protected middle branch, and downside below the
  barrier.
* A [Barclays Supertrack term sheet](https://www.sec.gov/Archives/edgar/data/312070/000148105724008934/formfwp.htm)
  gives the same practical parameters: a barrier percentage, an upside
  leverage factor, and a worst-of reference set.
* A [capped leveraged note example](https://www.sec.gov/Archives/edgar/data/895421/000183988226013998/ms14612_424b2-08710.htm)
  shows that a cap is a maximum settlement amount and therefore limits the
  leveraged upside rather than changing the underlying's final fixing.
* The [ISDA FpML FX range-accrual schema](https://www.fpml.org/spec/fpml-5-11-7-rec-1/html/transparency/schemaDocumentation/schemas/fpml-fx-accruals-5-11_xsd/schema-overview.html)
  models the fixing schedule, observable source, accrual region, expiry, and
  settlement as separate concepts. It is an interoperability check, not a
  reason to copy the interchange payload into the internal tables.

These are prospectus/filing examples, not a claim that every issuer uses the
same convention. The implementation therefore stores the convention instead
of inferring it from a product label.

## Second-pass verification (10 September 2026)

The review was repeated against primary-source disclosures before freezing the
first slice. The SEC range-accrual material shows both the minimum/maximum
coupon behaviour and the distinction between a stated annual factor and the
qualifying observation fraction. A separate SEC example makes the calculation
explicit as `Interest Factor × Variable Days / Actual Days` and spells out that
payment-date postponement and non-business-day treatment are contractual. The
Barclays Barrier Supertrack disclosure confirms the least-performing-underlier
branches (upside leverage, a protected middle branch, and downside below a
barrier). A recent Morgan Stanley capped-leveraged note also demonstrates that
an underlying cap level and a maximum settlement amount are not necessarily the
same term. The first slice therefore keeps an underlying-return cap and defers
amount-based caps instead of silently treating those terms as interchangeable.

## Range accrual: minimum contractual model

The product is a parent structured-product instrument with:

1. a periodic coupon programme;
2. one range eligibility condition group per coupon period, with inclusive
   lower and upper levels (unless the term sheet says otherwise);
3. a coupon rate quoted per annum and an explicit accrual basis;
4. an observation frequency (daily, weekly, or monthly for the first slice);
5. a non-business-day treatment; and
6. a period payment date that may differ from the last observation date.

The economic coupon is:

```text
coupon = notional × annual coupon rate × accrual fraction
accrual fraction = qualifying observations (or qualifying days) / denominator
```

The denominator is not implicit. `OBSERVATION_COUNT` and `CALENDAR_DAYS` are
different contractual bases. The first UI preview shows one row per coupon
period and the range rule; it does not create a child digital instrument for
each daily fixing. `observation_schedule_id` currently points to the
coupon-period anchor schedule. Persisted range terms carry the observation
convention so a later lifecycle service can materialise and evaluate the
detailed fixings without pretending that the preview is the fixing ledger.
The generic coupon-programme and coupon-period `coupon_rate` fields are NULL
for this subtype: they represent per-period rates, whereas the annualised rate
belongs only in `structured_product_range_accrual_terms`.

The MVP leaves holiday calendars and publication/fixing lags to the governed
calendar/lifecycle service. It must not silently assume that a weekend-only
preview is the production result.

## Supertracker: minimum contractual model

The product is a parent structured-product instrument with a final valuation
and maturity settlement. Its graph contains:

* one long vanilla call/return component carrying the positive participation
  (for example `1.35` means 135% exposure);
* optionally, one short call at the cap strike carrying the same negative
  participation. A cap expressed as a return percentage `C` is represented by
  a cap call strike of `100 + C` percent of the initial fixing, so the signed
  call combination flattens at the contractual maximum;
* optionally, a separate signed KIP/downside component with its own barrier
  observation style; and
* a parent final-redemption action at maturity. Principal redemption is a
  parent lifecycle action, not an invented principal option child.

The final branch is evaluated by the later outcome service. `SINGLE`,
`BEST_OF`, and `WORST_OF` remain explicit scope choices; the UI does not hide a
worst-of assumption in the word “supertracker”. The current onboarding slice
fails closed unless the scope is `SINGLE` with one underlying. A future
worst-of/basket slice should use a dedicated reference basket or payoff node,
so it can define the aggregation and fixing/disruption rules once rather than
copying a single-underlier option per component.

## Deferred decisions

The following are intentionally outside this onboarding slice:

* issuer-specific barrier observation and market-disruption rules;
* lookback/high-water-mark and averaging variants;
* dual-range or multi-rate range accruals;
* callable/issuer-option features;
* a full payoff/pricing engine and condition-outcome ledger; and
* production holiday calendars and fixing publication lags.

Those features require versioned lifecycle/outcome contracts and should be
added as explicit terms, not inferred from subtype names.

The primary sources used for the second-pass check are the [SEC range-accrual
disclosure](https://www.sec.gov/Archives/edgar/data/806085/000119312508187726/dfwp.htm),
the [JPMorgan range-accrual term sheet](https://www.sec.gov/Archives/edgar/data/19617/000089109212003517/e48892fwp.pdf),
the [Barclays Barrier Supertrack disclosure](https://www.sec.gov/Archives/edgar/data/312070/000148105724008934/formfwp.htm),
the [Morgan Stanley capped leveraged note](https://www.sec.gov/Archives/edgar/data/895421/000183988226013998/ms14612_424b2-08710.htm),
the [ISDA FpML range-accrual schema](https://www.fpml.org/spec/fpml-5-11-7-rec-1/html/transparency/schemaDocumentation/schemas/fpml-fx-accruals-5-11_xsd/schema-overview.html),
and the [SEC investor bulletin on structured notes](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-76).
