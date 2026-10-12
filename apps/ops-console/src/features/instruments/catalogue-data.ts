import "server-only";
import { ReferenceApiError, searchReferenceInstruments, searchInstrumentCatalogue, type ReferenceApiSearchOptions } from "@/lib/reference-api-client";
import { fixtureSearch, fixtureCatalogue } from "./fixture-search";
export async function loadInstrumentSearch(query: string, options: ReferenceApiSearchOptions) {
  try { return await searchReferenceInstruments(query, options); }
  catch (error) {
    if (!canUseDevelopmentFixtures(error)) throw error;
    return fixtureSearch(query, options);
  }
}

export async function loadCatalogue(query: string, options: ReferenceApiSearchOptions) {
  try { return await searchInstrumentCatalogue(query, options); }
  catch (error) {
    if (!canUseDevelopmentFixtures(error)) throw error;
    return fixtureCatalogue(query, options);
  }
}

function canUseDevelopmentFixtures(error: unknown): boolean {
  const developmentFixtures = process.env.NODE_ENV !== "production" && process.env.APP_ENV !== "production" && process.env.ALLOW_SYNTHETIC_FALLBACK === "true";
  const outage = error instanceof ReferenceApiError ? error.status >= 500
    : error instanceof DOMException ? error.name === "TimeoutError"
    : error instanceof TypeError && /fetch failed|failed to fetch|networkerror/i.test(error.message);
  return developmentFixtures && outage;
}
