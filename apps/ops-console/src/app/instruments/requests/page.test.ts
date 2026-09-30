import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const requestsPage = fileURLToPath(new URL("./page.tsx", import.meta.url));

describe("instrument requests page", () => {
  it("uses serializable href navigation from the server-rendered request list", () => {
    const source = readFileSync(requestsPage, "utf8");

    expect(source).not.toContain("component={Link}");
    expect(source).toContain('href="/instruments/create"');
    expect(source).toContain("href={request.reviewPath}");
  });
});
