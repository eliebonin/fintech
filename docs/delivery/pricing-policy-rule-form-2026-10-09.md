# Pricing policy rule form — 9 October 2026

Reorganised the existing rule editor into Applies to, Price and timing, and Freshness and missing data groups. Each rule has a human-readable scope/price/timing summary. Advanced settings contain optional dataset/calendar overrides, subject type, exact identifiers and adjustment filters. Their configured restrictions remain visible in the collapsed heading. Existing values remain active when closed.

General choice help and available source definitions are collapsible. Price certification and as-traded/conversion choices remain in the main price group. Required timing fields stay visible when applicable. Two-column groups stack on small screens; CSS is scoped through a module.

All existing change handlers, policy payloads, compatibility acknowledgements, retry state, source permission checks and immutable save semantics are retained. No operating policy was saved or modified.

Verification: 21 pricing-policy tests passed across three files; TypeScript and isolated Next production build passed. Financial request/state code was compared with the pre-change snapshot and is unchanged. The isolated build directory and generated TypeScript include entries were removed; the starting next-env file was restored. The existing development app remains running.

The first live check received a transient service-unavailable response during tenant selection. A retry after build completion passed tenant selection and returned HTTP 200 for the policy editor, with all three new groups and advanced settings present in served HTML. Browser automation failed at Windows sandbox startup. No rendered visual or interaction acceptance is claimed.
