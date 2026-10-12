import { describe, expect, it } from "vitest";

import { WORKSPACE_NAV_ITEMS, getActiveWorkspaceSection } from "./navigation";

describe("workspace navigation", () => {
  it('exposes source settings as its own market-data destination',()=>{
    expect(WORKSPACE_NAV_ITEMS.find(item=>item.href==='/market-data/sources')?.label).toBe('Data sources');
    expect(getActiveWorkspaceSection('/market-data/sources')).toBe('market-data-sources');
  });
  it("routes valuation to a fresh workspace rather than a hardcoded demo strategy", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.key === "pnl")?.href).toBe("/valuation");
    expect(getActiveWorkspaceSection("/valuation")).toBe("pnl");
  });
  it("exposes the booked trades destination", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.label === "Trades")?.href).toBe("/trades");
  });

  it("exposes a dedicated booking route from workspace navigation", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.label === "Book trade")?.href).toBe("/trades/new");
    expect(getActiveWorkspaceSection("/trades/new")).toBe("book-trade");
  });

  it("uses a dedicated instrument catalogue route", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.key === "instruments")?.href).toBe("/instruments");
  });

  it("exposes a tenant-scoped operations inbox from the menu", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.key === "operations")?.href).toBe("/operations");
    expect(getActiveWorkspaceSection("/operations")).toBe("operations");
  });

  it("keeps detail and workflow routes under their parent navigation section", () => {
    expect(getActiveWorkspaceSection("/tenant-profile")).toBe("tenant-profile");
    expect(getActiveWorkspaceSection("/strategies/strategy-001")).toBe("strategies");
    expect(getActiveWorkspaceSection("/trades/TRADE-001")).toBe("trades");
    expect(getActiveWorkspaceSection("/pnl/uk")).toBe("pnl");
    expect(getActiveWorkspaceSection("/instruments/listings/new")).toBe("instruments");
    expect(getActiveWorkspaceSection("/market-data")).toBe("market-data");
  });

  it("does not advertise hard-coded portfolio counts", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.key === "pnl")?.count).toBeUndefined();
  });
});
