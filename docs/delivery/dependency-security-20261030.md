# Dependency security remediation — 30 October 2026

**Scope:** Security-review point 2, authorised by the user.  
**Status:** Implemented and locally verified; remote execution awaits push.  
**Branch:** `codex/pnl-ops-review`, existing working checkout.

The initial live workspace audit reported 16 JavaScript advisories: three
critical, five high, seven moderate and one low. OSV identified two affected
Python packages, Certifi and pytest. Critical advisory severity does not imply
that every affected optional framework feature is used by this application.

## Change and rationale

- Raise Next.js to the patched 16.4 family and update both Vitest consumers to
  the patched 4.1 family. Re-resolve the actual image-processing, source-map and
  mocker dependencies, preserving application features.
- Update the existing `@redocly/openapi-core` override to 1.34.22, whose declared
  js-yaml dependency is 4.3.2. Keep the current OpenAPI generator version and verify
  generated output parity.
- Raise pytest's allowed major to 9 with a 9.0.3 security floor and lock 9.0.3,
  the bounded patch target. Add a Certifi floor of 2026.10.19 and resolve the
  current 2026.10.23 bundle. The two advisory feeds differ on the earliest patched
  Certifi date; the selected floor and installed release exceed both dates.
- Preserve all other Python version pins and regenerate hashes with pip-tools.
- Add read-only, fail-closed PR/main/manual/weekly dependency jobs. They use the
  complete locks, including development tools, without ignored advisories.
  [Maintainer workflow](../platform/dependency-security.md).

No financial formulas, product handlers, identity rules, permissions, operating
records or database migrations are changed. The separate secret-scanner defect
is security-review point 4 and remains outside this delivery.

## Verification

Resolved versions on 30 October 2026:

| Package | Installed/locked version |
| --- | --- |
| Next.js | 16.4.3 |
| Vitest / mocker | 4.1.12 |
| sharp | 0.35.5 |
| source-map-js | 1.2.2 |
| js-yaml | 4.3.2 |
| Redocly OpenAPI core | 1.34.22 |
| Certifi | 2026.10.23 |
| pytest | 9.0.3 |

- Complete `pnpm audit --audit-level=low`: zero advisory findings at every
  severity, including development dependencies.
- Hashed Python lock installation and `pip check`: passed. Only Certifi and
  pytest changed version; the other 44 pins are unchanged.
- `pip-audit` 2.10.1, PyPI service, `--require-hashes`: no known vulnerabilities.
  Independent OSV batch scan checked all 46 lock entries, including package names
  carrying extras: 46 responses, zero findings. The initial pip-audit OSV request
  failed with an SSL EOF; it was not counted as a successful audit. No TLS
  verification was disabled. CI uses PyPI's hash-validating audit mode.
- Python: 138 focused offline tests and 38 disposable-database tests passed on
  pytest 9.0.3. The database slice covers cash booking, file imports, economic P&L,
  self-publication storage and transactional request audit. No full Python suite
  was run. One existing Starlette test-client deprecation warning remains.
- Frontend: all 1,077 tests across 220 files passed with `--maxWorkers=2`.
  The first unrestricted run overlapped the build/backend checks: 1,061 passed
  and 16 failed, predominantly five-second timeouts with follow-on mock failures.
  The complete bounded rerun passed without changing assertions, timeouts or
  product behaviour. API-contract tests: three passed.
- Both TypeScript checks and the Next.js optimized production build passed using
  Node 24.19.0. Build output was isolated in `.next-dependency-security`; temporary
  generated configuration edits were removed afterwards.
- OpenAPI export check passed. Regenerating TypeScript with the unchanged
  generator and patched transitive dependencies produced identical bytes:
  SHA-256 `6D1B3837722D1DC380C97C03C437CD70791E5C1DA778026604DFFD595F3C6EDC`.
- Three isolated Edge/Playwright checks passed: group validation, import-source
  validation and the real Next stale-context guard. Synthetic browser servers
  used ports 3118/3119 with no financial API/database connection. This is bounded
  compatibility evidence, not all-page visual or accessibility acceptance.
- Scoped documentation links, workflow YAML/immutable actions and resolved
  transitive-version checks passed. The working-tree whitespace check passed.

The separate dependency workflow runs on PRs, main pushes, manual dispatch and
Mondays at 06:23 UTC; audit/service errors fail the jobs. No advisories are
ignored. No GitHub execution, commit, push, migration or operating restart is
claimed. The surrounding checkout contains earlier unrelated work, which is
preserved. Production identity and the other security-review findings remain
outside this point-2 fix.

## Primary guidance checked

- [Next.js image-processing advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw):
  patched Next.js 16.4.1 / sharp 0.35.5 or later; the RCE scenario is conditional
  on the affected Linux image-processing path.
- [Next.js development-server disclosure](https://github.com/vercel/next.js/security/advisories/GHSA-39w2-rjm5-chcv).
- [Certifi trust-root advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2).
- [pytest 9.0.3 release](https://github.com/pytest-dev/pytest/releases/tag/9.0.3):
  insecure temporary-directory handling fix, CVE-2025-71176.
- [PyPA audit-action source](https://github.com/pypa/gh-action-pip-audit/tree/1220774d901786e6f652ae159f7b6bc8fea6d266):
  verified immutable v1.1.0 commit and supported input/failure semantics.
- [pip-tools](https://pip-tools.pypa.io/en/latest/): targeted upgrades with
  preserved existing constraints and generated hashes.

See the [implementation plan](../superpowers/plans/2026-10-30-dependency-security.md).
