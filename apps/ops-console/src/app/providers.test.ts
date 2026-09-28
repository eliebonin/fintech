import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(fileURLToPath(new URL("./providers.tsx", import.meta.url)), "utf8");

describe("MUI App Router integration", () => {
  it("uses the SSR Emotion cache provider around the theme", () => {
    expect(source).toContain("@mui/material-nextjs/v16-appRouter");
    expect(source).toContain("<AppRouterCacheProvider>");
    expect(source).toContain("</AppRouterCacheProvider>");
  });
});
