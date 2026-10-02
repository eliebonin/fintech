import type { ConfiguredProperty } from "@/lib/trade-configuration-client";
export const sections = ["Standard fields", "Custom fields", "Reference catalogues", "Audit history"] as const;
export type Section = typeof sections[number];
export const fieldTypes: Record<string, string> = { TEXT: "Text", INTEGER: "Whole number", DECIMAL: "Decimal number", DATE: "Date", BOOLEAN: "Yes / no", REFERENCE: "Dropdown" };
export function typeLabel(type: string) { return type === "CHOICE" ? "Legacy dropdown · history only" : fieldTypes[type] ?? type; }
export function recordStatusLabel(record: string, catalogue: string) {
  if (record === "RETIRED") return "Retired";
  if (catalogue === "DRAFT") return "Awaiting catalogue publication";
  if (catalogue === "RETIRED") return "History only";
  return "Published";
}
export function fieldPage(fields: ConfiguredProperty[], query: string, type: string, history: boolean, offset: number) {
  const q = query.trim().toLocaleLowerCase();
  const matches = fields.filter(f => (history || f.status === "ACTIVE") && (!type || f.valueType === type) && `${f.code} ${f.label} ${f.description ?? ""}`.toLocaleLowerCase().includes(q));
  const start = Math.max(0, Math.min(offset, Math.max(0, Math.ceil(matches.length / 25) - 1) * 25));
  return { items: matches.slice(start, start + 25), total: matches.length, offset: start };
}
export function selectionDelta(original: { id: string; label?: string }[], draft: { id: string; label?: string }[]) {
  const before = new Set(original.map(r => r.id)), after = new Set(draft.map(r => r.id));
  const added = [...after].filter(id => !before.has(id)).length, removed = [...before].filter(id => !after.has(id)).length;
  return { added, removed, changed: added + removed > 0 };
}
export function tabDestination(index: number, key: string) {
  if (key === "ArrowLeft") return (index + sections.length - 1) % sections.length;
  if (key === "ArrowRight") return (index + 1) % sections.length;
  if (key === "Home") return 0;
  if (key === "End") return sections.length - 1;
  return null;
}
