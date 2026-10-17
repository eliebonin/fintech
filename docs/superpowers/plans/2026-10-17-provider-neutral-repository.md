# Provider-neutral repository implementation plan

**Goal:** Remove the former operator's name from current source, configuration,
fixtures and all documentation, including archives, without rewriting Git history
or stored operating evidence. The user approved this scope on 17 October 2026.

**Architecture:** Use `platform` / `Platform` / `PLATFORM` as neutral technical
names. Existing UUIDs, migration revision identifiers, financial calculations and
authorization semantics remain unchanged. Existing installations retain their
connection settings through local environment configuration; fresh deployments
use neutral database and container defaults.

**Execution:** Sequential in the current checkout, preserving its pre-existing
staged work. No commits, pushes, operating migrations, reseeding or database
renames are part of this task.

## Tasks

- [x] Add a repository-wide neutrality regression and observe its initial failure.
- [x] Replace prose, sample names, schema comments and internal symbols together.
  Scrub local developer paths and rename external legacy-project references as
  legacy implementation references. Preserve public research URLs and citations.
- [x] Change browser context producers/consumers and synthetic acceptance fixtures
  together. Preserve the actual context validation protocol and permissions.
- [x] Neutralize deployment defaults, CI, fixture names and test database guards.
  Retain explicit environment overrides and owned disposable-database cleanup.
- [x] Check append-only source labels and deterministic fixture identities: new
  evidence uses neutral labels; existing events and approved versions stay intact.
- [x] Run the neutrality guard, focused Python checks, frontend type checking,
  contracts and affected browser acceptance. Use disposable databases only.
- [x] Document actual verification and the existing-installation transition.

## Review focus

1. Existing database volumes must not be mistaken for a fresh neutral deployment.
2. A stale browser tab must not bypass the context guard after the marker rename.
3. Changing demo labels must not create duplicate tenant UUIDs or replace versions.
4. Renamed source labels must not weaken idempotent booking replay.
5. Fixture and test guards must still reject operating databases of any name.

## Decisions

- Archived prose is included by explicit user request; chronology and evidence
  limitations remain, with an editorial neutralisation notice.
- Existing database values, local ignored configuration, dependencies, generated
  runtime outputs and Git internals are outside the source-tree content policy.
- No encoded legacy compatibility strings are added to production code. The
  regression check expresses its forbidden sequence numerically only to avoid
  making the check itself violate the repository policy.

## Verification

Completed: 19 offline checks; 101 selected backend checks in an owned disposable
database; 957 frontend unit checks; 21 isolated browser journeys; types,
contracts, compilation and code whitespace checks. Original archive hashes
remain unchanged alongside the current-copy hashes. See the
[delivery record](../../delivery/provider-neutral-repository-20261017.md) for
commands, durations, environment limitations and deployment compatibility.

Final review found one existing disposable-fixture prefix omitted by the new
guard. Its regression failed first, then passed after adding the exact UUID
family. No operating database access was permitted by that adjustment.
