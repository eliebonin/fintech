import "server-only";
import { searchInstruments } from "@/lib/instrument-data";
import type { ReferenceApiSearchOptions } from "@/lib/reference-api-client";
export function fixtureSearch(query: string, options: ReferenceApiSearchOptions) {
  const matches = searchInstruments(query).filter(item =>
    (!options.instrumentType || item.instrumentType === options.instrumentType) &&
    (!options.assetClass || item.assetClass === options.assetClass) &&
    (!options.status || item.status === options.status));
  const offset = options.offset ?? 0;
  return { data: matches.slice(offset, offset + (options.limit ?? 25)), meta: {
    total: matches.length, source: "synthetic-fixture-fallback", tenantContext: options.tenantId,
    warning: "Reference API unavailable; synthetic development fixtures are shown.",
  } };
}

export function fixtureCatalogue(query: string, options: ReferenceApiSearchOptions) {
  const result = fixtureSearch(query, options);
  return { ...result, data: result.data.map(item => ({
    instrumentId: item.instrumentId, canonicalName: item.canonicalName,
    instrumentType: item.instrumentType, assetClass: item.assetClass,
    status: item.status, baseCurrency: item.baseCurrency,
    listingCount: item.listings.length,
  })) };
}
