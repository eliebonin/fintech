# Incomplete price review and reviewed mark overrides

## Intent and agreed workflow

Ops needs to review useful P&L when a required position price is absent. Calculate
and stage the priced population; retain every affected position as unpriced with
its required dates and original ledger proof. Missing contributions are unknown,
not zero. Report numeric aggregates as calculated subtotals. Normal publication
requires supplied marks or reviewed manual marks followed by recalculation.
Acknowledging a warning or adding a P&L adjustment cannot bypass that requirement.

## Chosen approach

Use the existing policy `WARN` / `MANUAL_OVERRIDE` missing-data actions. `FAIL`
keeps its existing behavior. Strict/flexible still controls rule selection.
Continue only for genuine absence/staleness under an eligible known rule;
authorization, licensing, invalid conventions, calendar failures and unsupported
economics remain hard errors. Do not silently fall through to another fixing,
dataset, prior date, another contract, execution price or zero.

Keep complete financial attributions numeric and retain unpriced position proof
separately in the immutable staged summary. This avoids fictitious zero
attributions or weakening existing financial-column constraints. If any daily
bridge lacks a required mark, the affected position's entire period contribution
is excluded from the priced-position subtotal and displayed as unavailable.
Independent economic flows/cash remain separately assessed. Optional accrual and
cash-snapshot omissions keep their previously agreed nonblocking behavior.

Add immutable manual-mark requests and decisions below HTTP. Bind each request to
a retained gap, exact tenant/strategy/policy/rule/cut/date and an eligible existing
series quotation. That series supplies units, currency and product dimensions;
the value is visibly a tenant-reviewed mark, not a provider observation. Preserve
source rights, reviewer independence (including real operator), source/reason,
exact Decimal value, information cutoff and later withdrawal/correction history.
Normal eligible observations win when supplied. Approved overrides only fill
permitted missing inputs and never edit prior attempts or stored observations.
Revalidate their current approval and scope before publication.

## Alternatives and trade-offs

- Failing the whole run preserves completeness but hides useful reviewed data.
- Inventing/carrying prices or booking adjustment P&L conceals unknown financial
  contributions; rejected.
- Partial staging plus independently reviewed source marks is the agreed choice.
  It requires explicit subtotal/coverage presentation and a server-side publication
  guard. A quote definition is required before a manual value can be meaningful;
  no unsupported instrument semantics are invented by the override workflow.

## Presentation and acceptance

Show Completed · Staged · Incomplete, a compact missing-mark count, labelled
subtotals and affected positions with unavailable P&L. Provide manual-mark request,
review and withdrawal controls using current valuation strategy actions. Keep
technical identity/proof in details. Publication stays disabled in UI and rejected
on the server while required inputs remain missing, including self-publication
and amended candidates. A new calculation uses later supplied/reviewed marks.

Tests cover FAIL/WARN, mixed/all-missing populations, multi-day and zero boundaries,
quote/FX semantics, preserved rights and authority, independent review/replay,
information cutoffs, withdrawal and stale publication. Use focused disposable
regressions and a local browser smoke check; no invented operating marks or
publication. Work sequentially in the current feature checkout, preserving all
unrelated changes; no commit or push is requested.

## Guidance checked

The [FCA COLL 6.3 guidance](https://handbook.fca.org.uk/handbook/coll6/coll6s3?timeline=true)
requires accurate official fund valuation and documented fair-value methods where
reliable prices are unavailable. The [ESMA valuation review](https://www.esma.europa.eu/sites/default/files/2023-05/ESMA34-45-1802_2022_CSA_on_Asset_Valuation_-_Final_Report.pdf)
emphasizes documented procedures and independent checks. These support governed
marks; they do not prescribe this internal partial P&L report or make it an
official NAV. Research performed 31 October 2026.

## Acceptance finding: cash FX

The first local partial FCPGF attempt reached cash assessment and exposed a
missing required FX observation on a supplied EoD balance. Extend the same
permissive missing-price classification to cash FX: retain account/currency and
snapshot proof, exclude its whole period contribution, and block publication.
Exact-date reviewed FX marks use the same independent workflow. Optional missing
cash snapshots remain nonblocking; no cash balance or provider quote is invented.
