import { redirect } from "next/navigation";
import Link from "next/link";

import { WorkspaceShell } from "@/components/workspace-shell";
import { getActiveTenantWorkspace } from "@/lib/tenant-session";

export const dynamic = "force-dynamic";

export default async function TenantProfilePage() {
  let workspace;
  try { workspace = await getActiveTenantWorkspace(); } catch { redirect("/select-tenant"); }
  return <WorkspaceShell moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">ACTIVE TENANT</p><h1>{workspace.tenantName}</h1><p className="muted">The current workspace identity, your membership, and the modules enabled for this tenant.</p></div><span className="synthetic-badge">ACTIVE CONTEXT</span></header><section className="tenant-profile-grid"><article className="tenant-profile-card"><p className="eyebrow">TENANT IDENTITY</p><dl><div><dt>Tenant code</dt><dd><code>{workspace.tenantCode}</code></dd></div><div><dt>Tenant ID</dt><dd><code>{workspace.tenantId}</code></dd></div></dl></article><article className="tenant-profile-card"><p className="eyebrow">YOUR MEMBERSHIP</p><strong className="tenant-role">{workspace.membershipRole}</strong><p className="muted">Your tenant role controls what you can do within this workspace.</p></article><article className="tenant-profile-card tenant-module-card"><p className="eyebrow">ENABLED MODULES</p><div className="module-list">{workspace.moduleCodes.map((module) => <span key={module}>{module}</span>)}</div><p className="muted">Navigation and actions are limited to these tenant entitlements.</p></article>{workspace.membershipRole==="TENANT_ADMIN"&&workspace.moduleCodes.includes("TRADING")?<article className="tenant-profile-card"><p className="eyebrow">TRADING SETTINGS</p><h2>Trade configuration</h2><p>Curate eligible parties, custom fields and reference catalogues.</p><Link href="/tenant-profile/trade-configuration">Manage trade configuration</Link></article>:null}</section></main></WorkspaceShell>;
}
