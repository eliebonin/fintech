import { ReferenceApiError, type ReferenceApiMeta } from "./reference-api-client";
import type { TenantContext } from "./tenant-context";
import { referenceFetch } from './reference-fetch';

export type WorkQueueItem = {
  itemId: string;
  category: "MAPPING_REVIEW" | "REFERENCE_DATA_REVIEW" | "NAV_REVIEW" | "MARKET_DATA_EXCEPTION";
  title: string;
  detail: string;
  status: string;
  proposalType?: string | null;
  proposedAt?: string | null;
  submittedByUserAccountId?: string | null;
  referenceId?: string;
  reviewPath?: string | null;
};

export type WorkQueuePayload = {
  counts: Record<WorkQueueItem["category"], number>;
  items: WorkQueueItem[];
  meta: ReferenceApiMeta;
};

export type WorkQueueOptions = Pick<TenantContext, "tenantId" | "userAccountId"> & {
  baseUrl?: string;
  correlationId?: string;
  fetchImpl?: typeof fetch;
  limit?: number;
  offset?: number;
};

export async function getWorkQueue(options: WorkQueueOptions): Promise<WorkQueuePayload> {
  const baseUrl = options.baseUrl ?? process.env.REFERENCE_API_URL ?? "http://localhost:8000";
  const fetchImpl = options.fetchImpl ?? referenceFetch();
  const url = new URL('/v1/work-queue',baseUrl);
  if(options.limit!==undefined)url.searchParams.set('limit',String(options.limit));
  if(options.offset!==undefined)url.searchParams.set('offset',String(options.offset));
  const response = await fetchImpl(url, {
    method: "GET",
    cache: "no-store",
    signal: AbortSignal.timeout(35000),
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
  return (await response.json()) as WorkQueuePayload;
}
