# Platform

[Dataset governance and workload admission](dataset-rights-and-workload.md)
explains strict missing-profile denial, invented-data origin and retryable
capacity controls, with current defaults and deferred deployment isolation.

[Local security setup](security-controls.md) documents separate database runtime/
maintenance credentials, loopback Docker publishing, append-only audit, safe
denials, nonce CSP and HTTPS cookies. Production authentication remains deferred.

**Status:** Accepted  
**Content type:** Platform index  
**Owner:** Platform engineering team  
**Last reviewed:** 2026-10-12

Use [API](api/README.md), [frontend](frontend/README.md), and [data/schema](data-and-schema/README.md). The platform serves the canonical plane and tenant overlays through versioned contracts, provenance, and audit controls.

See the [feature register](../product/feature-register.md) for actual delivery; engineering boundaries do not imply production identity, separate-database deployment, full NAV or universal product support.
