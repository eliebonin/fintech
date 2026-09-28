import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(fileURLToPath(new URL("./form.tsx", import.meta.url)), "utf8");

describe("cryptoasset text-field labels", () => {
  it("floats labels for text inputs so placeholders never render under the label", () => {
    for (const [label, slots] of [
      ["Canonical name", "floatedLabel"],
      ["Internal code (optional)", "floatedLabel"],
      ["Canonical / native symbol", "floatedLabel"],
      ["Protocol / programme name (optional)", "floatedLabel"],
      ["Smallest-unit decimals (optional)", "floatedNumber"],
    ] as const) {
      const start = source.indexOf(`label="${label}"`);
      const field = start >= 0 ? source.slice(Math.max(0, source.lastIndexOf("<TextField", start)), source.indexOf("/>", start) + 2) : "";
      expect(field, `${label} field should be found`).not.toBe("");
      expect(field, `${label} should force its MUI label to shrink`).toContain(slots);
    }
  });
});
