"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Membership = { tenantId: string; tenantCode: string; tenantName: string; membershipRole: string };

export default function SelectTenantPage() {
  const router = useRouter();
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [error, setError] = useState("");
  const [selecting, setSelecting] = useState("");
  useEffect(() => { fetch("/api/session/memberships", { cache: "no-store" }).then(async (response) => response.ok ? response.json() : Promise.reject(new Error("Memberships are unavailable"))).then((payload: { data: Membership[] }) => setMemberships(payload.data)).catch((cause: Error) => setError(cause.message)); }, []);
  async function select(tenantId: string) {
    setSelecting(tenantId); setError("");
    const response = await fetch("/api/session/active-tenant", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tenantId }) });
    if (!response.ok) { setError("That tenant is no longer available to this session."); setSelecting(""); return; }
    router.push("/strategies"); router.refresh();
  }
  return <main className="tenant-select-page"><section className="tenant-select-card"><p className="eyebrow">TENANT WORKSPACE</p><h1>Select a tenant</h1><p className="muted">Your active tenant controls the data and modules available in this workspace.</p>{error ? <p className="error-panel">{error}</p> : null}<div className="tenant-options">{memberships.map((membership) => <button key={membership.tenantId} onClick={() => select(membership.tenantId)} disabled={Boolean(selecting)}><strong>{membership.tenantName}</strong><span>{membership.tenantCode} · {membership.membershipRole}</span><em>{selecting === membership.tenantId ? "Opening…" : "Open workspace →"}</em></button>)}</div>{!error && !memberships.length ? <p className="muted">Loading your available tenants…</p> : null}</section></main>;
}
