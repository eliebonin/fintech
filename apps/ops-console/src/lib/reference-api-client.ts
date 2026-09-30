import "server-only";

import type { TenantContext } from "./tenant-types";
import { isReferenceApiProblem } from "api-contracts";
import type {
  BondProposalPayload,
  CryptoAssetProposalPayload,
  DayCountConventionPayload,
  EquityProposalPayload,
  EtpProposalPayload,
  FxForwardProposalPayload,
  IndexFamilyProposalPayload,
  IndexProposalPayload,
  InstrumentSearchPayload,
  ReferenceNodeSearchPayload,
  CurrencyGroupCode,
  CurrencyPayload,
  DayCountConvention,
  MarketVenue,
  MarketVenuePayload,
  ReturnProfilePayload,
  IndexKindPayload,
  OrganisationOptionPayload,
  IndexFamilyPayload,
  IndexKind,
  OrganisationOption,
  IndexFamilyOption,
  ReturnProfile,
  CurrencyGroup,
  Currency,
  ReferenceApiMeta,
  ReferenceDataProposalPayload,
  StructuredProductProposalPayload,
} from "api-contracts";

export type {
  BondProposalPayload,
  CryptoAssetProposalPayload,
  DayCountConventionPayload,
  EquityProposalPayload,
  EtpProposalPayload,
  FxForwardProposalPayload,
  IndexFamilyProposalPayload,
  IndexProposalPayload,
  InstrumentSearchPayload,
  ReferenceNodeSearchPayload,
  CurrencyGroupCode,
  CurrencyPayload,
  DayCountConvention,
  MarketVenue,
  MarketVenuePayload,
  ReturnProfilePayload,
  IndexKindPayload,
  OrganisationOptionPayload,
  IndexFamilyPayload,
  IndexKind,
  OrganisationOption,
  IndexFamilyOption,
  ReturnProfile,
  CurrencyGroup,
  Currency,
  ReferenceApiMeta,
  ReferenceDataProposalPayload,
  StructuredProductProposalPayload,
} from "api-contracts";

export class ReferenceApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
    public readonly requestId?: string,
  ) {
    super(code ? message : `Reference API returned HTTP ${status}`);
    this.name = "ReferenceApiError";
  }
}

export type ReferenceApiSearchOptions = Pick<TenantContext, "tenantId" | "userAccountId"> & {
  instrumentType?: string;
  assetClass?: string;
  status?: string;
  baseUrl?: string;
  limit?: number;
  offset?: number;
  correlationId?: string;
  fetchImpl?: typeof fetch;
};

export async function searchReferenceInstruments(query: string, options: ReferenceApiSearchOptions): Promise<InstrumentSearchPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/instruments/search", baseUrl);
  url.searchParams.set("q", query);
  url.searchParams.set("limit", String(options.limit ?? 50));
  url.searchParams.set("offset", String(options.offset ?? 0));
  if (options.instrumentType) url.searchParams.set("instrument_type", options.instrumentType);
  if (options.assetClass) url.searchParams.set("asset_class", options.assetClass);
  if (options.status) url.searchParams.set("status", options.status);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
  });
  if (!response.ok) {
    let problem: unknown;
    try {
      problem = await response.json();
    } catch {
      // Unrecognised upstream JSON and invalid bodies never reach the browser.
    }
    if (isReferenceApiProblem(problem)) {
      throw new ReferenceApiError(response.status, problem.detail, problem.code, problem.requestId);
    }
    throw new ReferenceApiError(response.status, `Reference API returned HTTP ${response.status}`);
  }
  return (await response.json()) as InstrumentSearchPayload;
}

export type ReferenceNodeSearchOptions = Pick<TenantContext, "tenantId" | "userAccountId"> & {
  nodeType?: string | string[];
  instrumentType?: string | string[];
  assetClass?: string;
  referenceLevel?: "ANY" | "ECONOMIC" | "LISTING";
  baseUrl?: string;
  limit?: number;
  offset?: number;
  correlationId?: string;
  fetchImpl?: typeof fetch;
};

export async function searchReferenceNodes(query: string, options: ReferenceNodeSearchOptions): Promise<ReferenceNodeSearchPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/reference-nodes/search", baseUrl);
  const asList = (value: string | string[] | undefined) => value ? (Array.isArray(value) ? value : [value]).join(",") : undefined;
  url.searchParams.set("q", query);
  url.searchParams.set("limit", String(options.limit ?? 50));
  url.searchParams.set("offset", String(options.offset ?? 0));
  const nodeType = asList(options.nodeType);
  const instrumentType = asList(options.instrumentType);
  if (nodeType) url.searchParams.set("node_type", nodeType);
  if (instrumentType) url.searchParams.set("instrument_type", instrumentType);
  if (options.assetClass) url.searchParams.set("asset_class", options.assetClass);
  if (options.referenceLevel) url.searchParams.set("reference_level", options.referenceLevel);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as ReferenceNodeSearchPayload;
}

export type EquityProposalOptions = Pick<TenantContext, "tenantId" | "userAccountId"> & {
  baseUrl?: string;
  correlationId?: string;
  fetchImpl?: typeof fetch;
};

export async function getReferenceDataProposal(proposalId: string, options: EquityProposalOptions): Promise<ReferenceDataProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL(`/v1/reference-data-proposals/${proposalId}`, baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as ReferenceDataProposalPayload;
}

export async function decideReferenceDataProposal(
  proposalId: string,
  payload: { decision: "APPROVED" | "REJECTED"; reason: string },
  options: EquityProposalOptions,
): Promise<ReferenceDataProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL(`/v1/reference-data-proposals/${proposalId}/decision`, baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as ReferenceDataProposalPayload;
}

export async function submitEquityProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<EquityProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/equity-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as EquityProposalPayload;
}

export async function submitCryptoAssetProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<CryptoAssetProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/crypto-asset-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as CryptoAssetProposalPayload;
}

export async function submitStructuredProductProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<StructuredProductProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/structured-product-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as StructuredProductProposalPayload;
}

export async function submitCryptoAssetProposalFromBff(payload: Record<string, unknown>, fetchImpl: typeof fetch = fetch): Promise<CryptoAssetProposalPayload> {
  const response = await fetchImpl("/api/instruments/crypto-assets", {
    method: "POST",
    cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Cryptoasset proposal returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string; error?: { message?: string } };
      message = body.detail ?? body.error?.message ?? message;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as CryptoAssetProposalPayload;
}

export async function getCryptoAssetProposal(proposalId: string, options: EquityProposalOptions): Promise<CryptoAssetProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL(`/v1/crypto-asset-proposals/${proposalId}`, baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as CryptoAssetProposalPayload;
}

export async function decideCryptoAssetProposal(
  proposalId: string,
  payload: { decision: "APPROVED" | "REJECTED"; reason: string },
  options: EquityProposalOptions,
): Promise<CryptoAssetProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL(`/v1/crypto-asset-proposals/${proposalId}/decision`, baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as CryptoAssetProposalPayload;
}

export async function decideCryptoAssetProposalFromBff(
  proposalId: string,
  payload: { decision: "APPROVED" | "REJECTED"; reason: string },
  fetchImpl: typeof fetch = fetch,
): Promise<CryptoAssetProposalPayload> {
  const response = await fetchImpl(`/api/instruments/crypto-assets/${proposalId}/decision`, {
    method: "POST",
    cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Cryptoasset decision returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string; error?: { message?: string } };
      message = body.detail ?? body.error?.message ?? message;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as CryptoAssetProposalPayload;
}

export async function submitBondProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<BondProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/bond-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as BondProposalPayload;
}

export async function submitEtpProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<EtpProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const response = await (options.fetchImpl ?? fetch)(new URL("/v1/etp-proposals", baseUrl), {
    method: "POST", cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-Tenant-Id": options.tenantId, "X-User-Account-Id": options.userAccountId },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new ReferenceApiError(response.status, `Reference API returned HTTP ${response.status}`);
  return await response.json() as EtpProposalPayload;
}

export async function submitFxForwardProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<FxForwardProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/fx-forward-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as FxForwardProposalPayload;
}

export async function submitIndexProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<IndexProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/index-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as IndexProposalPayload;
}

export async function submitIndexFamilyProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<IndexFamilyProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/index-family-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as IndexFamilyProposalPayload;
}

export async function decideIndexFamilyProposal(proposalId: string, payload: { decision: "APPROVED" | "REJECTED"; reason: string }, options: EquityProposalOptions): Promise<IndexFamilyProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL(`/v1/index-family-proposals/${proposalId}/decision`, baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as IndexFamilyProposalPayload;
}

export async function submitIndexFamilyProposalFromBff(payload: Record<string, unknown>, fetchImpl: typeof fetch = fetch): Promise<IndexFamilyProposalPayload> {
  const response = await fetchImpl("/api/instruments/index-families", {
    method: "POST",
    cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Index-family proposal returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string; error?: { message?: string } };
      message = body.detail ?? body.error?.message ?? message;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as IndexFamilyProposalPayload;
}

export async function submitEquityListingProposal(payload: Record<string, unknown>, options: EquityProposalOptions): Promise<EquityProposalPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/listing-proposals", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as EquityProposalPayload;
}

export async function listMarketVenues(options: EquityProposalOptions): Promise<MarketVenuePayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/market-venues", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as MarketVenuePayload;
}

export async function listDayCountConventions(options: EquityProposalOptions): Promise<DayCountConventionPayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL("/v1/day-count-conventions", baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as DayCountConventionPayload;
}

async function listReferenceCatalogue<T>(path: string, options: EquityProposalOptions): Promise<T> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const url = new URL(path, baseUrl);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Tenant-Id": options.tenantId,
      "X-User-Account-Id": options.userAccountId,
      ...(options.correlationId ? { "X-Correlation-Id": options.correlationId } : {}),
    },
  });
  if (!response.ok) {
    let message = `Reference API returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export function listCurrencies(options: EquityProposalOptions, groups?: CurrencyGroupCode[]): Promise<CurrencyPayload> {
  const suffix = groups?.length ? `?groups=${encodeURIComponent(groups.join(","))}` : "";
  return listReferenceCatalogue<CurrencyPayload>(`/v1/currencies${suffix}`, options);
}

export function listReturnProfiles(options: EquityProposalOptions): Promise<ReturnProfilePayload> {
  return listReferenceCatalogue<ReturnProfilePayload>("/v1/return-profiles", options);
}

export function listIndexKinds(options: EquityProposalOptions): Promise<IndexKindPayload> {
  return listReferenceCatalogue<IndexKindPayload>("/v1/index-kind-catalogue", options);
}

export function listOrganisations(options: EquityProposalOptions, query = ""): Promise<OrganisationOptionPayload> {
  const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
  return listReferenceCatalogue<OrganisationOptionPayload>(`/v1/organisations${suffix}`, options);
}

export function listIndexFamilies(options: EquityProposalOptions): Promise<IndexFamilyPayload> {
  return listReferenceCatalogue<IndexFamilyPayload>("/v1/index-families", options);
}

/**
 * Browser-facing catalogue read. The browser must go through the Next BFF so
 * tenant headers and the upstream API base URL stay server-side and the UI is
 * not coupled to localhost/network topology.
 */
export async function listDayCountConventionsFromBff(fetchImpl: typeof fetch = fetch): Promise<DayCountConventionPayload> {
  const response = await fetchImpl("/api/day-count-conventions", {
    method: "GET",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    let message = `Day-count catalogue returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string; error?: { message?: string } };
      message = body.detail ?? body.error?.message ?? message;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as DayCountConventionPayload;
}

async function listCatalogueFromBff<T>(path: string, label: string, fetchImpl: typeof fetch): Promise<T> {
  const response = await fetchImpl(path, { method: "GET", cache: "no-store", headers: { Accept: "application/json" } });
  if (!response.ok) {
    let message = `${label} catalogue returned HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string; error?: { message?: string } };
      message = body.detail ?? body.error?.message ?? message;
    } catch {
      // Preserve the typed HTTP error when the upstream body is not JSON.
    }
    throw new ReferenceApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export function listCurrenciesFromBff(fetchImpl: typeof fetch = fetch, groups?: CurrencyGroupCode[]): Promise<CurrencyPayload> {
  const suffix = groups?.length ? `?groups=${encodeURIComponent(groups.join(","))}` : "";
  return listCatalogueFromBff<CurrencyPayload>(`/api/currencies${suffix}`, "Currency", fetchImpl);
}

export function listReturnProfilesFromBff(fetchImpl: typeof fetch = fetch): Promise<ReturnProfilePayload> {
  return listCatalogueFromBff<ReturnProfilePayload>("/api/return-profiles", "Return-profile", fetchImpl);
}

export function listIndexKindsFromBff(fetchImpl: typeof fetch = fetch): Promise<IndexKindPayload> {
  return listCatalogueFromBff<IndexKindPayload>("/api/index-kind-catalogue", "Index-kind", fetchImpl);
}

export function listOrganisationsFromBff(fetchImpl: typeof fetch = fetch): Promise<OrganisationOptionPayload> {
  return listCatalogueFromBff<OrganisationOptionPayload>("/api/organisations", "Organisation", fetchImpl);
}

export function listIndexFamiliesFromBff(fetchImpl: typeof fetch = fetch): Promise<IndexFamilyPayload> {
  return listCatalogueFromBff<IndexFamilyPayload>("/api/index-families", "Index-family", fetchImpl);
}
