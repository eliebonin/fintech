import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("./strategy-console.tsx", import.meta.url), "utf8");

describe("strategy creation submit handling", () => {
  it("captures the form before awaiting the create request", () => {
    expect(source).toContain("const form = event.currentTarget;");
    expect(source).toContain("new FormData(form)");
    expect(source).toContain("form.reset()");
    expect(source).not.toContain("event.currentTarget.reset()");
  });
});
