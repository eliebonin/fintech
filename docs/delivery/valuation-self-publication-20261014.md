# Controlled valuation self-publication

**Status:** Implemented; default disabled, local migration applied  
**Content type:** Delivery / governance decision  
**Owner:** Valuation and tenant access administration  
**Last reviewed:** 2026-10-14

## Agreed purpose

Support a one-person operations team and temporary cover when another reviewer
is unavailable. Independent review remains the default; explicit self-publication
is a supported continuity mode, not a hidden override. It waives only the final
publication independence check, not financial validation or amendment approval.

## Configuration and authority

1. In **Tenant profile → People & access → Groups**, the tenant administrator
   configures **Valuation self-publication**. Opt-in is disabled by default.
   A mandatory reason and confirmation accompany every change. Leave expiry blank
   for standing permission or specify an inclusive UTC end date for temporary cover.
2. Explicitly grant **Self-publish valuations** (`VALUATION_SELF_PUBLISH`) and
   **Review valuations** (`VALUATION_REVIEW`) through active groups with appropriate
   strategy scopes. The new action is subject to the VALUATION module entitlement.
   Policy opt-in does not add any group grants; admin/legacy Ops bootstrap and seeds
   do not automatically grant the new action.
3. Each self-publication requires the active policy, strategy-scoped review and
   self-publication rights, complete contributor lineage, a reason and explicit
   acknowledgement. Both the selected subject and the **real operator** must hold
   the relevant tenant/strategy permissions when they differ.

The local context selector is not a substitute for real-operator authority. A
platform administrator impersonating a tenant user cannot borrow that user's
self-publication grant: the real operator needs explicit tenant membership and
review/self-publication grants too. This delivery does not automatically provision
that membership or introduce a general impersonation-authority exception.

Temporary expiry is **tenant opt-in expiry**, not per-user/group expiry. Strategy
limits remain group-scoped; an administrator can revoke grants or disable the
policy earlier. Per-user expiring exception grants are not implemented here.

## Publication and evidence

- Existing `/publish` still requires independent real-operator review. A separate
  `/self-publish` endpoint requires `confirmSelfPublication=true`; ordinary publish
  rejects override fields. The BFF allowlists the explicit endpoint and propagates
  trusted session context.
- The storage layer rechecks exception authority rather than trusting an API/UI
  boolean. It serializes publication with policy configuration on the tenant row;
  the existing strategy/date and input-revision publication locks remain.
- Pending amendments, blocking validations, current accrued-input revisions,
  financial/rounding reconciliation, source DISPLAY permissions, stale official
  population and stage status checks remain in place. Component amendment approval
  continues to require independent review; SELF_PUBLISH does not replace REVIEW.
- Publication retains a `SELF_PUBLISHED` review event and a `PUBLISHED` operational
  event containing `reviewMode=SELF_REVIEWED`, permission, policy revision/expiry,
  contributor operators, selected reviewer, real operator and reason. The financial
  summary/attribution evidence is not rewritten to add the marker. Normal new
  publications record `reviewMode=INDEPENDENT`; older unmarked records are not
  retroactively presented as proven independent.
- Result detail, History/Results report rows and operational status display
  **Completed · Published · Self-reviewed** where that retained evidence exists.
  The existing PUBLISHED batch state is retained, not replaced by an ad hoc status.

## Frontend behavior

The existing prominent publication control uses server-provided exception
eligibility. Authorised contributors see **Publish without independent review**,
a required acknowledgement and a mandatory self-publication reason. Without
authority it stays disabled and explains the blocker. Current real-operator checks
also prevent a switched test identity from falsely appearing independent.
Publication remains a confirmation workflow; selecting a button is not approval.

Tenant policy configuration uses context-pinned BFF writes, expected revision and
append-only governance rows. Stale saves are rejected. A successful save explicitly
states that no user permissions were added. Tenant administration and operational
review authority remain separate.

## Schema, activation and verification

- Migration **87** adds `nav.valuation_publication_policy`, with append-only
  revisions, actor/reason/time, enablement and optional UTC expiry. A database trigger
  rejects updates/deletes; subsequent configuration appends a revision. Missing
  policy means disabled. No records or grants are seeded by the migration.
- Migration applied to the verified operating `platform_secm` database; Alembic
  reports `20261014_87`. API restarted after exact-process verification;
  logs `logs/api-self-publication-20261014.out.log` / `.err.log`. Frontend hot reload.
- **61 affected Python tests passed** on an owned disposable database, including
  policy default/expiry, no implicit admin grant, real-operator impersonation denial,
  self-publication provenance, pending-amendment blocking, policy confirmation/stale
  revision, immutable configuration, transport acknowledgement and existing
  independent storage/amendment/strategy-scope behavior. The test database was
  removed by the isolated runner; no integration tests used operating data.
- **82 affected frontend tests passed** across 15 files; type checking,
  `pnpm contract:check` and `git diff --check` passed. Includes publication visibility/acknowledgement,
  self-reviewed labels, BFF allowlisting, governance form requirements and existing
  access/valuation interactions. OpenAPI and generated TypeScript were refreshed;
  no commit/push or full application regression run was performed.
- Live browser inspected policy revision 0 / Independent review required, expiry
  and reason/confirmation controls, and the new **unchecked** group permission.
  The existing group editor was cancelled without saving. No policy enabled, grants
  changed or financial result published against operating data. Authorised financial
  publication was exercised only in disposable storage tests, not a live browser.

## Limits and governance references

Independent retrospective review/attestation of an already self-published result
is not implemented. Per-user expiry, production identity-provider acceptance and
regulated fund-NAV governance assessment remain separate. This continuity feature
does not establish legal compliance or complete NAV capability.

[NIST separation-of-duty guidance](https://csrc.nist.gov/glossary/term/separation_of_duty)
and [ESMA asset-valuation review](https://www.esma.europa.eu/sites/default/files/2023-05/ESMA34-45-1802_2022_CSA_on_Asset_Valuation_-_Final_Report.pdf),
checked 14 October 2026, inform preserving explicit authority, provenance and
independence as the default. The exception vocabulary/configuration is a project
choice for this personal alpha, not a prescribed regulatory schema.

Implementation: [exception authority/policy](../../valuation/self_publication.py),
[storage](../../valuation/storage.py), [migration](../../alembic/versions/20261014_87_self_publication_policy.py),
[API](../../apps/reference_api/valuation_routes.py), [access management](../../apps/reference_api/access_routes.py),
[publication UI](../../apps/ops-console/src/features/valuation/publication-action.tsx),
[tenant settings](../../apps/ops-console/src/components/valuation-publication-settings.tsx),
[storage regressions](../../tests/test_self_publication_storage.py),
[API regressions](../../tests/test_self_publication_api.py).
