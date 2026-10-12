import { cookies } from 'next/headers';

/** Forward the opaque local session only to the configured private API. */
export async function forwardLocalSession(input: RequestInfo | URL, init?: RequestInit): Promise<RequestInit | undefined> {
  let url: URL;
  try { url = new URL(input instanceof Request ? input.url : String(input)); }
  catch { return init; } // Browser-relative BFF requests never receive API credentials.
  const api = new URL(process.env.REFERENCE_API_URL ?? 'http://localhost:8000');
  if (url.origin !== api.origin) return init;
  let token: string | undefined;
  try { token = (await cookies()).get('local_access_session')?.value; }
  catch { return init; } // Unit tests and non-request callers have no cookie store.
  if (!token) return init;
  const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
  headers.set('X-Local-Access-Token', token);
  return { ...init, headers };
}
