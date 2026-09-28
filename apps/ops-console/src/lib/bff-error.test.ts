import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { bffErrorResponse } from "./bff-error";

describe("BFF error envelope", () => {
  it("does not reflect arbitrary server exception text", async () => {
    const response = bffErrorResponse(
      new Error("database password must not reach a browser"),
      "Reference data service is unavailable",
      new Request("http://ops-console.test", { headers: { "X-Correlation-Id": "corr-safe-1" } }),
      "REFERENCE_API_UNAVAILABLE",
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("X-Correlation-Id")).toBe("corr-safe-1");
    expect(body.error).toMatchObject({
      code: "REFERENCE_API_UNAVAILABLE",
      message: "Reference data service is unavailable",
      correlationId: "corr-safe-1",
      retryable: true,
    });
  });
});
