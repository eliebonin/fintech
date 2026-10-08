export type ApiFieldErrors = Record<string, string[]>;

export type ApiErrorBody = {
  code?: unknown;
  message?: unknown;
  correlationId?: unknown;
  fieldErrors?: unknown;
  retryable?: unknown;
};

/**
 * Error returned by a same-origin BFF call. The browser receives a safe,
 * stable contract; tenant headers and upstream implementation details stay on
 * the server.
 */
export class BffApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code = "BFF_REQUEST_FAILED",
    public readonly correlationId?: string,
    public readonly fieldErrors?: ApiFieldErrors,
    public readonly retryable = false,
  ) {
    super(message);
    this.name = "BffApiError";
  }
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function normaliseFieldErrors(value: unknown): ApiFieldErrors | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const result: ApiFieldErrors = {};
  for (const [field, messages] of Object.entries(value)) {
    if (Array.isArray(messages)) {
      const strings = messages.filter((message): message is string => typeof message === "string");
      if (strings.length) result[field] = strings;
    } else if (typeof messages === "string" && messages.trim()) {
      result[field] = [messages];
    }
  }
  return Object.keys(result).length ? result : undefined;
}

/** Parse the one BFF error envelope, with a safe compatibility fallback. */
export async function parseApiErrorResponse(response: Response, fallbackMessage: string): Promise<BffApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }

  const root = body && typeof body === "object" ? body as Record<string, unknown> : {};
  const envelope = root.error && typeof root.error === "object" && !Array.isArray(root.error)
    ? root.error as ApiErrorBody
    : root as ApiErrorBody;
  const detail = root.detail;
  const detailMessage = typeof detail === "string"
    ? detail
    : Array.isArray(detail)
      ? detail.map((item) => typeof item === "object" && item && "msg" in item ? String((item as { msg: unknown }).msg) : String(item)).join("; ")
      : undefined;

  return new BffApiError(
    response.status,
    response.status===403?'Your current tenant role or module access does not allow this action. Ask your tenant administrator to review your access.'
      :response.status===401?'Select an active tenant or sign in again before continuing.'
      :asString(envelope.message) ?? detailMessage ?? fallbackMessage,
    asString(envelope.code) ?? `HTTP_${response.status}`,
    asString(envelope.correlationId) ?? response.headers.get("X-Correlation-Id") ?? undefined,
    normaliseFieldErrors(envelope.fieldErrors),
    ![401,403].includes(response.status)&&envelope.retryable === true,
  );
}
