import { NextRequest, NextResponse } from "next/server";

import { bffErrorResponse } from "@/lib/bff-error";
import {pricingPolicyClient} from '@/lib/pricing-policy-api';

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, { params }: { params: Promise<{ snapshotId: string }> }) {
  const { snapshotId } = await params;
  try {
    const client = await pricingPolicyClient();
    const result = await client.GET("/v1/market-data-resolution-snapshots/{snapshot_id}", { params: { path: { snapshot_id: snapshotId } } });
    if (result.error || !result.data) return NextResponse.json({ error: result.error ?? { code: "MARKET_DATA_API_ERROR" } }, { status: result.response.status });
    return NextResponse.json(result.data);
  } catch (error) {
    return bffErrorResponse(error, "Market-data resolution service is unavailable.", request, "MARKET_DATA_RESOLUTION_API_UNAVAILABLE");
  }
}
