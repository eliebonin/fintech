import { NextResponse } from "next/server";
import { apiRead } from "@/lib/server/api-read";
import {getActiveTenantContext} from '@/lib/tenant-session';
import {SessionRequiredError,WorkspaceApiError} from '@/lib/server/workspace-errors';
export async function GET() {
  try {
    const selected=await getActiveTenantContext();
    const response = await apiRead(new URL("/v1/session/memberships", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), {
      headers: { "X-User-Account-Id": selected.userAccountId,'X-Tenant-Id':selected.tenantId }, cache: "no-store",redirect:'error',
    });
    if (!response.ok) return NextResponse.json({ error: { code: "MEMBERSHIPS_UNAVAILABLE" } }, { status: response.status });
    return NextResponse.json(await response.json());
  } catch(error) { return NextResponse.json({ error: { code: error instanceof SessionRequiredError?'ACTIVE_TENANT_REQUIRED':'MEMBERSHIPS_UNAVAILABLE' } },
    { status:error instanceof SessionRequiredError?401:error instanceof WorkspaceApiError?error.status:503 }); }
}
