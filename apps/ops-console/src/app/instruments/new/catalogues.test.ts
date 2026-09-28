import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(fileURLToPath(new URL("./page.tsx", import.meta.url)), "utf8");

describe("equity currency catalogue", () => {
  it("uses the grouped database-backed currency selector", () => {
    expect(source).toContain("listCurrenciesFromBff");
    expect(source).toContain("Include cryptoassets");
    expect(source).toContain("<optgroup");
    expect(source).not.toContain("const CURRENCIES");
  });
});
