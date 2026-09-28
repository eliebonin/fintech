# Workflow: external identifier mapping review

1. An authenticated operations analyst submits a mapping proposal containing
   the source namespace, external value, target UUID/type, optional venue
   context, effective date, and reason.
2. The API validates the target is visible in the trusted tenant context and
   stores the serialized proposal as `IDENTIFIER_MAPPING` with status `PENDING`.
3. A steward approves or rejects the proposal. The decision is append-only and
   records the actor, timestamp, reason, and proposal ID.
4. Approval creates a new `ing.external_object_mapping` row with `VERIFIED`
   status. Existing mappings are not overwritten; a conflicting active mapping
   returns HTTP 409 for human resolution.
5. The work queue removes the proposal from pending review once a decision is
   recorded.

The local BFF derives tenant and actor UUIDs from the local session seam. The
production adapter will derive them from Auth0 claims and enforce tenant
membership before forwarding the request.
