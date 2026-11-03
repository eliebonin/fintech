# Incomplete price review and reviewed manual marks

**Scope:** F32/F37/F39 alpha. Useful partial economic P&L for Ops review; not an
official NAV, a complete financial result or permission to publish unknown P&L.

## Delivered behavior

- A rule with `WARN` or `MANUAL_OVERRIDE` stages available investment positions
  when a required price/position FX observation is absent or too stale. `FAIL`
  retains its blocking behavior. Strict/flexible remains a rule-selection choice.
- The full original position projection, ledger facts, requested dates, missing
  resolutions and available selected marks remain retained. Unpriced positions
  have unavailable P&L, without fabricated numeric attributions. A missing daily
  bridge excludes that position's entire requested period from the priced subtotal.
- The same bounded handling covers required FX on supplied EoD cash balances.
  Affected account/currency scopes retain snapshots and unavailable FX P&L;
  their entire period contribution is excluded. Missing cash snapshots and
  optional assessed interest remain their separate, nonblocking coverage cases.
- Results show Completed · Staged · Incomplete, calculated subtotals, unpriced
  positions/cash and exact missing dates. An all-unpriced financial population
  displays unavailable amounts, not an apparently confirmed zero portfolio result.
- UI and server publication reject missing required marks. Self-publication,
  explanations and component amendments cannot waive the completeness check.

## Manual-mark workflow and controls

In the selected result's **Review** tab, an authorised calculator can request an
exact mark against a missing input's existing compatible quotation. The request
retains its Decimal value, currency/date, source reference, reason, confirmed quote
basis and verified selected-user/real-operator identity. A DIRTY bond quote also
requires its paired accrued component per 100 and quote settlement date.

An independently authorised reviewer and different real operator approve/reject
the request; an independent reviewer can later withdraw an approval. Switching
selected users under the same local operator is insufficient. Requests/decisions
are append-only. An uncertain UI request retains the same payload and key for an
explicit unchanged retry.

Approval does not edit provider observations, recalculate or publish. Ops prepares
a new calculation with a new information cutoff. Ordinary eligible observations
win; reviewed marks fill only exact permitted missing inputs known by that cutoff.
Current quotation, source rights and approval are rechecked before publication.
A later approval supersedes the prior manual mark; withdrawal never silently
revives an older mark. Used manual inputs retain their makers in publication
operator lineage. Changed/withdrawn decisions flag source reassessment without
rewriting earlier financial figures. Arrival of an ordinary source mark is also
checked before publication of a manual-mark candidate.

## Ownership and schema

- `valuation.price_inputs` owns typed missing-input handling and population proof;
  native product economics, quote/FX orientation and calendar guards stay in place.
- `valuation.mark_overrides` owns request, independent decision, exact-scope
  selection and current-proof checks; `mark_health` projects review-state changes.
- Migration **107** adds `nav.valuation_mark_override_request` and
  `nav.valuation_mark_override_decision`, with typed exact financial fields,
  tenant scope, replay identities and mutation-rejection triggers. No source price,
  trade, prior attribution or permission migration is performed.
- The audited HTTP/BFF adapters expose scoped review/create/approve/reject/withdraw
  operations. The portal renders server amounts and authority; it does not reprice.
- Source-specific FCPGF reconciliation scripts remain ignored/private or under
  optional `tooling/reconciliation_csv`, outside product runtime and migrations.

## Boundaries and remaining work

Only genuine missing/stale observations under a known permissive rule are softened.
Invalid terms, units, currencies, price-basis evidence, unsupported instruments,
calendar configuration, licensing and authority are not repaired by an override.
Missing quote definitions still require governed configuration. No implied spot,
execution-price, prior-date, other-contract or zero substitute is introduced.

Independent economic-flow FX remains subject to its existing required-input
validation; this delivery does not invent an incomplete monetary-flow ledger.
Optional interest/cash omissions do not become mandatory merely because this
required-price guard exists. There is no automatic mark expiry/recalculation,
provider-price insertion, official-NAV certification or operating publication.

## Verification and activation

Focused disposable-database checks cover mixed/all-unpriced populations, both
boundaries, hard FAIL/calendar errors, authority, Decimal/replay/scope, real-operator
independence, information cutoff, source arrival, withdrawal, dirty bond pairing,
cash FX and publication guards. Valuation-scoped frontend tests and TypeScript
checks cover subtotal/unavailable rendering and the allowlisted BFF. Three
isolated Edge journeys cover all-unpriced/mobile display, uncertain exact retry
and independent approval with explicit recalculation, including console diagnostics.

Migration 107 is applied locally, with API 8000 and portal 3001 running. The
FCPGF 19→20 October rerun used a new immutable v2 policy with WARN actions;
its original v1 and the FCAGF policy are unchanged. It completed into staging:

- 125 investment buckets: 123 calculated and two unpriced forwards.
- Four missing required observations: the two 19 October contract-forward marks
  and SGD→GBP cash FX for 19 and 20 October, affecting one cash account/currency.
- Calculated net subtotal **−29,187.337591610357 GBP**; price/FX subtotal
  **−72,196.616419211257 GBP** and included cash FX **32,834.6018038488 GBP**.
  These are incomplete subtotals, not a whole-portfolio final result.
- Nine supplied-window cash scopes: six calculated cash attributions, one with
  missing required FX and two optional missing-snapshot cases. Historical absent
  account/currencies are not reintroduced as coverage obligations.
- Normal authenticated detail and mark-review endpoints return 200; all four
  gaps have compatible existing quote choices, with zero manual requests made.
- Live browser inspection confirms incomplete status, disabled publication,
  exact unpriced quantities/dates, SGD cash omission and Review controls. No
  browser warnings/errors were reported. Source-health CURRENT means retained
  sources are unchanged, not that required-price coverage is complete.

No mark was invented, requested, approved or published on the operating data.
No trade/source-price change, permission grant or full-suite run was performed.
Private request/response evidence remains ignored beside the retained bundle;
temporary operator API sessions were ended. Financial reconciliation of the
complete portfolio remains pending the four supplied/reviewed marks and a new
calculation.

## Guidance and design

The [FCA valuation rules](https://handbook.fca.org.uk/handbook/coll6/coll6s3?timeline=true)
and [ESMA asset-valuation review](https://www.esma.europa.eu/sites/default/files/2023-05/ESMA34-45-1802_2022_CSA_on_Asset_Valuation_-_Final_Report.pdf)
support documented valuation methods and independent challenge. They do not
prescribe this internal partial-report implementation or legitimise publishing
missing financial contributions. For the UI, the established
[WAI form grouping](https://www.w3.org/WAI/tutorials/forms/grouping/) and
[GOV.UK check-answers pattern](https://design-system.service.gov.uk/patterns/check-answers/)
inform grouped exact-input forms and explicit consequential review actions.
See the [agreed design](../superpowers/specs/2026-10-31-incomplete-price-review-design.md)
and [implementation ledger](../superpowers/plans/2026-10-31-incomplete-price-review.md).
