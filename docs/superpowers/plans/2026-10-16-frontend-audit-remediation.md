# Frontend audit remediation implementation plan

**Goal:** Address FRONTEND-001–010 with tested changes and truthful acceptance evidence.
**Execution:** Sequential in the existing feature checkout, as requested. No automatic
commit, push, operating-data mutation or dependency upgrade. Existing audit findings
are the specification; backend audit defects and structured-product economic design
are separate work. Existing unrelated edits must survive.

## Design and constraints

- Bind each document to a non-credential fingerprint of its HTTP-only context
  cookies. A shared browser transport echoes that fingerprint; Next Proxy compares
  it before any same-origin BFF mutation. Session selection/reset is explicitly
  exempt. Existing endpoint action/tenant/actor authority remains decisive.
- Keep payload/key intent immutable across uncertain writes; distinguish rejected,
  uncertain, confirmed and confirmed-but-refresh-failed. Do not infer duplicate
  writes from network failure or automatically replay them.
- Preserve exact decimal strings and current display rights. Presentation-only
  currency changes must not re-run financial selection.
- Keep cheap focused tests, add browser checks using synthetic handlers/data, and
  record real acceptance limits. No declaration of universal accessibility/security.

## Tasks and completion ledger

1. [x] **001:** Shared page-context fingerprint, browser transport and API Proxy;
   regression cases: missing/stale/same context, actor switch, session exemption,
   external requests and reads. Wire all browser writes, retaining endpoint checks.
2. [x] **002:** Preserve upstream request ID in BFF error JSON/headers; test with
   incoming correlation ID and without, preserving safe unknown errors.
3. [x] **003:** Explicit access reload result and stale lock; test successful command
   followed by failed read, read-only recovery and refreshed editor state.
4. [x] **004:** Shared retained mutation intent for older proposal forms and cash;
   changed intent blocked after uncertainty, same-key retry, confirmed new intent.
5. [x] **005:** Exact cash/fee formatting with tiny/large/negative regression values.
6. [x] **006:** Cash/coupon loaded/pending/error/empty states and dependent controls;
   test delayed and failed reads without false absence claims.
7. [x] **007:** Activate/focus/open correction destination, contextual Yahoo basis
   and scope copy; test actual navigation handler and series-specific explanation.
8. [x] **009/010:** Extract shared protocols, reuse monetary result for display
   toggles, batch visible labels and reuse coherent shell context. Assert request
   counts and retain rights/context invalidation. No whole-app rewrite.
9. [x] **008:** Real-browser synthetic critical journeys, keyboard/focus and
   responsive checks; retain executable evidence and distinguish manual acceptance.
10. [x] **Final:** Focused red/green tests, typecheck, bounded whole frontend suite,
    scoped review and MD reconciliation per stable finding ID.

## Review focus

Cookie switch in another tab must not redirect a stale write into that new context;
no fingerprint is an authorization credential. Delayed/failed refresh must never
suggest a rejected committed command. Same-key retries retain exact payloads.
Hidden-tab destinations must become visible. Reused values/labels must not widen
the server-authorized population or outlive identity/rights changes.

## Progress

- Completed October 16: 911 frontend regressions in 195 files; ten isolated Edge
  browser cases; TypeScript and isolated production build passed. Current evidence,
  earlier corrected failures, user approval and remaining acceptance/performance
  boundaries are in the [resolution record](../../delivery/quality-reviews/2026-10-16-frontend-remediation.md).
  No operating financial writes, migrations, permissions, commits or pushes.

- Starting baseline: strategy-specific FRONTEND-001 guard already implemented;
  broader rollout and the other nine findings remain open. Prior frontend suite
  has two documented import-timeout flakes. Worktree preference and sequential
  execution follow the user's existing instructions; no further plan approval.
