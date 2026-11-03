import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
import { POST } from "./route";

describe("active tenant BFF route", () => {
  it("directs legacy tenant-only selection to the verified context selector", async () => {
    const response = await POST();
    expect(response.status).toBe(410);
    await expect(response.json()).resolves.toMatchObject({error:{code:'CONTEXT_SELECTION_REQUIRED'}});
  });

  it("never sets a legacy identity cookie", async () => {
    const response = await POST();
    expect(response.headers.get("set-cookie")).toBeNull();
  });
});
