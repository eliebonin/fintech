import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const tradesPage = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");
const tradeDetailPage = readFileSync(new URL("./[tradeId]/page.tsx", import.meta.url), "utf8");

describe("trade pages", () => {
  it("use the selected tenant session rather than the legacy local context", () => {
    for (const page of [tradesPage, tradeDetailPage]) {
      expect(page).toContain("getActiveTenantContext");
      expect(page).toContain("getActiveTenantWorkspace");
      expect(page).not.toContain("resolveLocalTenantContext");
    }
  });
});
