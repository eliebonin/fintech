# Local PostgreSQL port recovery — 11 November 2026

## Change and safety boundary

Windows excluded TCP 54316–54415, blocking the original loopback 54329 binding. No container was listening on 54329. PostgreSQL now publishes **127.0.0.1:15432 →5432**. Only the existing Compose `postgres` service was recreated (`up -d --no-deps --pull never postgres`). The resolved original named volume, mount destination, PostgreSQL 18 image, Compose project, database names, logins and passwords were retained. No volume removal, data migration, credential rotation, schema upgrade, seed, booking or financial run was performed.

The ignored runtime and maintenance URLs changed only their port. Compose, the fresh-install example/setup and existing local-only operator guards now use 15432; those guards still require the same local environment/host and explicitly selected database. Source-specific CSV tools remain isolated convenience tooling. CI's separate Linux PostgreSQL service retains its independent 54329 mapping; historical delivery records retain their original port evidence.

## App restart and verification

- The original PostgreSQL system identifier, read from the stopped volume through a read-only, network-disabled temporary container, matches the running recovered database.
- Read-only database checks confirmed 3 tenants, 10 strategies, 1,549 trades and 2,404 reference nodes. The non-owner runtime privilege check passed. Database revision `20261105_112` already matches repository head.
- API runs on **127.0.0.1:8000**; frontend runs on **127.0.0.1:3001**. Existing server-only operator configuration was retained. `/health` and `/select-context` returned 200.
- An isolated Edge browser rendered **Choose your workspace** with all three tenant choices and no uncaught page errors. It did not select a user or issue financial commands.
- All seven running Toolhive containers retain exactly the same container IDs, start timestamps and published ports. Their 8001/8090/8091 bindings were not stopped, reassigned or reconfigured.
- Final focused offline configuration/CLI regression: **17 passed** (29.41s), including the new port/identity-preservation check and local-target rejection guards. A first broader invocation had four DB-fixture setup errors because no test URL was supplied. A subsequent seeded run used a separate throwaway PostgreSQL container with test-only credentials; it was intentionally stopped during the expensive repeated universe-seeding cases. No full DB/operator-suite completion is claimed. Its container and test data were removed; operating credentials were not supplied to that runner.

Private process IDs, logs, database identity checks and container metadata are retained in ignored `.superpowers/sdd/2026-11-11-local-port-recovery/`. They are not product data or committed configuration. The application is left running for review; test-only resources are removed after verification.

## Future local startup

Keep the existing installation's ignored Compose names/volume settings and private credentials. Start only this project's database service with `docker compose up -d postgres`; use the already-configured runtime URL on 15432. Run the API on 8000 rather than Toolhive's 8001. The normal frontend upstream remains `http://127.0.0.1:8000`. A host-port change does not justify provisioning a new volume or reapplying password/setup commands.
