import { NextRequest, NextResponse } from "next/server";

import { listOrganisations } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.get("q") ?? "";
    if(query.length>250)return NextResponse.json({error:{message:"Search must be at most 250 characters."}},{status:400});
    return NextResponse.json(await listOrganisations(await getActiveTenantContext(), query));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
