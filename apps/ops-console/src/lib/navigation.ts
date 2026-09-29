export type WorkspaceNavItem = {
  key: WorkspaceSection;
  icon: string;
  label: string;
  count?: string;
  href: string;
};

export type WorkspaceSection = "work-queue" | "strategies" | "instruments" | "market-data" | "trades" | "pnl";

export const WORKSPACE_NAV_ITEMS: WorkspaceNavItem[] = [
  { key: "work-queue", icon: "⌂", label: "Work queue", href: "/#work-queue" },
  { key: "strategies", icon: "◇", label: "Strategies", href: "/strategies" },
  { key: "instruments", icon: "◈", label: "Instruments", href: "/" },
  { key: "market-data", icon: "◷", label: "Market data", href: "/market-data" },
  { key: "trades", icon: "▣", label: "Trades", href: "/trades" },
  { key: "pnl", icon: "∑", label: "Portfolios & P&L", href: "/pnl/us" },
];

export const REFERENCE_ACTION_ITEMS: WorkspaceNavItem[] = [
  { key: "instruments", icon: "+", label: "Add instrument", href: "/instruments/new" },
  { key: "instruments", icon: "+", label: "Add bond", href: "/instruments/bonds/new" },
  { key: "instruments", icon: "+", label: "Add fund", href: "/instruments/funds/new" },
  { key: "instruments", icon: "+", label: "Add index family", href: "/instruments/index-families/new" },
  { key: "instruments", icon: "+", label: "Add index", href: "/instruments/indices/new" },
  { key: "instruments", icon: "+", label: "Add ETP", href: "/instruments/etps/new" },
  { key: "instruments", icon: "+", label: "Add structured product", href: "/instruments/autocalls/new" },
  { key: "instruments", icon: "+", label: "Add cryptoasset", href: "/instruments/crypto/new" },
  { key: "instruments", icon: "+", label: "Add FX forward", href: "/instruments/fx-forwards/new" },
  { key: "instruments", icon: "+", label: "Add listing", href: "/instruments/listings/new" },
];

export function getActiveWorkspaceSection(pathname: string, hash = ""): WorkspaceSection {
  if (pathname === "/" && hash === "#work-queue") return "work-queue";
  if (pathname.startsWith("/strategies")) return "strategies";
  if (pathname.startsWith("/market-data")) return "market-data";
  if (pathname.startsWith("/trades")) return "trades";
  if (pathname.startsWith("/pnl")) return "pnl";
  if (pathname.startsWith("/instruments")) return "instruments";
  return "instruments";
}
