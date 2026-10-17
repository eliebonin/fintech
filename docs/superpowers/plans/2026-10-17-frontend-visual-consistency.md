# Frontend visual consistency implementation plan

**Goal:** Homogeneous shared presentation and reduced page density without changing
financial, booking, access or evidence behavior.

**Spec:** [Visual consistency review](../specs/2026-10-17-frontend-visual-consistency.md).
**Architecture:** Native CSS + existing MUI, small shared tokens/navigation primitives;
presentation-only changes to pricing policy and structured-product sections.
**Execution:** Sequential in the current feature checkout; preserve existing changes.

## Global constraints and review focus

- No backend/schema/operating changes, service restart, dependency install or push.
- Preserve mounted form state, native validation and exact retained mutation intent.
- Keep essential warnings/errors visible and all existing audit/evidence reachable.
- Native fallback specificity must not override existing primary/destructive styles.
- Do not globally realign financial columns or impose content/row caps.
- Test keyboard focus, 390px reflow, read-only users, unsaved drafts and tab switching.

## Task 1 — Shared presentation

- [x] Add failing visual/browser assertions for unstyled native controls, narrow
  organisation table containment and shared-native/MUI defaults.
- [x] Add `src/lib/workspace-theme.ts` and `workspace-presentation.ts` (palette/tokens/theme), wire providers/root,
  update existing native foundations and organisation styles, preserve specialized
  classes and exact value displays.
- [x] Verify focus/disabled/compact variants and desktop/mobile visual samples.

## Task 2 — Related-task tabs and policy density

- [x] Add failing unit/browser tests for controlled tabs, keyboard activation and
  retained form values; create `src/components/workspace-navigation.tsx` and its CSS.
- [x] Wrap pricing-policy Configuration/Preview/Reference without touching handlers,
  rule construction, compatibility acknowledgement or requests. Keep saved picker
  and notices outside panels; panels remain mounted.
- [x] Test actual policy component read/manage variants, editable draft retention,
  saved-version preview selection and full retained evidence availability.

## Task 3 — Long-form orientation and shell navigation

- [x] Add failing focus/navigation tests, then implement shared outline and skip
  link in the same small `workspace-navigation.tsx` module.
- [x] Add stable heading IDs and outline in structured creation, no hidden fields
  or rewritten contract logic. Integrate skip link/target in existing shell without
  changing permission conditions. Preserve native hash/navigation behavior.
- [x] Verify keyboard focus, target availability and long-form warnings/controls.

## Task 4 — Regression, visual review and documentation

- [x] Run full frontend unit suite, browser suite, typecheck and production build.
- [x] Review final scoped changes for hidden controls, cascade regressions, focus,
  event handlers and domain boundaries. Fix evidenced issues with regression tests.
- [x] Update delivery, F49 and frontend reference with inventory, research, fixes,
  measured verification and explicit remaining visual/assistive acceptance limits.

## Ledger

- Inventory: 50 page entry points, 146 production JSX modules, nine stylesheets.
- Decision: preserve two existing render families, no UI-framework migration.
- Decision: price policy uses task tabs; contractual creation uses outline links,
  not collapsed required fields. Neither changes the payload/valuation methodology.
- Task 1 → Task 2/3: shared tokens/defaults must remain compatible with both existing
  native classes and MUI. Browser fixtures render actual components with fake data.
- No commits or subagents: preserve the user's current checkout and sequential work.
- Presentation tokens are pure and server-safe; MUI theme construction stays in
  its own module. Next's cache provider stays in the app, not the Vite fixture.
- Browser fixtures now load the real global/native/organisation cascade and MUI
  theme/CssBaseline. Static HTML does not expose streamed Next/MUI cache CSS;
  computed-style browser assertions are the visual evidence instead.
- Visual follow-up reproduced grid row stretching on short organisation pages;
  `align-content:start` fixes it without constraining long content or row counts.
- Policy identity controls also stretched to 86.8px beside explanatory copy;
  a failing real-browser height assertion led to scoped top alignment. All 20
  isolated browser cases pass after that correction. Unit suite: 932/199 files;
  types and production build pass. No independent agent review was used, honoring
  the user's sequential-work instruction; scoped inline review is not an external
  audit. [Delivery](../../delivery/quality-reviews/2026-10-17-frontend-visual-consistency.md).
