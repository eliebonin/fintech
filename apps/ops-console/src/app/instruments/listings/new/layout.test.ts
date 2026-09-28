import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(fileURLToPath(new URL("./page.tsx", import.meta.url)), "utf8");

describe("listing data layout", () => {
  it("keeps currency, quote factor, unit multiplier, and effective date usable", () => {
    expect(source).toContain("const listingColumn = { flex: 1, minWidth: 0 } as const;");
    expect(source.match(/sx=\{listingColumn\}/g)?.length).toBe(4);
  });
});
