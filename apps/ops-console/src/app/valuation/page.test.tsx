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
  session.workspace.mockResolvedValue({tenantName: "Selected tenant", membershipRole: "TENANT_ADMIN", moduleCodes: ["MARKET_DATA", "VALUATION"]});
});
afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); });

it("shows bounded live market-only workflow without browser pricing or a guessed total", async () => {
  const fetch = vi.fn(() => { throw new Error("No financial query is allowed"); });
  vi.stubGlobal("fetch", fetch);
  const { default: Page } = await import("./page");
  const html = renderToStaticMarkup(await Page());
  expect(html).toContain("MARKET-ONLY ALPHA");
  expect(html).toContain("Run history");
  expect(html).not.toContain("Total P&amp;L");
  expect(html).not.toContain("LIVE API · DEMO DATA");
  expect(fetch).not.toHaveBeenCalled();
});

it("requires a selected tenant instead of using the old demo context", async () => {
  session.context.mockRejectedValue(new Error("No selected tenant"));
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
