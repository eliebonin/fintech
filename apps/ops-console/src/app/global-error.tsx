"use client";
export default function GlobalError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <html lang="en"><body><main><h1>The workspace could not be loaded</h1><p role="alert">Try again or return to tenant selection.</p><button type="button" onClick={() => retry()}>Try again</button><p><a href="/select-tenant">Select a tenant</a></p></main></body></html>;
}
