import { describe, expect, expectTypeOf, it } from "vitest";

import { createReferenceApiClient, type paths } from "./index";

describe("Reference API contract client", () => {
  it("types a v1 search request", () => {
    const client = createReferenceApiClient({ baseUrl: "https://example.test" });

    expectTypeOf(client.GET).toBeFunction();
    expectTypeOf<paths>().not.toBeAny();
    expect(client).toBeDefined();
  });
});
