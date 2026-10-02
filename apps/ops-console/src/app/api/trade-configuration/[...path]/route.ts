import { NextRequest, NextResponse } from "next/server";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { ReferenceApiError } from "@/lib/reference-api-client";
import { bffErrorResponse } from "@/lib/bff-error";
export const dynamic = "force-dynamic";
const uuid = "[0-9a-fA-F-]{36}";
function allowedConfigurationPath(path:string,method:string) {
  const reads=[/^properties$/, /^catalogues$/,new RegExp(`^catalogues/${uuid}$`),new RegExp(`^catalogues/${uuid}/records$`),/^selections\/(COUNTERPARTY|EXECUTING_BROKER|TRADER)$/,/^candidates\/(COUNTERPARTY|EXECUTING_BROKER|TRADER)$/,/^audit$/];
  const writes=[/^properties$/,new RegExp(`^properties/${uuid}/(retire|replace)$`),/^catalogues$/,new RegExp(`^catalogues/${uuid}/(publish|retire|records)$`),new RegExp(`^catalogues/${uuid}/records/${uuid}/(correct|retire)$`),/^selections\/(COUNTERPARTY|EXECUTING_BROKER|TRADER)$/];
  return (method==="GET"?reads:writes).some(pattern=>pattern.test(path));
}
async function proxy(request:NextRequest,ctx:{params:Promise<{path:string[]}>}) {
  const path=(await ctx.params).path.join("/");
  if(!allowedConfigurationPath(path,request.method))return NextResponse.json({error:{message:"Unknown configuration action."}},{status:404});
  try {
    const context=await getActiveTenantContext();
    if(request.headers.get("X-Expected-Tenant-Id")!==context.tenantId)return NextResponse.json({error:{message:"Tenant context changed. Reload this page."}},{status:409});
    const response=await fetch(new URL(`/v1/trade-configuration/${path}${request.nextUrl.search}`,process.env.REFERENCE_API_URL??"http://localhost:8000"),{
      method:request.method,cache:"no-store",headers:{"Content-Type":"application/json","X-Tenant-Id":context.tenantId,"X-User-Account-Id":context.userAccountId},
      ...(request.method==="POST"?{body:JSON.stringify(await request.json())}:{}),
    });
    const result=await response.json();
    if(!response.ok)throw new ReferenceApiError(response.status,result.detail??"Configuration request failed.",result.code??"configuration.failed");
    return NextResponse.json(result,{status:response.status});
  }catch(error){return bffErrorResponse(error,"Trade configuration is unavailable.",request);}
}
export const GET=proxy;
export const POST=proxy;
