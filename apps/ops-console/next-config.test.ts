import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(fileURLToPath(new URL("./next.config.ts", import.meta.url)), "utf8");

describe("local development origins", () => {
  it("allows the loopback host used by the local browser", () => {
    expect(source).toContain('allowedDevOrigins: ["127.0.0.1", "localhost"]');
  });
});
