"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import Link, { useLinkStatus } from "next/link";
import { usePathname } from "next/navigation";
import { Box, Chip, Divider, Drawer, IconButton, Stack, Typography } from "@mui/material";

import { getActiveWorkspaceSection, WORKSPACE_NAV_ITEMS, type WorkspaceSection } from "@/lib/navigation";
import type { ActiveTenantWorkspace } from '@/lib/tenant-session';
import {canBookTrades,canManageInstruments,writePageRequirement} from '@/lib/instrument-authority';

function NavigationHint() {
  const { pending } = useLinkStatus();
  return <span aria-hidden="true" className={`workspace-nav-hint${pending ? " is-pending" : ""}`} />;
}

function Sidebar({ activeSection, moduleCodes, tenantName, membershipRole, permissionCodes, onNavigate }: { activeSection: WorkspaceSection; moduleCodes?: string[]; tenantName?: string; membershipRole?: string; permissionCodes?:string[]; onNavigate?: () => void }) {
  const enabledItems = moduleCodes ? WORKSPACE_NAV_ITEMS.filter((item) => {
    if (item.key === "strategies") return moduleCodes.includes("TRADING") || moduleCodes.includes("FUND_MANAGEMENT");
    if (item.key === "book-trade") return canBookTrades({membershipRole:membershipRole??'',moduleCodes,permissionCodes});
    if (item.key === 'instruments' || item.key === 'operations') return moduleCodes.includes('SECURITY_MASTER');
    if (item.key === "trades") return moduleCodes.includes("TRADING");
    if (item.key === "market-data" || item.key === "market-data-sources") return moduleCodes.includes("MARKET_DATA");
    if (item.key === "pnl") return moduleCodes.includes("MARKET_DATA") && moduleCodes.includes("VALUATION");
    return true;
  }) : WORKSPACE_NAV_ITEMS;
  return (
    <Box sx={{ width: 252, flexShrink: 0, bgcolor: "#101a2d", color: "#d7e0f1", display: "flex", flexDirection: "column", height: "100dvh", minHeight: 0 }}>
      <Box sx={{ px: 2.5, py: 2.4, flexShrink: 0 }}>
        <Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}>
          <Box sx={{ width: 30, height: 30, bgcolor: "#1f5eff", borderRadius: 1.5, display: "grid", placeItems: "center", color: "white", fontWeight: 900 }}>S</Box>
          <Typography sx={{ fontWeight: 800, color: "white", letterSpacing: "-0.02em" }}>Security Master</Typography>
        </Stack>
        <Typography variant="caption" sx={{ display: "block", color: "#8290aa", mt: 1 }}>OPERATIONS CONSOLE · MVP</Typography>
      </Box>
      <Divider sx={{ borderColor: "#28344d" }} />
      <Box sx={{ p: 1.5, flex: 1, minHeight: 0, overflowY: "auto", overscrollBehaviorY: "contain" }}>
        <Typography variant="overline" sx={{ px: 1.2, color: "#70809c", letterSpacing: "0.12em", fontWeight: 800 }}>Workspace</Typography>
        <Stack spacing={0.4} sx={{ mt: 0.8 }}>
          {enabledItems.map((item) => {
            const active = item.key === activeSection;
            return <Box key={item.label} component={Link} href={item.href} onClick={onNavigate} sx={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "space-between", px: 1.2, py: 1, borderRadius: 1.5, bgcolor: active ? "#1e2d4c" : "transparent", color: active ? "white" : "#aab7cc", textDecoration: "none", "&:hover": { bgcolor: active ? "#24385f" : "#17243b" } }}><Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}><Typography sx={{ width: 18, textAlign: "center", color: active ? "#6e9aff" : "#8090aa" }}>{item.icon}</Typography><Typography variant="body2" sx={{ fontWeight: active ? 700 : 550 }}>{item.label}</Typography></Stack>{item.count && <Chip label={item.count} size="small" sx={{ height: 20, minWidth: 22, bgcolor: active ? "#e9a23b" : "#263651", color: active ? "#172238" : "#cad6e9", fontSize: 11, fontWeight: 800 }} />}<NavigationHint /></Box>;
          })}
        </Stack>
      </Box>
      <Box sx={{ p: 2, flexShrink: 0, borderTop: "1px solid #28344d" }}><Typography variant="caption" sx={{ color: "#8290aa", display: "block" }}>TENANT CONTEXT</Typography><Typography variant="body2" sx={{ color: "white", fontWeight: 700, mt: 0.5 }}>{tenantName ?? "Tenant context unavailable"}</Typography><Typography variant="caption" sx={{ color: "#8290aa" }}>{membershipRole ?? "Select a tenant or retry"}</Typography>{<Box component={Link} href="/select-context" onClick={onNavigate} sx={{ display: "inline-block", mt: 0.8, color: "#8cabff", fontSize: 12, fontWeight: 700 }}>{tenantName ? "Change tenant" : "Select tenant"}</Box>}</Box>
    </Box>
  );
}

export function WorkspaceShell({ children, sourceLabel = "LIVE API", moduleCodes, tenantName, membershipRole,permissionCodes,userName,actorId }: { children: ReactNode; sourceLabel?: string; moduleCodes?: string[]; tenantName?: string; membershipRole?: string;permissionCodes?:string[];userName?:string;actorId?:string }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [hash, setHash] = useState("");
  const [loadedWorkspace,setLoadedWorkspace] = useState<{pathname:string;workspace:ActiveTenantWorkspace} | null>(null);
  useEffect(() => {
    if (permissionCodes && userName) return;
    const controller = new AbortController();
    fetch('/api/session/active-tenant',{cache:'no-store',signal:controller.signal})
      .then(async response => { if (!response.ok) throw new Error('Workspace unavailable'); return response.json() as Promise<ActiveTenantWorkspace>; })
      .then(workspace => {if (!controller.signal.aborted) setLoadedWorkspace({pathname,workspace});})
      .catch(() => {if (!controller.signal.aborted) setLoadedWorkspace(null);});
    return () => controller.abort();
  },[pathname,permissionCodes,userName]);
  const inherited = loadedWorkspace?.pathname === pathname ? loadedWorkspace.workspace : null;
  const sidebarContext = {
    moduleCodes:moduleCodes ?? inherited?.moduleCodes ?? [],
    tenantName:tenantName ?? inherited?.tenantName,
    membershipRole:membershipRole ?? inherited?.membershipRole,
    permissionCodes:permissionCodes ?? inherited?.permissionCodes,
  };
  useEffect(() => {
    const updateHash = () => setHash(window.location.hash);
    updateHash();
    window.addEventListener("hashchange", updateHash);
    return () => window.removeEventListener("hashchange", updateHash);
  }, []);
  const activeSection = getActiveWorkspaceSection(pathname, hash);
  const activeItem = WORKSPACE_NAV_ITEMS.find((item) => item.key === activeSection);
  const requiredModule=writePageRequirement(pathname);
  const accessKnown=Boolean(sidebarContext.tenantName&&sidebarContext.membershipRole);
  const writeWorkspace={...sidebarContext,membershipRole:sidebarContext.membershipRole??''};
  const writeAllowed=accessKnown&&(requiredModule==='TRADING'?canBookTrades(writeWorkspace):canManageInstruments(writeWorkspace));
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "#f3f6fb" }}>
      <Box sx={{ display: { xs: "none", md: "block" }, position: "sticky", top: 0, alignSelf: "flex-start", flexShrink: 0, height: "100dvh" }}><Sidebar activeSection={activeSection} {...sidebarContext} /></Box>
      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { bgcolor: "#101a2d" } }}><Sidebar activeSection={activeSection} {...sidebarContext} onNavigate={() => setMobileOpen(false)} /></Drawer>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        {(userName??inherited?.userName)?<div className="access-testing-banner"><span>Testing as <strong>{userName??inherited?.userName}</strong> · {sidebarContext.tenantName}</span><Link href="/select-context">Switch user / return to platform</Link></div>:null}
        <Box sx={{ height: 68, px: { xs: 2, md: 3.5 }, bgcolor: "white", borderBottom: "1px solid #e7ecf4", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}><IconButton onClick={() => setMobileOpen(true)} sx={{ display: { xs: "inline-flex", md: "none" }, color: "#1f5eff" }} aria-label="Open navigation">☰</IconButton><Box><Typography variant="caption" color="text.secondary">WORKSPACE / {activeItem?.label.toUpperCase()}</Typography><Typography variant="body2" sx={{ fontWeight: 750, mt: 0.25 }}>{activeItem?.label}</Typography></Box></Stack>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}><Chip label={sourceLabel} size="small" sx={{ bgcolor: sourceLabel === "LIVE API" ? "#e5f7ed" : "#fff4dc", color: sourceLabel === "LIVE API" ? "#14753c" : "#9a6200", fontWeight: 800, fontSize: 10 }} /><Box sx={{ width: 30, height: 30, bgcolor: "#dce7ff", color: "#1f5eff", borderRadius: "50%", display: "grid", placeItems: "center", fontWeight: 800 }}>OA</Box></Stack>
        </Box>
        {requiredModule&&!writeAllowed?<main className="mvp-page"><h1>{requiredModule==='TRADING'?'Trade booking access':'Instrument management access'}</h1><div className="error-panel" role="alert">{accessKnown?<>Your current user does not have the required action permission in the {requiredModule} module. Ask your tenant administrator to review group permissions.</>:<>Tenant permissions are being checked or could not be verified. No write form is available. Select your tenant or reload this page to retry.</>}</div><div className="ticket-actions"><Link href={requiredModule==='TRADING'?'/trades':'/instruments'}>{requiredModule==='TRADING'?'View trade history':'Explore instruments'}</Link><Link href="/select-context">Change context</Link></div></main>:children}
      </Box>
    </Box>
  );
}
