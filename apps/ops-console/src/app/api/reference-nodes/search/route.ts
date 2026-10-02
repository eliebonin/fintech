import { NextRequest, NextResponse } from "next/server";

import { searchInstruments } from "@/lib/instrument-data";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { searchReferenceNodes } from "@/lib/reference-api-client";
import type { ReferenceNodeOption } from "api-contracts";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

function splitFilter(value: string | undefined): string[] {
  return (value ?? "")
    .split(",")
    .map((part) => part.trim().toUpperCase())
    .filter(Boolean);
}

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const query = params.get("q") ?? "";
  const nodeType = params.get("node_type") ?? undefined;
  const instrumentType = params.get("instrument_type") ?? undefined;
  const assetClass = params.get("asset_class") ?? undefined;
  const referenceLevel = params.get("reference_level") as "ANY" | "ECONOMIC" | "LISTING" | null;
  const limit = params.get("limit") ?? undefined;
  const offset = params.get("offset") ?? undefined;
  let context;
  try { context = await getActiveTenantContext(); }
  catch { return NextResponse.json({error:{code:'ACTIVE_TENANT_REQUIRED'}},{status:401}); }

  return searchReferenceNodes(query, {
    ...context,
    nodeType,
    instrumentType,
    assetClass,
    referenceLevel: referenceLevel ?? undefined,
    limit: limit ? Number(limit) : undefined,
    offset: offset ? Number(offset) : undefined,
  })
    .then((payload) => NextResponse.json(payload))
    .catch((error: unknown) => {
      const localFallbackAllowed = process.env.APP_ENV !== "production" && process.env.ALLOW_SYNTHETIC_FALLBACK !== "false";
      if (!localFallbackAllowed) {
        return bffErrorResponse(error, "Reference data service is unavailable", request, "REFERENCE_API_UNAVAILABLE");
      }

      const requestedNodeTypes = splitFilter(nodeType);
      const requestedInstrumentTypes = splitFilter(instrumentType);
      const data: ReferenceNodeOption[] = searchInstruments(query)
        .filter((item) => {
          const nodeMatch = requestedNodeTypes.length === 0 || requestedNodeTypes.includes("INSTRUMENT");
          const instrumentMatch = requestedInstrumentTypes.length === 0 || requestedInstrumentTypes.includes(item.instrumentType);
          return requestedNodeTypes.length > 0 && requestedInstrumentTypes.length > 0
            ? nodeMatch || instrumentMatch
            : nodeMatch && instrumentMatch;
        })
        .filter((item) => !assetClass || item.assetClass === assetClass.toUpperCase())
        .flatMap<ReferenceNodeOption>((item) => referenceLevel === "LISTING"
          ? item.listings.map((listing) => ({
            referenceNodeId: listing.listingId,
            canonicalName: `${item.canonicalName} — ${listing.marketVenueMic} · ${listing.tradingSymbol}`,
            internalCode: listing.listingId,
            nodeType: "LISTING",
            instrumentType: item.instrumentType,
            assetClass: item.assetClass,
            baseCurrency: item.baseCurrency,
            status: listing.status,
            isTradable: true,
            parentReferenceNodeId: item.instrumentId,
            marketVenueMic: listing.marketVenueMic,
            venueName: listing.venueName,
            tradingSymbol: listing.tradingSymbol,
            tradingCurrency: listing.tradingCurrency,
          }))
          : [{
          referenceNodeId: item.instrumentId,
          canonicalName: item.canonicalName,
          internalCode: item.instrumentId,
          nodeType: "INSTRUMENT",
          instrumentType: item.instrumentType,
          assetClass: item.assetClass,
          baseCurrency: item.baseCurrency,
          status: item.status,
          isTradable: item.listings.length > 0,
        }])
        .filter((item) => referenceLevel !== "ECONOMIC" || item.nodeType !== "LISTING")
        .slice(Number(offset ?? 0), Number(offset ?? 0) + Number(limit ?? 50));

      return NextResponse.json({
        data,
        meta: {
          tenantContext: context.tenantId,
          source: "synthetic-fixture-fallback",
          apiVersion: "fixture-v1",
          correlationId: request.headers.get("X-Correlation-Id") ?? crypto.randomUUID(),
          warning: "Reference API unavailable; only instrument fixtures are shown for local development.",
        },
      });
    });
}
