// @ts-expect-error Node's runtime module type is intentionally not part of this browser-neutral package.
import { readFileSync } from "node:fs";
import { describe, expect, expectTypeOf, it } from "vitest";

import type { paths } from "./generated";

describe("market-data resolution OpenAPI contract", () => {
  it("publishes bounded snapshot creation and frozen-read operations", () => {
    const document = JSON.parse(readFileSync(new URL("../openapi/reference-data-api.v1.json", import.meta.url), "utf8"));
    const create = document.paths["/v1/market-data-resolution-snapshots"]?.post;
    expect(create).toBeDefined();
    expect(create.parameters.some((item: { name: string }) => item.name === "Idempotency-Key")).toBe(true);
    expect(create.responses["201"]).toBeDefined();
    expect(create.responses["409"]).toBeDefined();
    const schemaRef = create.requestBody.content["application/json"].schema.$ref as string;
    const schema = document.components.schemas[schemaRef.split("/").at(-1) as string];
    expect(schema.properties.subjectReferenceNodeIds.minItems).toBe(1);
    expect(schema.properties.subjectReferenceNodeIds.maxItems).toBe(50);
    expect(schema.properties.subjectReferenceNodeIds.uniqueItems).toBe(true);
    expectTypeOf<paths["/v1/market-data-resolution-snapshots"]>().not.toBeAny();
  });
});
