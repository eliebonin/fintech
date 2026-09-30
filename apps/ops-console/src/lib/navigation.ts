export type WorkspaceNavItem = {
  key: WorkspaceSection;
  icon: string;
  label: string;
  count?: string;
  href: string;
};

export type WorkspaceSection = "tenant-profile" | "strategies" | "instruments" | "market-data" | "trades" | "pnl";

export const WORKSPACE_NAV_ITEMS: WorkspaceNavItem[] = [
  { key: "tenant-profile", icon: "◉", label: "Tenant profile", href: "/tenant-profile" },
  { key: "strategies", icon: "◇", label: "Strategies", href: "/strategies" },
  { key: "instruments", icon: "◈", label: "Instruments", href: "/instruments" },
  { key: "market-data", icon: "◷", label: "Market data", href: "/market-data" },
  { key: "trades", icon: "▣", label: "Trades", href: "/trades" },
  { key: "pnl", icon: "∑", label: "Portfolios & P&L", href: "/pnl/us" },
];

export function getActiveWorkspaceSection(pathname: string, hash = ""): WorkspaceSection {
  if (pathname.startsWith("/tenant-profile")) return "tenant-profile";
  if (pathname.startsWith("/strategies")) return "strategies";
  if (pathname.startsWith("/market-data")) return "market-data";
  if (pathname.startsWith("/trades")) return "trades";
  if (pathname.startsWith("/pnl")) return "pnl";
  if (pathname.startsWith("/instruments")) return "instruments";
  return "instruments";
}
