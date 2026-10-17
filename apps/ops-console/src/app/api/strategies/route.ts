import { NextRequest, NextResponse } from "next/server";

import { getActiveTenantContext } from "@/lib/tenant-session";
import {referenceFetch} from '@/lib/reference-fetch';
import {readWriteContext} from '@/lib/server/write-context';

const baseUrl = process.env.REFERENCE_API_URL ?? "http://localhost:8000";

async function tenantHeaders() {
  const context = await getActiveTenantContext();
  return { Accept: "application/json", "Content-Type": "application/json", "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId };
}

export async function GET() {
  let headers;
  try {
    headers = await tenantHeaders();
  } catch {
    return NextResponse.json({ error: { code: "ACTIVE_TENANT_REQUIRED" } }, { status: 401 });
  }
  try {
    const response = await referenceFetch()(new URL("/v1/strategies", baseUrl), { headers, cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: { code: "STRATEGIES_UNAVAILABLE" } }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const checked=await readWriteContext(request);
  if(checked.response)return checked.response;
  const headers={Accept:'application/json','Content-Type':'application/json',
    'X-Tenant-Id':checked.context.tenantId,'X-User-Account-Id':checked.context.userAccountId};
  let payload:unknown;
  try{payload=await request.json();}
  catch{return NextResponse.json({error:{code:'INVALID_JSON',message:'Request body must be valid JSON.'}},{status:400});}
  try {
    const response = await referenceFetch()(new URL("/v1/strategies", baseUrl), { method: "POST", headers, body: JSON.stringify(payload), cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: { code: "STRATEGIES_UNAVAILABLE" } }, { status: 502 });
  }
}
