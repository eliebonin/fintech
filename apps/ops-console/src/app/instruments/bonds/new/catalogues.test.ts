import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(fileURLToPath(new URL("./page.tsx", import.meta.url)), "utf8");

describe("bond catalogue fields", () => {
  it("uses database-backed native selects for issuer and base currency", () => {
    expect(source).toContain("listCurrenciesFromBff");
    expect(source).toContain("listOrganisationsFromBff");
    expect(source).toMatch(/<TextField\s+select\s+label="Issuer organisation \(optional\)"/);
    expect(source).toMatch(/<TextField\s+select\s+label="Base \/ denomination currency \(optional\)"/);
    expect(source).toContain("Include cryptoassets");
    expect(source).toContain("<optgroup");
    expect(source).not.toContain("Issuer organisation UUID");
    expect(source).not.toContain("Base currency UUID");
  });

  it("keeps issuer, currency, and effective date in equal-width columns", () => {
    expect(source).toContain("const identityColumn = { flex: 1, minWidth: 0 } as const;");
    expect(source.match(/sx=\{identityColumn\}/g)?.length).toBe(3);
  });
});
