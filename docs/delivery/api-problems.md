# Reference Data API problem responses

The Reference Data API returns errors as RFC 9457 Problem Details with media
type `application/problem+json`. Every response carries `X-Request-ID`; the
same UUID appears in the `requestId` extension member and should be supplied
to support when reporting a failed request.

The API accepts a canonical UUID in `X-Request-ID` and otherwise creates one.
`X-Correlation-ID` remains a temporary compatibility input for existing BFF
callers, but clients should adopt `X-Request-ID`.

| Type URI suffix | Status | Code | Safe client detail | Retry guidance |
| --- | ---: | --- | --- | --- |
| `invalid-request` | 400 | `request.invalid` | The request could not be processed. | Correct the request. |
| `authentication-required` | 401 | `authentication.required` | Authentication context is required. | Re-establish a valid session/BFF context. |
| `access-denied` | 403 | `authorization.forbidden` | The request is not permitted. | Do not retry unchanged; request access if appropriate. |
| `resource-not-found` | 404 | `resource.not_found` | The requested resource was not found. | Refresh client state before retrying. |
| `request-conflict` | 409 | `request.conflict` | The request conflicts with the current resource state. | Refresh and resolve the conflict. |
| `request-validation` | 422 | `request.validation_failed` | One or more request fields are invalid. | Correct fields described by safe `errors` entries. |
| `internal-error` | 500 | `internal.error` | The service could not complete the request. | Retry only if the calling workflow permits it; retain the request ID. |

Each payload contains the standard `type`, `title`, `status`, `detail`, and
`instance` members plus the documented `code` and `requestId` extensions.
Validation responses may contain `errors` entries with a field location,
message, and error kind. They deliberately omit rejected values. Error bodies
and normal request logs never contain submitted bodies, headers, cookies,
tokens, connection strings, raw exception messages, or stack-trace text.
