"use client";
export default function ErrorPage({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <main className="mvp-page"><h1>This page could not be loaded</h1><p role="alert">Try again. If the problem continues, contact support{error.digest ? ` with reference ${error.digest}` : ""}.</p><button type="button" onClick={() => retry()}>Try again</button><p><a href="/select-tenant">Select a tenant</a></p></main>;
}
