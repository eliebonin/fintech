/** Bounded reads only. Mutations use their existing uncertain-outcome policy. */
export function readTimeoutMs(): number {
  const configured = Number(process.env.REFERENCE_API_READ_TIMEOUT_MS ?? 10000);
  return Number.isSafeInteger(configured) && configured > 0 ? configured : 10000;
}
export async function apiRead(input: RequestInfo | URL, init?: RequestInit, fetchImpl: typeof fetch = fetch): Promise<Response> {
  const { forwardLocalSession } = await import('./local-session-forward');
  init = await forwardLocalSession(input, init);
  const callerSignal = init?.signal ?? (input instanceof Request ? input.signal : undefined);
  const deadline = AbortSignal.timeout(readTimeoutMs());
  return fetchImpl(input, { ...init, signal: callerSignal ? AbortSignal.any([callerSignal, deadline]) : deadline });
}
