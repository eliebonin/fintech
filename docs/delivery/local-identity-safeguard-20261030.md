# Local identity safeguard — 30 October 2026

**Scope:** User-authorised security-review point 1 containment.  
**Status:** Implemented and locally verified; production authentication deferred.  
**Branch:** Existing `codex/pnl-ops-review`; unrelated changes preserved.

Ordinary protected API requests now require a verified stored session. Optional
identity headers are consistency checks. Bootstrap requires a random server-only
capability and the configured operator. Non-local/implicit startup and missing
configuration fail closed. The context selector and current authority/audit checks
remain; demo-user/signed-tenant authentication is removed. Setup writes matching
ignored configuration without printing secrets. Optimised local builds are
distinguished from production deployments.

No production identity provider, migration, permission grant, financial formula
change or operating booking/publication is included. Production identity remains
BACKEND-001 and a deployment blocker.

## Verification

Initial regressions reproduced unsafe behaviour: 13 of 14 API boundary/startup
cases and all five BFF cases failed. Final focused backend coverage adds a UUID
equivalence case; 27 offline cases passed. The final session/transport/BFF slice
passed 23 tests, including refusing credential redirects.

- Affected API/session regression: 344 cases in 39 files. The first run passed
  328; 16 failures exposed old header-auth assumptions, separate uncommitted
  connection fixtures, router-only apps and missing operator credentials. All 16
  passed focused reruns after fixture corrections. A temporary fixture import
  name collision was corrected; no application authentication bypass was added.
- Final stable-snapshot database slice: 20 passed, covering real authentication,
  session authority, transactional audit, cash-booking replay and rollback. All
  databases used the owned disposable runner and were removed afterwards.
- The independent valuation acceptance fixture also restored its pricing policy
  before calculation. Its lifetime now spans acceptance, preserving the exact
  financial assertions and price-basis guard. It uses explicitly granted review
  rights and two separately authenticated synthetic operators. Calculation,
  concurrent retry, amendment, rejection of same-operator identity switching,
  independent publication and evidence revocation/redaction pass. Expected P&L
  remains `109.877`, amended/published `99.877`.
- Frontend regression: 1,080 of 1,081 passed in the broad run; the sole five-second
  timeout passed with all eight cases in its file when rerun alone. Assertions
  and timeouts were unchanged. Final credential-transport coverage passed after
  redirect hardening. Types and OpenAPI contract checks passed.
- Three isolated browser cases passed: validation/console integrity and the real
  Next stale-context guard. Optimised builds use a separate `.next-local-identity`
  output and two build workers. No production identity sign-off follows from this.
  The final build passed after credential-redirect hardening; generated temporary
  config/type-path edits were removed afterwards.
- Private configuration was generated without printing the key; Git ignores both
  files. The key was absent from tracked/unignored source and all 89 public build
  files in the inspected build. Provider-neutrality/archive checks passed.
- Read-only local activation check found zero unexpired/unrevoked operating local
  sessions. Operating services were not listening on their usual ports when
  checked; no operating session revocation, permission grant, booking or valuation
  was performed. No migration is needed. Launchers load the new private settings.

The full Python suite was intentionally not run. Existing SQLAlchemy/Starlette
deprecation warnings remain. Scope is local containment and compatibility, not
an exhaustive security, scale, browser or production-authentication certification.

The [maintained configuration/limits reference](../platform/local-identity-safeguard.md)
records primary guidance, local credentials, bootstrap scope and deferred work.
This delivery does not claim production authentication certification.
