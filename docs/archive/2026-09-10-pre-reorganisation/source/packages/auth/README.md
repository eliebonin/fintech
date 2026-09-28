# Authentication helpers

This package will contain shared UI-server authentication/session helpers,
including Auth0 subject handling and authorised tenant context propagation.

It must never be treated as the sole authorization layer. Backend APIs remain
authoritative for tenant scope, entitlements, permissions, and lifecycle
transitions. Browser code must not receive tenant database credentials.
