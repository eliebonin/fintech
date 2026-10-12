import { SessionRequiredError, WorkspaceApiError } from "@/lib/server/workspace-errors";
import { NextRequest, NextResponse } from "next/server";

import { selectActiveTenant, signActiveTenantId } from "@/lib/tenant-session";

export async function GET() {
  const { getActiveTenantWorkspace } = await import("@/lib/tenant-session");
  try {
    return NextResponse.json(await getActiveTenantWorkspace());
  } catch (error) {
    const status = error instanceof SessionRequiredError ? 401 : error instanceof WorkspaceApiError ? error.status : 503;
    return NextResponse.json({ error: { code: status === 401 ? "ACTIVE_TENANT_REQUIRED" : status === 403 ? "TENANT_FORBIDDEN" : "WORKSPACE_UNAVAILABLE" } }, { status });
  }
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { tenantId?: string };
  if (!body.tenantId) return NextResponse.json({ error: { code: "TENANT_REQUIRED" } }, { status: 400 });
  try {
    const response = NextResponse.json(await selectActiveTenant(body.tenantId));
    response.cookies.set("active_tenant", signActiveTenantId(body.tenantId), { httpOnly: true, sameSite: "lax", path: "/" });
    response.headers.set("X-Tenant-Context-Changed", "1");
    return response;
  } catch (error) {
    const status = error instanceof WorkspaceApiError ? error.status : 503;
    return NextResponse.json({ error: { code: status >= 500 ? "WORKSPACE_UNAVAILABLE" : "TENANT_FORBIDDEN" } }, { status });
  }
}
