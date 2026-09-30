"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Box, Chip, Divider, Drawer, IconButton, Stack, Typography } from "@mui/material";

import { getActiveWorkspaceSection, WORKSPACE_NAV_ITEMS, type WorkspaceSection } from "@/lib/navigation";

function Sidebar({ activeSection, moduleCodes, tenantName, membershipRole, onNavigate }: { activeSection: WorkspaceSection; moduleCodes?: string[]; tenantName?: string; membershipRole?: string; onNavigate?: () => void }) {
  const enabledItems = moduleCodes ? WORKSPACE_NAV_ITEMS.filter((item) => {
    if (item.key === "strategies") return moduleCodes.includes("TRADING") || moduleCodes.includes("FUND_MANAGEMENT");
    if (item.key === "trades") return moduleCodes.includes("TRADING");
    if (item.key === "market-data" || item.key === "pnl") return moduleCodes.includes("MARKET_DATA");
    return true;
  }) : WORKSPACE_NAV_ITEMS;
  return (
    <Box sx={{ width: 252, flexShrink: 0, bgcolor: "#101a2d", color: "#d7e0f1", display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Box sx={{ px: 2.5, py: 2.4 }}>
        <Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}>
          <Box sx={{ width: 30, height: 30, bgcolor: "#1f5eff", borderRadius: 1.5, display: "grid", placeItems: "center", color: "white", fontWeight: 900 }}>S</Box>
          <Typography sx={{ fontWeight: 800, color: "white", letterSpacing: "-0.02em" }}>Security Master</Typography>
        </Stack>
        <Typography variant="caption" sx={{ display: "block", color: "#8290aa", mt: 1 }}>OPERATIONS CONSOLE · MVP</Typography>
      </Box>
      <Divider sx={{ borderColor: "#28344d" }} />
      <Box sx={{ p: 1.5, flex: 1 }}>
        <Typography variant="overline" sx={{ px: 1.2, color: "#70809c", letterSpacing: "0.12em", fontWeight: 800 }}>Workspace</Typography>
        <Stack spacing={0.4} sx={{ mt: 0.8 }}>
          {enabledItems.map((item) => {
            const active = item.key === activeSection;
            return <Box key={item.label} component={Link} href={item.href} onClick={onNavigate} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", px: 1.2, py: 1, borderRadius: 1.5, bgcolor: active ? "#1e2d4c" : "transparent", color: active ? "white" : "#aab7cc", textDecoration: "none", "&:hover": { bgcolor: active ? "#24385f" : "#17243b" } }}><Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}><Typography sx={{ width: 18, textAlign: "center", color: active ? "#6e9aff" : "#8090aa" }}>{item.icon}</Typography><Typography variant="body2" sx={{ fontWeight: active ? 700 : 550 }}>{item.label}</Typography></Stack>{item.count && <Chip label={item.count} size="small" sx={{ height: 20, minWidth: 22, bgcolor: active ? "#e9a23b" : "#263651", color: active ? "#172238" : "#cad6e9", fontSize: 11, fontWeight: 800 }} />}</Box>;
          })}
        </Stack>
      </Box>
      <Box sx={{ p: 2, borderTop: "1px solid #28344d" }}><Typography variant="caption" sx={{ color: "#8290aa", display: "block" }}>TENANT CONTEXT</Typography><Typography variant="body2" sx={{ color: "white", fontWeight: 700, mt: 0.5 }}>{tenantName ?? "Demo investment office"}</Typography><Typography variant="caption" sx={{ color: "#8290aa" }}>{membershipRole ?? "Local mock session · analyst"}</Typography>{tenantName ? <Box component={Link} href="/select-tenant" onClick={onNavigate} sx={{ display: "inline-block", mt: 0.8, color: "#8cabff", fontSize: 12, fontWeight: 700 }}>Change tenant</Box> : null}</Box>
    </Box>
  );
}

export function WorkspaceShell({ children, sourceLabel = "LIVE API", moduleCodes, tenantName, membershipRole }: { children: ReactNode; sourceLabel?: string; moduleCodes?: string[]; tenantName?: string; membershipRole?: string }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [hash, setHash] = useState("");
  useEffect(() => {
    const updateHash = () => setHash(window.location.hash);
    updateHash();
    window.addEventListener("hashchange", updateHash);
    return () => window.removeEventListener("hashchange", updateHash);
  }, []);
  const activeSection = getActiveWorkspaceSection(pathname, hash);
  const activeItem = WORKSPACE_NAV_ITEMS.find((item) => item.key === activeSection);
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "#f3f6fb" }}>
      <Box sx={{ display: { xs: "none", md: "block" } }}><Sidebar activeSection={activeSection} moduleCodes={moduleCodes} tenantName={tenantName} membershipRole={membershipRole} /></Box>
      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { bgcolor: "#101a2d" } }}><Sidebar activeSection={activeSection} moduleCodes={moduleCodes} tenantName={tenantName} membershipRole={membershipRole} onNavigate={() => setMobileOpen(false)} /></Drawer>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box sx={{ height: 68, px: { xs: 2, md: 3.5 }, bgcolor: "white", borderBottom: "1px solid #e7ecf4", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}><IconButton onClick={() => setMobileOpen(true)} sx={{ display: { xs: "inline-flex", md: "none" }, color: "#1f5eff" }} aria-label="Open navigation">☰</IconButton><Box><Typography variant="caption" color="text.secondary">WORKSPACE / {activeItem?.label.toUpperCase()}</Typography><Typography variant="body2" sx={{ fontWeight: 750, mt: 0.25 }}>{activeItem?.label}</Typography></Box></Stack>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}><Chip label={sourceLabel} size="small" sx={{ bgcolor: sourceLabel === "LIVE API" ? "#e5f7ed" : "#fff4dc", color: sourceLabel === "LIVE API" ? "#14753c" : "#9a6200", fontWeight: 800, fontSize: 10 }} /><Box sx={{ width: 30, height: 30, bgcolor: "#dce7ff", color: "#1f5eff", borderRadius: "50%", display: "grid", placeItems: "center", fontWeight: 800 }}>OA</Box></Stack>
        </Box>
        {children}
      </Box>
    </Box>
  );
}
