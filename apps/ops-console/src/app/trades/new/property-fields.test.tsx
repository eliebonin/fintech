import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { PropertyFields } from "./property-fields";
import type { TradeBookingContext } from "@/lib/browser-api-client";
import type { EnrichedTicketDraft } from "./ticket-model";

const draft: EnrichedTicketDraft = { strategyId: "", side: "BUY", quantity: "", executionPrice: "", tradeDatetime: "", settlementDate: "", tradePurpose: "INVESTMENT", properties: {}, tagIds: [], externalReferences: [] };
const context: TradeBookingContext = { tenantId: "tenant", bookedByUserAccountId: "actor", properties: [
  { definitionId: "weight", code: "WEIGHT", label: "Allocation weight", valueType: "DECIMAL", required: true, choices: [], description: "Portfolio allocation." },
  { definitionId: "flag", code: "FLAG", label: "Internal cross", valueType: "BOOLEAN", required: false, choices: [], description: null },
  { definitionId: "bucket", code: "BUCKET", label: "Booking bucket", valueType: "REFERENCE", catalogueId: "catalogue", required: false, choices: [], description: "Choose a desk bucket." },
], tags: [{tagId: "core", code: "CORE", label: "Core"}] };
function render(errors: {field: string; message: string}[] = [], values = draft) { return renderToStaticMarkup(<PropertyFields context={context} draft={values} errors={errors} onChange={() => {}} />); }
describe("booking property section", () => {
  it("separates required, optional and tag groups without collapsing controls", () => {
    const html = render();
    expect(html).toContain("Required properties"); expect(html).toContain("Optional properties"); expect(html).toContain("Trade tags (optional)");
    expect(html.indexOf("Allocation weight")).toBeLessThan(html.indexOf("Internal cross"));
    expect(html).not.toContain("<details"); expect(html).not.toContain("<option value=\"true\">True");
    expect(html).toContain('<option value="true">Yes</option>'); expect(html).toContain("Decimal number");
  });
  it("keeps hints and field errors separately associated with scalar inputs", () => {
    const html = render([{field: "properties.weight", message: "Allocation weight is required."}]);
    expect(html).toContain('aria-describedby="properties.weight-help properties.weight-error"');
    expect(html).toContain('id="properties.weight-error"'); expect(html).toContain("Portfolio allocation.");
    expect(html).toContain('aria-invalid="true"');
  });
  it("gives governed fields a focusable summary target and described error", () => {
    const html = render([{field: "properties.bucket", message: "Select a governed catalogue entry."}]);
    expect(html).toContain('id="properties.bucket"'); expect(html).toContain('tabindex="-1"');
    expect(html).toContain('aria-describedby="properties.bucket-help properties.bucket-error"');
    expect(html).toContain("Search Booking bucket"); expect(html).toContain("Choose a desk bucket.");
    expect(html).not.toContain("Previous values");
  });
  it("shows selected catalogue labels instead of internal record IDs", () => {
    const html = render([], {...draft, properties: {bucket: "opaque-version"}, propertyLabels: {bucket: "CORE — Core"}});
    expect(html).toContain("CORE — Core"); expect(html).not.toContain("opaque-version"); expect(html).toContain("Clear Booking bucket");
  });
  it("explains empty configuration without offering in-ticket definition changes", () => {
    const html = renderToStaticMarkup(<PropertyFields context={{...context,properties:[],tags:[]}} draft={draft} errors={[]} onChange={() => {}} />);
    expect(html).toContain("No custom trade properties"); expect(html).toContain("No trade tags"); expect(html).not.toContain("Add field");
  });
});
