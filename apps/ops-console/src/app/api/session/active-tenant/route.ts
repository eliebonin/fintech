import { SessionRequiredError, WorkspaceApiError } from "@/lib/server/workspace-errors";
import { NextResponse } from "next/server";

export async function GET() {
  const { getActiveTenantWorkspace } = await import("@/lib/tenant-session");
  try {
    return NextResponse.json(await getActiveTenantWorkspace());
  } catch (error) {
    const status = error instanceof SessionRequiredError ? 401 : error instanceof WorkspaceApiError ? error.status : 503;
    return NextResponse.json({ error: { code: status === 401 ? "ACTIVE_TENANT_REQUIRED" : status === 403 ? "TENANT_FORBIDDEN" : "WORKSPACE_UNAVAILABLE" } }, { status });
  }
}

export async function POST() {
  return NextResponse.json({error:{code:'CONTEXT_SELECTION_REQUIRED',message:'Select a tenant and user at /select-context.'}},
    {status:410,headers:{'Cache-Control':'no-store'}});
}
