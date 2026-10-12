# Source catalogue and priorities — implementation ledger

Plan: `docs/superpowers/plans/2026-10-08-market-data-sources-ui.md`.

- Pre-flight: API produces catalogue and priority versions consumed by the frontend; shared priority loader produces frozen ordering consumed by both selection branches.
- Ruling: remain in the user's existing feature checkout, preserve unrelated work, do not create a new checkout or commit without request.
- Ruling: no subagents and no full suite, following the user's explicit instructions; focused integration and UI checks instead.
- Task 1 RED: three isolated catalogue/priority tests fail because the new service is absent.
- Task 1 in progress: additive migration 74, API service, contracts and immutable priority versions.
- Review: mixed reporting/valuation coverage could be misread; added separate purpose-specific coverage summaries and a regression test (RED → GREEN).
- Review: compiler found MUI 9 layout properties no longer accepted directly on Stack; moved them to `sx`; typecheck passed.
- Review: an unordered test query picked an unrelated dated observation in the combined run; the fixture now explicitly selects its canonical test observation. Production selection unchanged.
- Ruling: generated-contract Git cleanliness check compares against committed HEAD, so fails for intentionally uncommitted contracts. OpenAPI export check and byte-identical regeneration verify actual synchronisation instead.
- Browser runtime repeatedly exits during initialisation; do not claim a browser walkthrough. Use read-only HTTP activation checks and document manual UI acceptance as pending.
- Review: as-of tests must not assume Python and PostgreSQL clocks are identical. Use the returned configuration timestamp plus a fixed interval for post-save selection; keep the pre-save cutoff assertion separately.
- Task 1 complete: entitled catalogue, purpose-specific scope, permission checks, idempotency/concurrent edits, platform defaults/private exclusion verified.
- Task 2 complete: same-date ranking, explicit exclusions, semantic eligibility and as-known evidence integrated into both selection branches.
- Task 3 complete: page, BFF, menu, loading/error/read-only states and priority editor implemented. Missing-session BFF regression observed RED and fixed GREEN (401/non-retryable).
- Verification: 66 affected isolated backend tests passed (8 pre-existing seed-loader deprecation warnings); 18 frontend tests passed; typecheck and OpenAPI export check passed; contract regeneration byte-identical.
- Activation: migration 74 applied; API/UI on 8000/3000; operating page/BFF HTTP200; no-session BFF401. No operating priority saves or grant changes made for acceptance.
- Final review: self-review, user explicitly requested sequential/no-subagent work. Scope-by-purpose ambiguity and auth messaging fixed. Minor deferred: batch per-type catalogue/config reads as universe grows.
- Ruling: browser runtime unavailable; finish implementation with explicit pending visual/click-through acceptance, not a claimed browser signoff. Cost: browser-only interaction/layout defects remain possible.
- Delivery record: `docs/delivery/market-data-sources-ui.md`.
- Final live read confirms personal Yahoo has INTERNAL_REPORTING only. Regression test RED → GREEN ensures reporting-only scope is labelled "No valuation entitlement", not conflated with non-display activity rights.
