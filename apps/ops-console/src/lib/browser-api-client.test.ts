import { describe, expect, it } from "vitest";

import { submitStructuredProductProposalFromBff } from "./browser-api-client";

describe("browser API client structured-product workflow", () => {
  it("submits a structured-product draft through the same-origin BFF", async () => {
    let requestedUrl = "";
    let requestedHeaders: HeadersInit | undefined;
    let requestedBody = "";
    const fetchImpl: typeof fetch = async (input, init) => {
      requestedUrl = String(input);
      requestedHeaders = init?.headers;
      requestedBody = String(init?.body ?? "");
      return new Response(JSON.stringify({
        data: {
          proposalId: "proposal-sp-1",
          status: "PENDING",
          proposalType: "CREATE_STRUCTURED_PRODUCT",
          submissionMode: "MANUAL",
          productSubtype: "AUTOCALL_CONSOLATION",
          componentInstrumentIds: [],
          compositionIds: [],
          conditionGroupIds: [],
          actionIds: [],
          initialFixingIds: [],
          proposedAt: "2026-09-09T00:00:00Z",
        },
        meta: {},
      }), { status: 201 });
    };

    const result = await submitStructuredProductProposalFromBff({ productSubtype: "AUTOCALL_CONSOLATION" }, "sp-key-1", fetchImpl);

    expect(requestedUrl).toBe("/api/instruments/structured-products");
    expect(new Headers(requestedHeaders).get("Idempotency-Key")).toBe("sp-key-1");
    expect(JSON.parse(requestedBody)).toEqual({ productSubtype: "AUTOCALL_CONSOLATION" });
    expect(result.data.productSubtype).toBe("AUTOCALL_CONSOLATION");
  });
});
