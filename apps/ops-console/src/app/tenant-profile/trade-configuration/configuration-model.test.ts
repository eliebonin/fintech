import { describe, expect, it } from "vitest";
import { fieldPage, selectionDelta, tabDestination, typeLabel, recordStatusLabel } from "./configuration-model";
import type { ConfiguredProperty } from "@/lib/trade-configuration-client";

const field = (code: string, extra: Partial<ConfiguredProperty> = {}): ConfiguredProperty => ({
  definitionId: code, code, label: code === "BUCKET" ? "Booking bucket" : code,
  description: "Trade allocation", valueType: "TEXT", catalogueId: null,
  required: false, versionNo: 1, status: "ACTIVE", ...extra,
});

describe("trade configuration workspace", () => {
  it.each([["ACTIVE","DRAFT","Awaiting catalogue publication"],["ACTIVE","RETIRED","History only"],["RETIRED","ACTIVE","Retired"]])("does not imply a %s entry in a %s catalogue is selectable", (entry,source,label)=>{
    expect(recordStatusLabel(entry,source)).toBe(label);
  });
  it("keeps historical definitions out of the default list", () => {
    const fields = [field("BUCKET", { valueType: "REFERENCE" }), field("BUCKET", { definitionId: "old", status: "RETIRED", valueType: "CHOICE" })];
    expect(fieldPage(fields, "", "", false, 0).items).toHaveLength(1);
    expect(fieldPage(fields, "", "", true, 0).items).toHaveLength(2);
  });
  it("searches labels, codes and definitions together and combines type filters", () => {
    const fields = [field("BUCKET", { valueType: "REFERENCE" }), field("NOTE")];
    expect(fieldPage(fields, "booking", "REFERENCE", false, 0).items[0].code).toBe("BUCKET");
    expect(fieldPage(fields, "allocation", "TEXT", false, 0).items[0].code).toBe("NOTE");
    expect(fieldPage(fields, "missing", "", false, 0).total).toBe(0);
  });
  it("pages fields and clamps the offset after filtering or retirement", () => {
    const fields = Array.from({ length: 31 }, (_, i) => field(`FIELD_${i}`));
    expect(fieldPage(fields, "", "", false, 25).items).toHaveLength(6);
    expect(fieldPage(fields, "", "", false, 100).offset).toBe(25);
    expect(fieldPage(fields, "missing", "", false, 25)).toMatchObject({ offset: 0, total: 0, items: [] });
  });
  it("compares eligibility by canonical identity, not labels or order", () => {
    expect(selectionDelta([{ id: "a", label: "Old" }], [{ id: "a", label: "Corrected" }])).toEqual({ added: 0, removed: 0, changed: false });
    expect(selectionDelta([{ id: "a", label: "A" }], [{ id: "b", label: "B" }])).toEqual({ added: 1, removed: 1, changed: true });
  });
  it("supports keyboard tab navigation with wraparound", () => {
    expect(tabDestination(0, "ArrowLeft")).toBe(3);
    expect(tabDestination(3, "ArrowRight")).toBe(0);
    expect(tabDestination(2, "Home")).toBe(0);
    expect(tabDestination(1, "End")).toBe(3);
    expect(tabDestination(1, "Tab")).toBeNull();
  });
  it("uses business-friendly names without hiding historical types", () => {
    expect(typeLabel("REFERENCE")).toBe("Dropdown");
    expect(typeLabel("INTEGER")).toBe("Whole number");
    expect(typeLabel("CHOICE")).toBe("Legacy dropdown · history only");
  });
});
