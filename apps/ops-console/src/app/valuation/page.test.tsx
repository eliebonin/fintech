import { SessionRequiredError } from "@/lib/server/workspace-errors";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("next/navigation", () => ({
  redirect: (url: string) => { throw new Error(`redirect:${url}`); },
  usePathname: () => "/valuation",
}));
const session = vi.hoisted(() => ({ context: vi.fn(), workspace: vi.fn() }));
vi.mock("@/lib/tenant-session", () => ({
  getActiveTenantContext: session.context,
  getActiveTenantWorkspace: session.workspace,
}));
beforeEach(() => {
  session.context.mockResolvedValue({ tenantId: "selected", userAccountId: "user" });
  session.workspace.mockResolvedValue({tenantName: "Selected tenant", membershipRole: "TENANT_ADMIN", moduleCodes: ["MARKET_DATA", "VALUATION"],permissionCodes:["VALUATION_READ","VALUATION_RUN","VALUATION_REVIEW","MARKET_DATA_READ"]});
});
afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); });

it("shows bounded economic workflow without browser pricing or a guessed total", async () => {
  const fetch = vi.fn(() => { throw new Error("No financial query is allowed"); });
  vi.stubGlobal("fetch", fetch);
  const { default: Page } = await import("./page");
  const html = renderToStaticMarkup(await Page());
  expect(html).toContain("ECONOMIC P&amp;L ALPHA");
  expect(html).toContain("Run history");
  expect(html).not.toContain("Total P&amp;L");
  expect(html).not.toContain("LIVE API · DEMO DATA");
  expect(fetch).not.toHaveBeenCalled();
});

it("requires a selected tenant instead of using the old demo context", async () => {
  session.context.mockRejectedValue(new SessionRequiredError());
  const { default: Page } = await import("./page");
  await expect(Page()).rejects.toThrow("redirect:/select-tenant");
  expect(session.workspace).not.toHaveBeenCalled();
});

it("explains missing module access without claiming a service outage", async () => {
  session.workspace.mockResolvedValue({tenantName: "Restricted", membershipRole: "READ_ONLY", moduleCodes: []});
  const { default: Page } = await import("./page");
  const html = renderToStaticMarkup(await Page());
  expect(html).toContain("ACCESS RESTRICTED");
  expect(html).not.toContain("NOT IMPLEMENTED");
  expect(html).not.toContain("API UNAVAILABLE");
});

it("does not expose calculation with market data access alone", async () => {
  session.workspace.mockResolvedValue({tenantName: "Restricted", membershipRole: "TENANT_ADMIN", moduleCodes: ["MARKET_DATA"]});
  const { default: Page } = await import("./page");
  const html = renderToStaticMarkup(await Page());
  expect(html).toContain("ACCESS RESTRICTED");
  expect(html).not.toContain("Run history");
});

it("allows a group-granted member to calculate without granting review", async () => {
  session.workspace.mockResolvedValue({tenantName:"Delegated",membershipRole:"MEMBER",
    moduleCodes:["MARKET_DATA","VALUATION"],permissionCodes:["MARKET_DATA_READ","VALUATION_READ","VALUATION_RUN"]});
  const {default:Page}=await import("./page");
  const html=renderToStaticMarkup(await Page());
  expect(html).toContain("Calculate and stage");
  expect(html).toContain("Daily input register");
});

it("does not give a review-only member calculation controls", async () => {
  session.workspace.mockResolvedValue({tenantName:"Reviewer",membershipRole:"MEMBER",
    moduleCodes:["MARKET_DATA","VALUATION"],permissionCodes:["MARKET_DATA_READ","VALUATION_READ","VALUATION_REVIEW"]});
  const {default:Page}=await import("./page");
  const html=renderToStaticMarkup(await Page());
  expect(html).toContain("Run history");
  expect(html).not.toContain("Calculate and stage");
  expect(html).not.toContain("Daily input register");
});
