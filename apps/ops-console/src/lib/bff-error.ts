import { NextResponse } from "next/server";

import { ReferenceApiError } from "./reference-api-client";

type ErrorWithMetadata = Error & {
  code?: string;
  correlationId?: string;
  fieldErrors?: Record<string, string[]>;
  retryable?: boolean;
};

function asError(error: unknown): ErrorWithMetadata | undefined {
  return error instanceof Error ? error as ErrorWithMetadata : undefined;
}

/**
 * Keep every browser-facing route on one safe error contract. The correlation
 * id is returned in both the JSON envelope and a response header so support
 * tooling can correlate browser and upstream logs.
 */
export function bffErrorResponse(error: unknown, fallbackMessage: string, request?: Request, code = "REFERENCE_API_ERROR") {
  const referenceError = error instanceof ReferenceApiError ? error : undefined;
  const typedError = referenceError ? asError(referenceError) : undefined;
  const status = referenceError?.status ?? 503;
  const correlationId = typedError?.correlationId
    ?? request?.headers.get("X-Correlation-Id")
    ?? referenceError?.requestId
    ?? crypto.randomUUID();
  const retryable = typedError?.retryable ?? (status === 408 || status === 429 || status >= 500);
  const response = NextResponse.json({
    error: {
      code: typedError?.code ?? code,
      // Do not reflect arbitrary exception text to the browser. Upstream
      // ReferenceApiError messages are already bounded by the API client;
      // unknown failures receive the route's human-safe fallback.
      message: referenceError?.message ?? fallbackMessage,
      correlationId,
      ...(referenceError?.requestId?{requestId:referenceError.requestId}:{}),
      retryable,
      ...(typedError?.fieldErrors ? { fieldErrors: typedError.fieldErrors } : {}),
    },
  }, { status });
  response.headers.set("X-Correlation-Id", correlationId);
  if(referenceError?.requestId)response.headers.set('X-Request-Id',referenceError.requestId);
  return response;
}
