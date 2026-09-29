import { describe, expect, it } from "vitest";

import { REFERENCE_ACTION_ITEMS, WORKSPACE_NAV_ITEMS, getActiveWorkspaceSection } from "./navigation";

describe("workspace navigation", () => {
  it("exposes the booked trades destination", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.label === "Trades")?.href).toBe("/trades");
  });

  it("exposes a structured-product creation workflow", () => {
    expect(REFERENCE_ACTION_ITEMS.find((item) => item.label === "Add structured product")?.href).toBe("/instruments/autocalls/new");
  });

  it("keeps detail and workflow routes under their parent navigation section", () => {
    expect(getActiveWorkspaceSection("/strategies/strategy-001")).toBe("strategies");
    expect(getActiveWorkspaceSection("/trades/TRADE-001")).toBe("trades");
    expect(getActiveWorkspaceSection("/pnl/uk")).toBe("pnl");
    expect(getActiveWorkspaceSection("/instruments/listings/new")).toBe("instruments");
    expect(getActiveWorkspaceSection("/market-data")).toBe("market-data");
  });

  it("treats the work-queue hash as an active workspace state", () => {
    expect(getActiveWorkspaceSection("/", "#work-queue")).toBe("work-queue");
  });

  it("does not advertise hard-coded queue or portfolio counts", () => {
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.key === "work-queue")?.count).toBeUndefined();
    expect(WORKSPACE_NAV_ITEMS.find((item) => item.key === "pnl")?.count).toBeUndefined();
  });
});
