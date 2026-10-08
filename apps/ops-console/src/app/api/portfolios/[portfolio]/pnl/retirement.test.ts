import { NextRequest } from "next/server";
import { afterEach, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({}));
afterEach(() => vi.unstubAllGlobals());

it("returns Gone without forwarding demo aliases or querying market data", async () => {
  const fetch = vi.fn(() => { throw new Error("Legacy calculation must not run"); });
  vi.stubGlobal("fetch", fetch);
  const { GET } = await import("./route");
  const response = await GET(new NextRequest("http://localhost/api/portfolios/us/pnl?asOfDate=2026-08-28"), {params: Promise.resolve({portfolio: "us"})});
  expect(response.status).toBe(410);
  expect(await response.json()).toMatchObject({code: "valuation.demo_retired", status: 410});
  expect(fetch).not.toHaveBeenCalled();
});
