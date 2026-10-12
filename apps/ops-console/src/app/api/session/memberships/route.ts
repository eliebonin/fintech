import { NextResponse } from "next/server";
import { apiRead } from "@/lib/server/api-read";
import { cookies } from 'next/headers';
import {getActiveTenantContext} from '@/lib/tenant-session';
export async function GET() {
  try {
    const selected=(await cookies()).get('local_access_session')?.value?await getActiveTenantContext():null;
    const response = await apiRead(new URL("/v1/session/memberships", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), {
      headers: { "X-User-Account-Id": selected?.userAccountId??process.env.DEMO_USER_ACCOUNT_ID ?? "00000000-0000-7000-8000-000000000083",...(selected?{'X-Tenant-Id':selected.tenantId}:{}) }, cache: "no-store",
    });
    if (!response.ok) return NextResponse.json({ error: { code: "MEMBERSHIPS_UNAVAILABLE" } }, { status: response.status });
    return NextResponse.json(await response.json());
  } catch { return NextResponse.json({ error: { code: "MEMBERSHIPS_UNAVAILABLE" } }, { status: 503 }); }
}
