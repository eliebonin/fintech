# Strategy access scopes implementation plan

**Goal:** Bind group actions to strategy scope without broadening permissions through unrelated groups.
**Architecture:** Shared SQL scope predicate and action check, service-level write checks before replay,
request-bound actor for read filtering, scoped transport checks for derived IDs. Explicit ALL/SELECTED
group scope; subscription/membership/action remain independent upper bounds.
**Spec:** Approved research/design in this conversation (2026-10-13); sources below.
**Execution:** Sequential native, focused tests first; preserve unrelated changes. No additional approval gate.

## Tasks and interfaces

- [x] `security_master_schema/strategy_access.py`: `strategy_predicate(c,tenant,actor,action,column)`
  and `require_strategy_action(c,tenant,actor,action,strategy)`; group scope ALL or SELECTED, additive
  only within matching action grants. Pure/DB tests: unrelated broad reader never widens booking;
  empty selection denies; foreign IDs denied; suspended groups and immediate revocation.
- [x] Migration 85: group scope/version and tenant-scoped group/strategy associations, existing groups
  explicitly ALL; STRATEGY_CREATE split from WRITE for existing grant holders. Seeds preserve edits.
- [x] Admin group save/preview/matrix: atomic versioned actions+scope, preview gains/losses per user
  and strategy; audit changes; safe stale rejection. No direct user exceptions or deny rules.
- [x] Enforce strategy/trade/valuation direct IDs, lists/counts/options and derived evidence. Preserve
  object-level checks before booking/correction replay; constrain queries before pagination.
- [x] Strategy creation: separate permission, atomic chosen-group initial scope; ALL groups include
  future strategies; SELECTED groups need explicit assignment. No automatic creator ownership.
- [x] UI group scopes, impact confirmation, access matrix and initial strategy access. Focused UI,
  types/contracts, isolated backend regressions, then local migration/restart and non-mutating checks.
- [x] md-document reconciliation of root AGENTS/KNOWLEDGE/FIX for this reviewed scope, maintained
  capability register/map and delivery evidence. No exhaustive-code/production claim.

## Review focus

Check action/scope cross-product mistakes, restricted direct UUIDs/derived batches, empty scopes,
late revocation/idempotent replays, counts leaking denied rows, strategy creation with chosen groups,
optimistic version conflicts and preserved existing access. Metadata configuration may show strategy
names to ACCESS_MANAGE without granting financial-data reads. Tenant-wide instruments/licences
stay outside strategy scopes. Existing independent review and lifecycle controls remain enforced.

## Research basis

- [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP output filtering](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Decisions_And_Output_Handling_Cheat_Sheet.html)
- [OWASP service-level patterns](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Patterns_Cheat_Sheet.html)
- [Microsoft action/scope assignments](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)

## Execution record

Completed sequentially. 110 broader focused backend regressions passed, followed
by 57 access/backend checks after audit refinements. 42 frontend tests across 11
files, TypeScript and isolated production build passed. Contracts and local doc
links checked. No full Python suite or independent reviewer used.

Ruling: unknown legacy resolution context cannot be treated as shared; migration
recovers only known strategy-specific policy context and otherwise restricts reads
to an appropriate ALL grant. Cost: some restricted users need fresh evidence.
Ruling: non-admin creators can initialize access only through active groups they
belong to; admins can choose any active tenant group. No implicit creator ownership.
Ruling: UI preview is not independent approval. Authorized API updates require
group revision, and check the access-state fingerprint when supplied.
Ruling: use existing feature checkout and self-review, preserving unrelated files;
no commit/merge/push. Current authority model is local alpha, not production identity.

Migration 85 applied locally; API restarted. All 13 existing persona permission
sets preserved plus the creation split; 12 existing groups retain ALL. Trades 11,
strategies seven unchanged. Live BFF matrix/unchanged-preview/page checks passed;
temporary context revoked. Interactive browser acceptance remains unclaimed.
