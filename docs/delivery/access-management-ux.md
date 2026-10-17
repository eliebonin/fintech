# Access-management UX refinement

**Status:** Implemented UI refinement, authorization unchanged  
**Reviewed:** 2026-10-13  
**Capabilities:** F02 / F05

## Intent and navigation

Make the strategy-scope slice understandable without requiring administrators to
interpret action codes or open every group. Start at Tenant profile → Manage users
and groups, or `/tenant-profile/access`.

- **Users:** memberships, roles and group assignments. Separate save boundaries
  and suspension confirmation remain intact.
- **Groups:** permission counts and explicit strategy-scope summaries in the
  register. ALL means current **and future** strategies; empty SELECTED is visibly
  distinguished from broad access. Missing legacy scope is shown as unavailable,
  never guessed as ALL.
- **Strategy access:** choose a strategy, search users and filter users with/without
  access. Action names remain visible; supplementary source-group evidence is in
  “Why this access?”. A link opens the full user-access explanation.

Group editing follows four labelled sections: identity, permissions, strategy scope,
then review. Permissions have task-oriented labels and short descriptions. Scope
copy distinguishes strategy actions from tenant-wide configuration and creation.
Searching strategies retains selections outside the search results. The review
shows the captured group configuration, current gains/losses and future-strategy
warning; nothing is saved until confirmation. Editing returns to the retained draft
and requires another preview. Focus moves to the review heading and back to the
editor heading. Backend expected-version/fingerprint/context checks are unchanged.

## Research and design rationale

Primary sources checked on 2026-10-13:

- [GOV.UK Check answers](https://design-system.service.gov.uk/patterns/check-answers/)
  supports a distinct review before submission and returning to edit information.
  Applied to the group configuration summary and explicit confirmation.
- [GOV.UK Details](https://design-system.service.gov.uk/components/details/)
  recommends disclosure for secondary material, not information most users need.
  Allowed actions, denied state and broad-scope warnings stay visible; explanatory
  source groups are expandable.
- [Carbon data tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines)
  supports clear table titles, search/filter toolbars and supplementary expansion.
  Applied to the matrix controls and evidence display.

Numbered editor sections, action chips and keeping the current three tabs are our
bounded design choices, not regulatory or universal industry requirements. No new
UI dependency or authorization model was introduced.

## Evidence and remaining limits

Focused UI verification covers rendering, actual matrix filter/switch handlers,
preview-before-save, captured revision/hash confirmation and edit invalidation,
plus existing editor/context regressions. TypeScript and isolated production build
are checked separately from browser acceptance. See the final verification record
below for current results.

This is not a permission-policy rewrite. No operating grants are changed to test
the UI. Matrix search filters the already-fetched tenant matrix; it does **not**
fix backend users × strategies scaling or add server pagination. Preview still is
not independent access-change approval. Large tenant/small-screen usability and
assistive-technology acceptance remain separate from the local desktop walkthrough.

Related: [scope delivery and limits](strategy-access-scopes.md),
[capability record](../product/features/access-and-strategies.md#f02-users-groups-and-delegated-actions).

### Final verification

- **34 focused frontend tests across nine files passed**, including new register
  scope visibility, expandable evidence, matrix filtering/switching and existing
  editor/context checks. New review/register/disclosure expectations were observed
  failing before implementation. Filter-handler regressions were added afterward.
- TypeScript passed; isolated Next.js production build passed. Its generated
  config additions were restored to the operating development settings.
- Desktop in-app browser checked Groups → Edit Traders → unchanged preview →
  Edit configuration → Cancel → Strategy access. Review received keyboard focus,
  the draft retained its name, search reduced four users to the trader, and the
  disclosure showed the Traders source for each granted action. The no-access
  filter displayed clear no-match feedback; filters were reset for user review.
- Browser testing created a local test context and two non-persisting previews;
  no group confirmation, operating permission changes or financial writes.
  No full Python suite was run for this presentation-only change.
