export type WorkspaceNavItem = {
  key: WorkspaceSection;
  icon: string;
  label: string;
  count?: string;
  href: string;
};

export type WorkspaceSection = "tenant-profile" | "operations" | "strategies" | "instruments" | "market-data" | "market-data-sources" | "trades" | "book-trade" | "imports" | "pnl" | "regulatory-reporting" | "lifecycle";

export const WORKSPACE_NAV_ITEMS: WorkspaceNavItem[] = [
  { key: "tenant-profile", icon: "◉", label: "Tenant profile", href: "/tenant-profile" },
  { key: "operations", icon: "✓", label: "Operations", href: "/operations" },
  { key: "strategies", icon: "◇", label: "Strategies", href: "/strategies" },
  { key: "instruments", icon: "◈", label: "Instruments", href: "/instruments" },
  { key: "market-data", icon: "◷", label: "Market data", href: "/market-data" },
  { key: "market-data-sources", icon: "≋", label: "Data sources", href: "/market-data/sources" },
  { key: "trades", icon: "▣", label: "Trades", href: "/trades" },
  { key:"lifecycle",icon:"◴",label:"Lifecycle",href:"/lifecycle" },
  { key: "book-trade", icon: "+", label: "Book trade", href: "/trades/new" },
  { key: "imports", icon: "⇧", label: "Trade imports", href: "/imports" },
  { key: "pnl", icon: "∑", label: "Valuation & P&L", href: "/valuation" },
  { key:"regulatory-reporting",icon:"▤",label:"Regulatory Reporting",href:"/regulatory-reporting" },
];

export function getActiveWorkspaceSection(pathname: string, hash = ""): WorkspaceSection {
  if(pathname.startsWith('/lifecycle'))return 'lifecycle';
  if(pathname.startsWith('/regulatory-reporting'))return 'regulatory-reporting';
  if (pathname.startsWith('/imports')) return 'imports';
  if (pathname.startsWith("/tenant-profile")) return "tenant-profile";
  if (pathname.startsWith("/operations")) return "operations";
  if (pathname.startsWith("/strategies")) return "strategies";
  if (pathname.startsWith("/market-data/sources")) return "market-data-sources";
  if (pathname.startsWith("/market-data")) return "market-data";
  if (pathname.startsWith("/trades/new")) return "book-trade";
  if (pathname.startsWith("/trades")) return "trades";
  if (pathname.startsWith("/valuation") || pathname.startsWith("/pnl")) return "pnl";
  if (pathname.startsWith("/instruments")) return "instruments";
  return "instruments";
}
