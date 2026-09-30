import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const pageSource = readFileSync(resolve(import.meta.dirname, "page.tsx"), "utf8");

describe("Operations page", () => {
  it("loads the tenant-scoped work queue and renders the dedicated inbox", () => {
    expect(pageSource).toContain("getActiveTenantContext");
    expect(pageSource).toContain("getWorkQueue(tenantContext)");
    expect(pageSource).toContain("OperationsWorkQueue");
  });
});
