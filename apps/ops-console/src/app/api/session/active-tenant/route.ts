import { NextRequest, NextResponse } from "next/server";

import { selectActiveTenant } from "@/lib/tenant-session";

export async function GET() {
  const { getActiveTenantContext } = await import("@/lib/tenant-session");
  try {
    return NextResponse.json(await getActiveTenantContext());
  } catch {
    return NextResponse.json({ error: { code: "ACTIVE_TENANT_REQUIRED" } }, { status: 401 });
  }
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { tenantId?: string };
  if (!body.tenantId) return NextResponse.json({ error: { code: "TENANT_REQUIRED" } }, { status: 400 });
  try {
    const response = NextResponse.json(await selectActiveTenant(body.tenantId));
    response.cookies.set("active_tenant", body.tenantId, { httpOnly: true, sameSite: "lax", path: "/" });
    return response;
  } catch {
    return NextResponse.json({ error: { code: "TENANT_FORBIDDEN" } }, { status: 403 });
  }
}
