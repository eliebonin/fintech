# Valuation review signals and dual-currency accrued stocks

**Goal:** Make missing optional components discoverable without obstructing daily
Ops review, and display accrued stocks in local and reporting currency.

**Agreed scope:** User approved points 1 and 2; mixed-portfolio acceptance awaits
their data. Work sequentially in the existing checkout, with focused tests and
no operating financial writes or automatic commit. No new publication gate.

**Design:** One compact, collapsed input-review disclosure in the persistent
result summary; concise per-position notes open the existing inspector. Keep
blocking source/amendment failures prominent and independent. Remove duplicate
coverage banners, retain exact missing dates and source details on demand.
Backend and fallback Attention classification include missing interest FX,
accrued stock/FX and anchor discrepancies. Only actual window-bounded cash gaps
make a result partial; disappeared historical account/currency scopes remain
outside the warning population. Counts describe input dates/positions, not money.

**Alternatives considered:** Stacked banners are too disruptive; toast/modal
warnings disappear or interrupt review. The chosen inline disclosure preserves
permanent access to evidence with lower visual density. This is an implementation
choice informed by GOV.UK/Carbon guidance, not a new financial rule.

**Stock display:** A response-only exact Decimal projection translates retained
opening stock at frozen opening FX and closing stock at frozen closing FX.
Recorded equal currencies imply identity; known zero stock remains zero without
requiring a rate. Missing foreign FX/stock stays unavailable independently per
boundary. No current-FX query, financial evidence rewrite, duplicate stock columns
or schema migration. Original movement/receipt/CARRY proof stays inspectable.

## Tasks

- [x] 1. RED→GREEN pure coverage/attention and stock-projection tests; integrate
  engine completeness and authorized API presentation without changing amounts.
  Test cash-only gaps, no historical-scope warnings, zero/negative stocks, missing
  rates, exact precision, input immutability and denied-evidence behavior.
- [x] 2. RED→GREEN compact disclosure/Attention navigation, remove repeated
  notices, and add dual-currency stock display with detailed movement proof.
  Preserve pagination, closed inspector default, source filtering and blockers.
- [x] 3. Focused native database/API regressions, frontend tests/typecheck,
  isolated responsive/browser/console checks, and documented activation.
- [x] 4. Reconcile root AGENTS/KNOWLEDGE/FIX and capability register/map. Resolve
  FIX-VAL-005/006 only to the extent demonstrated. Keep broader source fanout,
  modelling and independent portfolio acceptance open.

## Research and verification ledger

Checked 28 October: [GOV.UK notification guidance](https://design-system.service.gov.uk/components/notification-banner/)
recommends sparse banners and in-context page content; [Carbon notifications,
updated 12 August 2026](https://www.carbondesignsystem.com/building-blocks/core/patterns/notifications)
supports concise inline feedback with proportionate interruption; [WCAG 2.2
status-message guidance](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
supports programmatic status without focus interruption. Apply a polite compact
status and native keyboard-operable disclosure; text carries meaning alongside
colour. No assistive-technology certification is claimed by automated checks.

Completed 29 October: [delivery, evidence and limitations](../../delivery/valuation-review-signals-20261029.md).
51 offline cases, 39 disposable-database cases and a final 11-case projection
rerun passed. 47 frontend cases, TypeScript/OpenAPI parity and two isolated
keyboard/mobile/console browser scenarios passed. API 8001 reloaded/healthy;
frontend 3001 started. No migration or operating financial writes. Portfolio
acceptance remains deferred until the user supplies data.
