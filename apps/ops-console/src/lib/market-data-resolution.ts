import type { components } from "api-contracts";

export type MarketDataResolutionSnapshot = components["schemas"]["MarketDataResolutionSnapshotView"];
export type MarketDataResolutionItem = components["schemas"]["MarketDataResolutionSnapshotItemView"];
export type MarketDataResolutionCreate = components["schemas"]["MarketDataResolutionSnapshotCreate"];

export function buildOneSubjectResolutionRequest(subjectReferenceNodeId: string, values: Omit<MarketDataResolutionCreate, "subjectReferenceNodeIds">): MarketDataResolutionCreate {
  return { ...values, subjectReferenceNodeIds: [subjectReferenceNodeId] };
}

export function resolutionStatusLabel(status: string): string {
  return ({ SELECTED: "Selected", MISSING: "Missing", STALE: "Stale", DENIED: "Denied" } as Record<string, string>)[status] ?? status;
}

export function formatResolutionTimestamp(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toISOString().replace("T", " ").replace(".000Z", "Z");
}
