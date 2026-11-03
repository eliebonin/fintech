# Frontend HTML and console integrity — 26 October 2026

**Status:** Implemented; verification below  
**Owner:** Operations Console / frontend engineering  
**Scope:** HTML nesting, native validation and browser diagnostics

## Review and fixes

The review inventoried 161 non-test TSX source files and checked 15 literal or
conditional input-pattern expressions. Source inspection was paired with the
existing browser journeys, then extended to supplied daily-interest evidence and
tenant group creation. This is a targeted console-integrity review, not an
exhaustive runtime, accessibility or security audit of every page/data combination.

| Finding | Consequence | Fix |
| --- | --- | --- |
| Supplied-interest currency names embedded native disclosures inside a paragraph; the shared name wrapper was an inline span containing flow content. | React reported details/summary descendants of p and warned about hydration. | ReferenceName now uses a flow-content div. Interest evidence gives local/reporting currency separate definition-list entries instead of a paragraph. Expandable IDs, copy controls, names and exact supplied amounts remain available. |
| Trade upload File source used an unescaped literal hyphen in its input pattern. | The browser rejected the Unicode-set regular expression and did not enforce the intended pattern. | Escape the literal hyphen, preserving the existing allowed characters and required alphanumeric first character. |
| Tenant group Code had the same unescaped-hyphen problem. | Browser pattern errors and missing native pattern enforcement. | Escape the literal hyphen; preserve the original letters/digits/underscore/hyphen convention. No authority or group-save semantics change. |

Implementation:

- [Technical references](../../../apps/ops-console/src/features/valuation/technical-reference.tsx)
  are flow content; use them in a div, table cell, definition or list item, not p/span.
- [Daily interest evidence](../../../apps/ops-console/src/features/valuation/input-evidence.tsx).
- [Trade upload](../../../apps/ops-console/src/features/imports/import-console.tsx).
- [Tenant group editor](../../../apps/ops-console/src/components/tenant-access-console.tsx).

## Regression protection

Every browser spec now uses the shared
[console check](../../../apps/ops-console/browser-tests/console-check.ts). It fails
the journey on browser warnings, errors and uncaught page errors, attaching the
diagnostics to failures. This covers React nesting/hydration/key warnings,
malformed native patterns and runtime exceptions encountered by those journeys.
There is no application-side console filtering or suppressHydrationWarning fix.

Resource-error console lines from deliberate HTTP-negative probes are excluded
from this test assertion; their status/recovery behavior is tested by the
individual journeys. This is not certification that every live API request is
healthy. Existing NO_COLOR/FORCE_COLOR warnings are test-process environment
warnings, not browser application errors.

New [pattern browser cases](../../../apps/ops-console/browser-tests/console-integrity.spec.ts)
check accepted and rejected values in the actual import and group controls without
saving. The supplied-interest case in
[P&L browser acceptance](../../../apps/ops-console/browser-tests/pnl-ops.spec.ts)
opens the inspector, checks exact values and expands both currency IDs while the
console guard runs.

## Verification

- Initial 37-case console-guard run: 35 passed; two import journeys exposed the
  malformed source pattern. The new interest case reproduced the p/details and
  p/summary diagnostics before the markup change.
- An initial group test incorrectly expected a short accessible name without its
  help text. Its locator was corrected; no timeout or application behavior was
  weakened. A temporary substitution of the old pattern in the isolated browser
  DOM then proved the regression rejects that broken pattern. The substitution
  was removed before final verification; product files were not rolled back.
- **1,026 frontend unit tests passed in 210 files.**
- **40 isolated headless-Edge browser journeys passed with the console guard
  enabled**, including native valid/invalid pattern checks and supplied-interest
  evidence. The full unit and browser logs are retained locally as
  logs/frontend-console-unit-final.log and logs/frontend-console-browser-verified.log.
- Final **TypeScript and whitespace checks passed**; normal dev Next imports
  were restored after the isolated browser server's type generation. Git reports
  the existing Windows LF/CRLF normalization notice for the edited app README.
  No Python suite, optimized production build or full live-page sweep was run.
- The final source scan found no candidates for the inspected p/block,
  span/disclosure, nested interactive/form/label or mapped-fragment patterns;
  all 15 inspected pattern expressions compile with the v flag. This bounded
  syntax scan is not a complete HTML validator or cross-component type proof.

No backend, migrations, financial arithmetic/evidence, permissions, operating
trade/balance uploads, calculations or publications changed. Existing dev service
hot reload applies the UI changes; no service restart is required. Sequential
author review followed the user's execution preference. No commit/push requested.

## Guidance checked 26 October 2026

- [HTML Standard: details](https://html.spec.whatwg.org/multipage/interactive-elements.html#the-details-element):
  disclosures belong in flow-content contexts. Applied to the shared reference
  component and its supplied-interest caller.
- [MDN: pattern](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/pattern):
  current native patterns use Unicode-set v semantics; literal hyphens need
  escaping, and invalid patterns are not applied. Applied to the two proven
  character-class defects, without changing backend validation.
- [React: hydrateRoot](https://react.dev/reference/react-dom/client/hydrateRoot):
  hydration mismatches are bugs to fix. The project choice was to repair markup
  and add real-browser diagnostic assertions, not suppress the warnings.
