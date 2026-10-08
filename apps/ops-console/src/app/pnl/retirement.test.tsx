import { expect, it, vi } from "vitest";
vi.mock("next/navigation", () => ({redirect: (url: string) => { throw new Error(`redirect:${url}`); }}));

it("sends old portfolio bookmarks to the new workspace without a calculation", async () => {
  const { default: Page } = await import("./[portfolio]/page");
  await expect(Page()).rejects.toThrow("redirect:/valuation");
});
