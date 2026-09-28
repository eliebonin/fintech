# Pre-reorganisation documentation archive

**Status:** Immutable preservation record  
**Content type:** Archive  
**Owner:** Architecture and platform team  
**Last reviewed:** 2026-09-10

This directory preserves the Markdown corpus as it existed immediately before the documentation-information-architecture migration.

- `source/` contains byte-preserved copies at their original relative paths.
- `manifest.md` records every archived source file, its SHA-256 hash, classification, and canonical documentation entry point.
- The snapshot excludes instruction files named `AGENTS.md` and `CLAUDE.md`, and excludes files already under `docs/archive/`.

The archive is historical evidence, not the current source of truth. Do not add new authored documentation here or amend archived files. Update canonical documentation under `docs/` and use the manifest to trace its source material.

To verify preservation, calculate the SHA-256 of each archived `source/` copy and compare it with the manifest value. A live source may deliberately differ after the migration because a non-destructive compatibility notice or canonical-navigation link has been added; the archive hash remains the proof of its pre-migration content.
