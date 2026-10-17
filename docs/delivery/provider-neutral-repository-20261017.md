# Provider-neutral repository

**Status:** Implemented and locally verified; existing installation names retained  
**Recorded:** 17 October 2026

## Intent and scope

Current tracked source, tests, sample configuration, fixtures and documentation
use neutral platform terminology rather than a particular operator's name.
Archived documents are included by explicit request: this is editorial
anonymisation, not a change to their dates, delivery claims or evidence limits.
Git history has not been rewritten. Ignored local configuration, existing
database values and build/log/dependency outputs are not repository source.

## Compatibility boundaries

- Demo dictionary keys use `platform_*`; the associated UUIDs are unchanged.
  New fixtures use neutral labels/codes. Rerunning loaders preserves existing
  rows and approved versions; it is not a database rebranding operation.
- Browser documents and their mutation helper use `platform-page-context`.
  The fingerprint, server-side validation and actual authority checks are
  unchanged. Reload old tabs after deploying; missing context remains rejected.
- New problem-detail types use `https://api.platform.local/problems`.
  Machine-readable error codes and status codes remain stable; consumers should
  not hard-code the former illustrative host.
- New correction/delivery evidence has neutral source labels. Existing source
  labels, payloads, hashes and event rows are not rewritten. Idempotency still
  resolves through the unchanged tenant/endpoint/key record, not the label.
- Historical migration revision IDs and schema structure are unchanged. Their
  descriptive comments use neutral wording. No operating migration is required
  for this source cleanup, and existing database comments are not rewritten.
- Legacy implementation references in documentation describe inspiration, not
  an importable dependency or a requirement for another local repository.

## Fresh local installation

Default database/user: `platform_secm` / `platform`. Default container:
`platform-postgres`. Default named volume:
`platform_security_master_postgres`. The sample password is local-only.

See [sample environment](../../.env.example). API and ingestor honour
`DATABASE_URL`. Docker Compose permits explicit container, volume, database,
user and password overrides. Do not use development defaults for production.

## Existing local installation: retain data first

This change does not rename or recreate the running PostgreSQL database,
container, user or volume. Do not run a fresh default Compose configuration
against an existing workspace and mistake an empty new volume for lost data.

1. Retain the current database service and its volume. Do not run `down -v`.
2. Keep its real connection string in an exported `DATABASE_URL`, outside
   versioned source. Set `LOCAL_WORKSPACE_DATABASE` to its actual database name
   for local-only seed/import commands; local environment/host/port restrictions
   still apply. Setting a connection string alone does not authorize a new target.
3. If later managing that same service through Compose, explicitly map
   `POSTGRES_CONTAINER_NAME`, `POSTGRES_VOLUME_NAME`, `POSTGRES_DB`,
   `POSTGRES_USER` and `POSTGRES_PASSWORD` to the existing installation. Verify
   the resolved names and existing volume before starting anything.
4. Renaming the database/user/container or moving a volume is a separate,
   backup-first operating transition. It was not performed here.

Compose reads a local `.env`; Python entry points do not automatically load it.
Export the connection setting in the shell/service launching Python.

## Verification policy

`tests/test_repository_neutrality.py` checks all tracked and non-ignored new
files, including archived documents and filenames. Its scan rule uses character
codes solely so the policy does not contain its own forbidden sequence. No
production alias or encoded compatibility label is introduced.

Tests use a uniquely owned neutral disposable database. An existing service's
credentials can be supplied with `TEST_DATABASE_ADMIN_URL`; the runner connects
to the PostgreSQL administration database to create/drop only its generated
database. It does not migrate, seed or query the operating application database.
The pytest guard accepts known disposable UUID names, the explicit CI fixture,
and the administration database; other application database names are rejected.

## Results

- Current source/documentation/filename scan: no retired operator-name matches.
- Offline naming, archive integrity, deployment configuration and database guard
  regressions: **19 passed**. The guard's added fixture-family compatibility
  check was observed failing before its fix, then passing.
- Selected disposable-database backend checks: **101 passed**, 919.11 seconds.
  Includes fixture reload/identity preservation, forward-only migration history,
  access management, problem details, correction concurrency/idempotent replay,
  FX delivery and mocked-provider ingestion. No real provider acquisition ran.
- Full frontend unit suite: **957 passed in 200 files**, 177.90 seconds.
- Isolated browser acceptance: **21 passed**, including the real Next context
  guard rejecting an old tab after an actor-cookie switch. The first launch
  could not find bundled Chromium; the completed run used installed Chrome
  through `PLAYWRIGHT_CHANNEL=chrome` (3.5 minutes).
- Frontend typecheck, OpenAPI freshness, generated-contract drift, Python
  compilation and non-Markdown whitespace checks passed.
- All **91 original archive hashes** are unchanged; separate current-copy
  hashes verify the anonymised files.

The backend run reported 100 ORM-deprecation/Pydantic field-metadata warnings;
these are not claimed as resolved by this naming cleanup. This was selected
backend coverage, not a rerun of the entire Python suite or production sign-off.
The author's final review was sequential, without subagents. No operating
database content, access grants, prices, financial results or Git history was
changed. Database/container/user/volume renaming remains a separate operating
transition, not a hidden part of this change.

## Local container activation

The existing PostgreSQL container was renamed in place to `platform-postgres`
and verified healthy. The API and frontend were restarted using the existing
installation's explicit connection settings; the context selector returned all
three tenants. Container renaming does not recreate PostgreSQL or its volume.
The existing database, role and physical volume retain their previous names
until the separately requested future reset. The volume's historical
security-master naming does not limit the database to that subsystem.
