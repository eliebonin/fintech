import createClient from "openapi-fetch";

import type { components, paths } from "./generated";

export type ReferenceApiProblem = components["schemas"]["ProblemDetails"];

export type ReferenceApiClientOptions = {
  baseUrl: string;
  fetch?: typeof fetch;
};

export function createReferenceApiClient(options: ReferenceApiClientOptions) {
  return createClient<paths>(options);
}

export function isReferenceApiProblem(value: unknown): value is ReferenceApiProblem {
  return Boolean(
    value
      && typeof value === "object"
      && "code" in value
      && "requestId" in value
      && "status" in value,
  );
}
