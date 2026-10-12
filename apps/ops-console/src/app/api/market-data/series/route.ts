import { NextRequest, NextResponse } from "next/server";

import { getMarketDataSeries } from "@/lib/mvp-api-client";
import {requireReferenceTenantContext} from '@/lib/reference-tenant-context';
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  try {
    const context = await requireReferenceTenantContext();
    const payload = await getMarketDataSeries(context, { fromDate: params.get("fromDate") ?? undefined, toDate: params.get("toDate") ?? undefined, referenceNodeId: params.get("referenceNodeId") ?? undefined, seriesId: params.get("seriesId") ?? undefined, includeChart: params.get("includeChart") === "true", limit: Number(params.get("limit") ?? 12), offset:Number(params.get('offset') ?? 0), observationLimit:Number(params.get('observationLimit') ?? 1000), observationOffset:Number(params.get('observationOffset') ?? 0) });
    return NextResponse.json(payload);
  } catch (error) {
    return bffErrorResponse(error, "Market-data service is unavailable.", request, "MARKET_DATA_API_UNAVAILABLE");
  }
}
