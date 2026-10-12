# Tenant access administration progress

Plan: `docs/superpowers/plans/2026-10-09-tenant-access-administration.md`.

User approved design and implementation in conversation; sequential/current-checkout preferences retained. No repeated approval handoff. Existing branch `codex/enriched-trade-booking` is dirty with prior project work, which must remain untouched except scoped extensions.

Ruling: use the current checkout rather than creating a worktree — previously requested current-checkout execution and running local app depend on uncommitted work; a fresh worktree would omit it.
Ruling: no automatic commits or reviewer subagents — direct user instructions override skill defaults; preserve unrelated work and perform a separate self-review.
Ruling: focused suites, not full Python suite — user's established lightweight-first preference; report scope and expand when evidence requires.

Pre-flight: schema actions → management APIs → validated context session → frontend affordances. One fixed catalogue governs both module/action grants and UI payload; unknown actions fail closed. Existing effective-date entitlements require serialized same-day toggling.

Task 1: complete; schema and action resolution verified in isolated migrated DB. Ambiguous active membership history now fails closed.
Task 2: complete; management tests pass, including cross-tenant denial, module toggling, last-admin protection and idempotent seed.
Task 3: complete; validated opaque sessions, recovery, production rejection, private-origin forwarding and real/effective actor evidence verified.
Task 4: complete; all 744 Vitest tests across 160 files, TypeScript and production build pass.
Task 5: activation and HTTP acceptance complete; manual browser signoff pending because automation cannot initialize.

Review: operations queue filters denied valuation items and counts before pagination; relative browser requests must never receive upstream session credentials. Regression tests recorded RED before changes.

Final review: self-review (user requested no subagents). Fixed correction-versus-booking gates, delegated configuration/calendar/valuation permission checks, suspended-group removal, overlapping membership ambiguity, fixed-user legacy navigation and recovery. Regression tests observed RED then GREEN. Existing role-label fixtures were updated to explicit group grants; no implicit non-admin privilege was restored to satisfy tests.

Verification:

- `logs/tenant-access-backend-signoff.log`: 124 passed, 9 existing dependency/fixture deprecation warnings; access, reference/booking controls, all-product corrections and the two corrected calendar/FX regressions. Disposable DB only.
- Earlier wider check: 167 passed / 2 failed; both failures were old role-grant expectations, corrected and passed in the final 124-test run. Do not report the original wider run as green.
- `logs/tenant-access-ui-signoff.log`: 160 files / 744 tests passed.
- `logs/tenant-access-typecheck-signoff.log`: TypeScript passed.
- `logs/tenant-access-build-signoff.log`: production build passed using isolated `.next-access-build`.
- `logs/tenant-access-http-signoff.log`: all 12 seeded personas passed real BFF/API context/authority checks, including wrong-origin and foreign-user switch denial, unchanged cookie on failed switch, admin/non-admin controls, read-only write denial, cross-tenant trade 404, stale submission 409 and reset. Business data not mutated.
- Operating DB: head 82, 3 tenants / 9 groups; 11 trades / 7 strategies unchanged. Registry backed up, seed repeated twice; API on 8000 and UI on 3000 restarted.

Browser blocker: `cua.getState()` failed at initialization with `node_repl kernel exited unexpectedly` and `windows sandbox failed: helper_unknown_error: setup refresh had errors`. No browser interaction claim is made.

UX follow-up completed October 9: profile, Users/Groups and context picker refined; new-group creation now closes/unmounts its form on success, resolving the retained-values issue. Role changes use explicit save; role/group saves keep other drafts open. Search, accessible tab navigation, module-grouped grants, confirmation and status feedback verified. Final frontend evidence: 163 files / 759 tests, TypeScript and isolated production build passed. Live HTTP rendering/access checks passed for all three admins and a reader; browser visual signoff remains blocked by the automation sandbox. See the UX refinement section in the delivery record for sources, scope and limits.

Registry queries and supplemental audit transport still require production scalability/durability hardening, documented as outside this local alpha.

Delivery record: `docs/delivery/tenant-access-administration.md`. No commit, push or unrelated data cleanup performed.

Platform update extension: migration 83 applied, API restarted, platform-only profile/contact editing and confirmed suspension/reactivation implemented. UUID/code remain immutable; stale writes return 409; before/after changes audited. 41 backend tests, 764 frontend tests, both TypeScript checks, OpenAPI freshness and production build passed. Live BFF denial/validation/conflict checks passed with tenant profiles unchanged. An unsafe old workspace test ignored DATABASE_URL and ran against the operating DB; fixture now rejects that DB. Its single test-created platform account/grant was backed up and removed; existing grants were retained. Counts remain 3 tenants / 7 strategies / 11 trades. The delivery record describes the initial failure and demo-seeding limitation explicitly. Browser visual signoff still pending.

## Conditional merge preflight October 12

User authorised merging all work to main and pushing only if safe. Only one feature branch exists; local main is its ancestor, and fetched origin/main is also an ancestor (64 committed changes behind the feature head). Recent implementation remains uncommitted. Generated `.next-*` folders were excluded, leaving source/documentation changes rather than thousands of build artifacts.

Twenty-four legacy test files now use the environment-selected DATABASE_URL instead of the operating database. A pytest SQLAlchemy connection guard rejects `fortem_secm` before network access; its regression was observed RED then GREEN. CI is prepared to use `fortem_isolated_tests_ci`, migrate and seed that disposable database. These safety changes remain uncommitted because merge verification did not pass.

Docker was initially stopped. Docker Desktop and the existing project PostgreSQL container were started; backend tests used the newly created `fortem_isolated_tests_merge_20261012`, not the operating DB. The first backend gate stopped at five failures: 87 passed; full backend signoff was not reached. Failures are `test_alembic_can_generate_offline_sql_for_head` (revision 71 queries a scalar on the offline MockConnection), both tests in `test_api_body_budget.py` (authentication middleware returns 401 before their expected 413), and the first two tests in `test_api_transaction_boundary.py` (500/non-JSON response rather than the expected transaction-boundary behavior). Detailed evidence: `logs/merge-backend-tests.log`. No permission or transaction safeguards were relaxed to turn the tests green.

The initial parallel frontend run had two 5000ms timeouts in the valuation and trade-detail page tests. Serial rerun passed all 764 frontend tests; three contract tests, both TypeScript checks, deterministic OpenAPI check and the production build passed. Logs: `logs/merge-frontend-tests.log`, `logs/merge-frontend-serial.log`, `logs/merge-build.log`. Build-generated type paths were restored to the development configuration afterward.

Decision: not safe to merge yet. No commit, branch merge, branch deletion or push was performed. Main remains unchanged. Resolve the backend failures and complete isolated verification before executing the authorised merge/push.

## Merge remediation and stable-snapshot verification October 12

User authorised fixing the preflight failures, merging and pushing main. A concurrent valuation task was discovered during the diagnostic run; the user confirmed its edits had finished and requested review of its latest files. The final verification therefore includes the retained real-operator review authority, amendment contributor lineage and delegated valuation/cancellation permissions. Work remains sequential, with no reviewer subagents.

Resolved the original failures without weakening permission checks: request context/error handling now wraps body limits and authentication, so oversized bodies are rejected before authority lookup and authentication failures retain safe problem responses. Transaction tests explicitly model the separate authentication and domain transactions. Revision 71 emits PostgreSQL index-validity checks in offline SQL rather than querying an offline mock connection; online validity checks remain intact. Its historical round-trip regression now owns a disposable database instead of downgrading the current schema through forward-only migrations. The valuation migration regression is pinned to its intended historical revision. Two legacy read/isolation fixtures now grant actual group permissions rather than relying on old role labels.

Focused remediation regressions passed before the fresh broad run. The intervening diagnostic broad run was stopped because it predated the concurrent changes; it is not a completed signoff. The final backend run uses the freshly migrated/seeded `fortem_isolated_tests_merge_final_20261012` with the operating-database connection guard enabled. No operating business records are modified by this verification.

Fresh frontend verification on the latest source: 768 tests across 164 files passed serially with a 15-second per-test budget; both TypeScript checks, three API-contract tests and the deterministic OpenAPI freshness check passed. The production build passed in isolated `.next-merge-verification`; generated type paths were restored afterward. The staged Gitleaks scan found no leaks. Backend result and integration outcome will be recorded below when complete. Browser visual acceptance remains a separate documented limitation.

### Completed remediation verification

The 1,544-test backend collection was exercised in partitions rather than repeatedly restarting it. `logs/merge-final-backend.log` stopped at ten failures after 951 passes. `logs/merge-backend-remaining.log` covered the previously unrun files: 580 passes and nine failures, including one repeated metadata failure. These are diagnostic runs, not a single clean full-suite pass. Each identified failure was then reproduced and corrected, with fresh disposable-database regressions covering the changed modules and their neighbors:

- `logs/merge-boundary-catalogue-fixes.log`: 34 passed. Fixed page-filter consistency and verified constant catalogue query cost including current permission/RLS checks. Operator orchestration moved to `apps/market_data_ingestor/index_trading_history.py` and `yahoo_fx_valuation_setup.py`; core/provider packages no longer import the API or provider-specific orchestration across their declared boundaries.
- `logs/merge-catalogue-review-fixes.log`: 8 passed. Market-data catalogue cost remains constant across page sizes, and independent-review refusal correctly uses 403.
- `logs/merge-final-remediation.log`: 82 passed on a fresh owned database. The valuation fixture now restores its shared demo policy when HTTP acceptance commits its synthetic setup; the ordering regression explicitly runs that acceptance before legacy selection/Soft-NAV/source-priority tests. Swap isolation uses a genuinely granted foreign-tenant reader instead of an ungranted legacy membership. Provisioning mocks target configuration authority. All schema columns now retain meaningful comments.
- `logs/merge-final-authority.log`: 61 passed on another fresh owned database. Authentication/action denials use RFC problem responses and request correlation; the local UI error alias remains for compatibility. Access/session/transaction/body-budget and valuation amendment/operator-authority checks remain enforced.
- `logs/merge-final-yahoo-fixes.log`: 18 passed on a fresh owned database. Fixed the duplicate `status` keyword crash after ingestion; output distinguishes source completion from RAW normalization readiness, and uncertified synthetic adjustment anchors remain partial rather than being silently accepted.

No single final clean full-suite rerun is claimed. The complete collection was exercised, all observed failures were addressed and affected suites rerun successfully. This avoids repeating the expensive already-passing unaffected tests. OpenAPI freshness and the final staged secret scan passed again after the backend fixes. Browser visual signoff and production scalability/durability remain outside this merge's acceptance scope.

Integration decision: proceed with the user's explicitly requested commit, fast-forward merge to main and normal push to origin/main. Retain the feature branch as a recovery reference; do not delete branches, force-push, alter operating business data or repeat the full suite merely because the branch name changes. Verify the merged tree is identical to the tested candidate and confirm the remote main SHA after push.
