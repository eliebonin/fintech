import { NextResponse } from "next/server";

export async function GET() {
  const response = await fetch(new URL("/v1/session/memberships", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), {
    headers: { "X-User-Account-Id": process.env.DEMO_USER_ACCOUNT_ID ?? "00000000-0000-7000-8000-000000000083" },
    cache: "no-store",
  });
  if (!response.ok) return NextResponse.json({ error: { code: "MEMBERSHIPS_UNAVAILABLE" } }, { status: response.status });
  return NextResponse.json(await response.json());
}
