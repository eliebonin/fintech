import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const pages = [
  "bonds/new/page.tsx",
  "new/page.tsx",
  "listings/new/page.tsx",
  "crypto/new/form.tsx",
] as const;

describe("instrument catalogue dropdowns", () => {
  for (const page of pages) {
    it(`${page} uses native select controls`, () => {
      const source = readFileSync(fileURLToPath(new URL(`./${page}`, import.meta.url)), "utf8");

      expect(source).toContain("select: { native: true }");
      expect(source).not.toContain("<MenuItem");
    });
  }
});
