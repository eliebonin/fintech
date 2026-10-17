# Pre-reorganisation documentation archive

**Status:** Historical preservation record with recorded editorial anonymisation  
**Content type:** Archive  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-09-10

This directory records the Markdown corpus from immediately before the
documentation-information-architecture migration. On 17 October 2026, the user
explicitly requested removal of former operator names throughout the repository,
including these archived copies. The original Git history remains available.

- `source/` contains copies at their original relative paths; some are now editorially anonymised.
- `manifest.md` retains each original SHA-256 and separately records the current copy's SHA-256, classification and canonical documentation entry point.
- The snapshot excludes instruction files named `AGENTS.md` and `CLAUDE.md`, and excludes files already under `docs/archive/`.

The archive is historical evidence, not the current source of truth. Do not add new authored documentation here or amend archived files. Update canonical documentation under `docs/` and use the manifest to trace its source material.

To verify current copies, calculate SHA-256 and compare with `Current copy SHA-256`.
The distinct original hash identifies the pre-edit snapshot in Git history; it is
not a claim that an anonymised copy remains byte-identical. Historical dates and
delivery claims have not been updated to imply new implementation evidence.
