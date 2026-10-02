import type {
  BondProposalPayload,
  CurrencyGroupCode,
  CurrencyPayload,
  CryptoAssetProposalPayload,
  DayCountConventionPayload,
  EquityProposalPayload,
  EtpProposalPayload,
  FxForwardProposalPayload,
  IndexFamilyPayload,
  IndexFamilyProposalPayload,
  IndexKindPayload,
  MarketVenuePayload,
  OrganisationOptionPayload,
  ReturnProfilePayload,
  ReferenceDataProposalPayload,
  ReferenceNodeSearchPayload,
  StructuredProductProposalPayload,
  components,
} from "api-contracts";
import { BffApiError, parseApiErrorResponse } from "./api-errors";

export { BffApiError } from "./api-errors";
export type {
  BondProposalPayload,
  Currency,
  CurrencyGroup,
  CurrencyGroupCode,
  CurrencyPayload,
  CryptoAssetProposalPayload,
  DayCountConvention,
  DayCountConventionPayload,
  EquityProposalPayload,
  EtpProposalPayload,
  FxForwardProposalPayload,
  IndexFamilyOption,
  IndexFamilyPayload,
  IndexFamilyProposalPayload,
  IndexKind,
  IndexKindPayload,
  InstrumentSearchPayload,
  MarketVenue,
  MarketVenuePayload,
  OrganisationOption,
  OrganisationOptionPayload,
  ReturnProfile,
  ReferenceDataProposalPayload,
  ReferenceNodeOption,
  ReferenceNodeSearchPayload,
  StructuredProductProposalPayload,
} from "api-contracts";

export type TradeBookingRequest = components["schemas"]["TradeBookingRequest"];
export type FxForwardBookingRequest = components["schemas"]["FxForwardBookingRequest"];
export type FxForwardBookingInstrumentView = components["schemas"]["FxForwardBookingInstrumentView"];
export function searchFxForwardBookingInstrumentsFromBff(query:string, fetchImpl:typeof fetch=fetch, offset=0) {
  return bffGet<components["schemas"]["FxForwardBookingInstrumentSearchResponse"]>(`/api/trades/fx-forward-instruments?q=${encodeURIComponent(query)}&limit=25&offset=${offset}`,fetchImpl);
}
export function getFxForwardBookingInstrumentFromBff(instrumentId:string, fetchImpl:typeof fetch=fetch) {
  return bffGet<components["schemas"]["FxForwardBookingInstrumentResponse"]>(`/api/trades/fx-forward-instruments/${encodeURIComponent(instrumentId)}`,fetchImpl);
}
export function submitFxForwardTradeFromBff(payload:FxForwardBookingRequest,key:string,expectedTenantId:string,fetchImpl:typeof fetch=fetch) {
  return bffPost<components["schemas"]["TradeDetailResponse"]>("/api/trades/fx-forwards",payload,key,fetchImpl,{"X-Expected-Tenant-Id":expectedTenantId});
}

export function flattenCurrencyGroups(groups: CurrencyPayload["data"]): CurrencyPayload["data"][number]["items"][number][] {
  return groups.flatMap((group) => group.items);
}

type FetchImplementation = typeof fetch;

export async function bffGet<T>(path: string, fetchImpl: FetchImplementation = fetch): Promise<T> {
  const response = await fetchImpl(path, {
    method: "GET",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw await parseApiErrorResponse(response, `BFF request returned HTTP ${response.status}`);
  return await response.json() as T;
}

export async function bffPost<T>(
  path: string,
  payload: unknown,
  idempotencyKey?: string,
  fetchImpl: FetchImplementation = fetch,
  extraHeaders: Record<string, string> = {},
): Promise<T> {
  const response = await fetchImpl(path, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
      ...extraHeaders,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseApiErrorResponse(response, `BFF request returned HTTP ${response.status}`);
  return await response.json() as T;
}

export function createIdempotencyKey(): string {
  const randomUuid = globalThis.crypto?.randomUUID;
  return typeof randomUuid === "function"
    ? randomUuid.call(globalThis.crypto)
    : `browser-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function listCurrenciesFromBff(fetchImpl: FetchImplementation = fetch, groups?: CurrencyGroupCode[]): Promise<CurrencyPayload> {
  const suffix = groups?.length ? `?groups=${encodeURIComponent(groups.join(","))}` : "";
  return bffGet<CurrencyPayload>(`/api/currencies${suffix}`, fetchImpl);
}

export function listDayCountConventionsFromBff(fetchImpl: FetchImplementation = fetch): Promise<DayCountConventionPayload> {
  return bffGet<DayCountConventionPayload>("/api/day-count-conventions", fetchImpl);
}

export function listReturnProfilesFromBff(fetchImpl: FetchImplementation = fetch): Promise<ReturnProfilePayload> {
  return bffGet<ReturnProfilePayload>("/api/return-profiles", fetchImpl);
}

export function listIndexKindsFromBff(fetchImpl: FetchImplementation = fetch): Promise<IndexKindPayload> {
  return bffGet<IndexKindPayload>("/api/index-kind-catalogue", fetchImpl);
}

export function listOrganisationsFromBff(fetchImpl: FetchImplementation = fetch, query = ""): Promise<OrganisationOptionPayload> {
  const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
  return bffGet<OrganisationOptionPayload>(`/api/organisations${suffix}`, fetchImpl);
}

export function listIndexFamiliesFromBff(fetchImpl: FetchImplementation = fetch): Promise<IndexFamilyPayload> {
  return bffGet<IndexFamilyPayload>("/api/index-families", fetchImpl);
}

export function listMarketVenuesFromBff(fetchImpl: FetchImplementation = fetch): Promise<MarketVenuePayload> {
  return bffGet<MarketVenuePayload>("/api/market-venues", fetchImpl);
}

export function searchReferenceInstrumentsFromBff(query: string, fetchImpl: FetchImplementation = fetch): Promise<import("api-contracts").InstrumentSearchPayload> {
  return bffGet<import("api-contracts").InstrumentSearchPayload>(`/api/instruments/search?q=${encodeURIComponent(query)}`, fetchImpl);
}

export function searchReferenceNodesFromBff(
  query: string,
  options: { nodeType?: string | string[]; instrumentType?: string | string[]; assetClass?: string; referenceLevel?: "ANY" | "ECONOMIC" | "LISTING" } = {},
  fetchImpl: FetchImplementation = fetch,
): Promise<ReferenceNodeSearchPayload> {
  const params = new URLSearchParams({ q: query });
  const asList = (value: string | string[] | undefined) => value ? (Array.isArray(value) ? value : [value]).join(",") : undefined;
  const nodeType = asList(options.nodeType);
  const instrumentType = asList(options.instrumentType);
  if (nodeType) params.set("node_type", nodeType);
  if (instrumentType) params.set("instrument_type", instrumentType);
  if (options.assetClass) params.set("asset_class", options.assetClass);
  if (options.referenceLevel) params.set("reference_level", options.referenceLevel);
  return bffGet<ReferenceNodeSearchPayload>(`/api/reference-nodes/search?${params.toString()}`, fetchImpl);
}

export function submitEquityProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<EquityProposalPayload> {
  return bffPost<EquityProposalPayload>("/api/instruments/equities", payload, idempotencyKey, fetchImpl);
}

export function submitEquityListingProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<EquityProposalPayload> {
  return bffPost<EquityProposalPayload>("/api/instruments/equity-listing-proposals", payload, idempotencyKey, fetchImpl);
}

export function submitBondProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<BondProposalPayload> {
  return bffPost<BondProposalPayload>("/api/instruments/bond-proposals", payload, idempotencyKey, fetchImpl);
}

export function submitEtpProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<EtpProposalPayload> {
  return bffPost<EtpProposalPayload>("/api/instruments/etps", payload, idempotencyKey, fetchImpl);
}

export function submitFxForwardProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<FxForwardProposalPayload> {
  return bffPost<FxForwardProposalPayload>("/api/instruments/fx-forwards", payload, idempotencyKey, fetchImpl);
}

export function submitIndexProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<import("api-contracts").IndexProposalPayload> {
  return bffPost<import("api-contracts").IndexProposalPayload>("/api/instruments/indices", payload, idempotencyKey, fetchImpl);
}

export function submitIndexFamilyProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<IndexFamilyProposalPayload> {
  return bffPost<IndexFamilyProposalPayload>("/api/instruments/index-families", payload, idempotencyKey, fetchImpl);
}

export function submitCryptoAssetProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<CryptoAssetProposalPayload> {
  return bffPost<CryptoAssetProposalPayload>("/api/instruments/crypto-assets", payload, idempotencyKey, fetchImpl);
}

export function submitStructuredProductProposalFromBff(payload: Record<string, unknown>, idempotencyKey?: string, fetchImpl: FetchImplementation = fetch): Promise<StructuredProductProposalPayload> {
  return bffPost<StructuredProductProposalPayload>("/api/instruments/structured-products", payload, idempotencyKey, fetchImpl);
}

export function submitBookedTradeFromBff(
  payload: TradeBookingRequest,
  idempotencyKey: string,
  fetchImpl: FetchImplementation = fetch,
  expectedTenantId?: string,
): Promise<import("./trades").TradeDetailPayload> {
  return bffPost<import("./trades").TradeDetailPayload>("/api/trades", payload, idempotencyKey, fetchImpl, expectedTenantId ? {"X-Expected-Tenant-Id":expectedTenantId} : {});
}

export type TradeBookingContext = components["schemas"]["TradeBookingContextView"];
export type OptionBookingRequest = components['schemas']['OptionBookingRequest'];
export type OptionBookingListingView = components['schemas']['OptionBookingListingView'];
export function searchOptionBookingListingsFromBff(query:string,fetchImpl:typeof fetch=fetch,offset=0) {
  return bffGet<components['schemas']['OptionBookingListingSearchResponse']>(`/api/trades/option-listings?q=${encodeURIComponent(query)}&offset=${offset}`,fetchImpl);
}
export function getOptionBookingListingFromBff(id:string,fetchImpl:typeof fetch=fetch) {
  return bffGet<components['schemas']['OptionBookingListingResponse']>(`/api/trades/option-listings/${encodeURIComponent(id)}`,fetchImpl);
}
export function submitOptionTradeFromBff(payload:OptionBookingRequest,key:string,tenant:string,fetchImpl:typeof fetch=fetch) {
  return bffPost<import('./trades').TradeDetailPayload>('/api/trades/options',payload,key,fetchImpl,{'X-Expected-Tenant-Id':tenant});
}
export function submitOptionProposalFromBff(payload:components['schemas']['OptionProposalRequest'],fetchImpl:typeof fetch=fetch) {
  return bffPost<components['schemas']['ReferenceDataProposalResponse']>('/api/instruments/options',payload,undefined,fetchImpl);
}
export type TradeTraderOption = components["schemas"]["TradeTraderOption"];
export function getTradeBookingContextFromBff(fetchImpl: FetchImplementation = fetch): Promise<{data:TradeBookingContext}> {
  return bffGet("/api/trades/booking-context", fetchImpl);
}
export function searchTradeTradersFromBff(query: string, fetchImpl: FetchImplementation = fetch): Promise<{data:TradeTraderOption[]}> {
  return bffGet(`/api/trades/traders?q=${encodeURIComponent(query)}`, fetchImpl);
}

export function getCryptoAssetProposalFromBff(proposalId: string, fetchImpl: FetchImplementation = fetch): Promise<CryptoAssetProposalPayload> {
  return bffGet<CryptoAssetProposalPayload>(`/api/instruments/crypto-assets/${encodeURIComponent(proposalId)}`, fetchImpl);
}

export function getReferenceDataProposalFromBff(proposalId: string, fetchImpl: FetchImplementation = fetch): Promise<ReferenceDataProposalPayload> {
  return bffGet<ReferenceDataProposalPayload>(`/api/reference-data-proposals/${encodeURIComponent(proposalId)}`, fetchImpl);
}

export function decideReferenceDataProposalFromBff(
  proposalId: string,
  payload: { decision: "APPROVED" | "REJECTED"; reason: string },
  idempotencyKey?: string,
  fetchImpl: FetchImplementation = fetch,
): Promise<ReferenceDataProposalPayload> {
  return bffPost<ReferenceDataProposalPayload>(`/api/reference-data-proposals/${encodeURIComponent(proposalId)}`, payload, idempotencyKey, fetchImpl);
}

export function decideCryptoAssetProposalFromBff(
  proposalId: string,
  payload: { decision: "APPROVED" | "REJECTED"; reason: string },
  idempotencyKey?: string,
  fetchImpl: FetchImplementation = fetch,
): Promise<CryptoAssetProposalPayload> {
  return bffPost<CryptoAssetProposalPayload>(`/api/instruments/crypto-assets/${encodeURIComponent(proposalId)}/decision`, payload, idempotencyKey, fetchImpl);
}

export function decideIndexFamilyProposalFromBff(
  proposalId: string,
  payload: { decision: "APPROVED" | "REJECTED"; reason: string },
  idempotencyKey?: string,
  fetchImpl: FetchImplementation = fetch,
): Promise<IndexFamilyProposalPayload> {
  return bffPost<IndexFamilyProposalPayload>(`/api/instruments/index-families/${encodeURIComponent(proposalId)}/decision`, payload, idempotencyKey, fetchImpl);
}
