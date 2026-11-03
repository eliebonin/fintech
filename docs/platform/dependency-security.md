# Dependency security

**Status:** Maintained reference  
**Owner:** Engineering  
**Last reviewed:** 2026-10-30

Dependency declarations and complete committed locks are the source of truth:
`requirements.in` / `requirements.lock` and the pnpm workspace manifests /
`pnpm-lock.yaml`. Python installs require lockfile hashes; JavaScript CI installs
use the frozen workspace lock. Audit results are dated evidence, not a permanent
claim that a package or deployment is secure.

## Recurring checks

[Dependency security CI](../../.github/workflows/dependency-security.yml) runs on
pull requests, pushes to main, manual dispatch and Mondays at 06:23 UTC. The jobs
need only repository read access and do not connect to application databases.

- JavaScript: `pnpm audit --audit-level=low` checks the complete workspace lock,
  including development dependencies. It needs no application package installation.
- Python: the PyPA audit action, pinned to its verified v1.1.0 commit, runs against
  `requirements.lock` with PyPI and `require-hashes`. The separate job
  installs audit tooling without installing or executing application packages.
- Advisory findings and scanner/service failures fail the corresponding job.
  No advisories, package families or development dependencies are excluded.
- These checks become active in GitHub when the workflow is pushed. The weekly
  schedule runs from the default branch; local verification does not prove that
  a remote scheduled execution has occurred.

For a local Python audit, install the maintained `pip-audit` tool in a separate
tool environment and run:

```powershell
python -m pip_audit --vulnerability-service pypi --require-hashes --progress-spinner off -r requirements.lock
```

PyPI mode validates the requirement hashes; `require-hashes` already implies
no dependency resolution. OSV is useful as an independent advisory cross-check.
Its audit mode checks hash presence rather than downloaded-artifact validity;
do not confuse that with the install/hash verification above.

## Updating dependencies

1. Read the maintainer advisory and inspect the actual installed and locked
   versions. Record reachability separately from the advisory's severity.
2. Prefer targeted supported-family updates. Raise a manifest floor when the old
   range permits a known vulnerable release; update an existing transitive
   override rather than suppressing its advisory.
3. Regenerate the shared pnpm lock using `pnpm install --no-frozen-lockfile`.
   For Python, use pip-tools with hashes and explicit `--upgrade-package` targets;
   inspect the resulting pin changes before installing with
   `python -m pip install --require-hashes -r requirements.lock`.
4. Re-audit complete locks and verify resolved transitive versions. Use Node 24
   for frontend compatibility checks, matching CI. Do not change a developer's
   global runtime just to run an audit.
5. Verify affected tests, types, generated-contract parity and an isolated output
   production build. Use disposable databases for integration checks. Retain
   unrelated working changes and report existing failures rather than weakening
   tests or editing financial evidence to obtain a clean run.

Production identity, browser/network hardening, data-source rights, audit-table
protection and resource controls are separate security workstreams. A clean
dependency audit does not close them.

## References

- [PyPA audit action and inputs](https://github.com/pypa/gh-action-pip-audit)
- [pip-tools targeted upgrades and hashes](https://pip-tools.pypa.io/en/latest/)
- [pnpm audit](https://pnpm.io/cli/audit)
- [30 October remediation and verification](../delivery/dependency-security-20261030.md)
