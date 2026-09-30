import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const detail = fileURLToPath(new URL("../../components/instrument-detail.tsx", import.meta.url));
const contextualListingPage = fileURLToPath(new URL("./[instrumentId]/listings/new/page.tsx", import.meta.url));

describe("contextual listing creation", () => {
  it("carries an approved instrument from its detail page into a dedicated listing form", () => {
    expect(readFileSync(detail, "utf8")).toContain("/instruments/${instrument.instrumentId}/listings/new");
    expect(existsSync(contextualListingPage)).toBe(true);
    expect(readFileSync(contextualListingPage, "utf8")).toContain("initialInstrument={response.data}");
  });
});
