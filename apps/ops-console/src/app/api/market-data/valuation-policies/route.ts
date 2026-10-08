import { NextRequest, NextResponse } from "next/server";

import { bffErrorResponse } from "@/lib/bff-error";
import { pricingPolicyClient } from "@/lib/pricing-policy-api";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const valuationDate = request.nextUrl.searchParams.get("valuationDate");
  if (!valuationDate) return NextResponse.json({ error: { code: "VALUATION_DATE_REQUIRED" } }, { status: 400 });
  try {
    const client = await pricingPolicyClient();
    const result = await client.GET("/v1/market-data/valuation-policies", { params: { query: { valuationDate } } });
    if (result.error || !result.data) return NextResponse.json({ error: result.error ?? { code: "MARKET_DATA_API_ERROR" } }, { status: result.response.status });
    return NextResponse.json(result.data);
  } catch (error) {
    return bffErrorResponse(error, "Market-data policy service is unavailable.", request, "MARKET_DATA_POLICY_API_UNAVAILABLE");
  }
}

export async function POST(request: NextRequest) {
  const key=request.headers.get('Idempotency-Key');
  if(!key?.trim()||key.length>255)return NextResponse.json({error:{message:'A stable submission key is required.'}},{status:400});
  try {
    const result=await (await pricingPolicyClient()).POST('/v1/market-data/valuation-policies',{
      body:await request.json(),params:{header:{'Idempotency-Key':key}}});
    return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
  }catch(error){return bffErrorResponse(error,'Policy submission outcome is uncertain. Retry unchanged with the same key.',request);}
}
