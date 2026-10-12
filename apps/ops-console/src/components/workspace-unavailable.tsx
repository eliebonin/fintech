"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
export function WorkspaceUnavailable({ forbidden = false, resource = "Workspace" }: { forbidden?: boolean; resource?: string }) {
  const router = useRouter();
  return <main className="mvp-page"><h1>{resource} {forbidden ? "access restricted" : "temporarily unavailable"}</h1>
    <p role="alert" className="error-panel">{forbidden ? "Your current tenant access does not allow this page. Ask your tenant administrator to review your access, or select another tenant." : "The service could not be reached. Your selected tenant has been preserved. Try again in a moment."}</p>
    <div className="ticket-actions"><button type="button" onClick={() => router.refresh()}>Try again</button><Link href="/select-tenant">Change tenant</Link></div></main>;
}
