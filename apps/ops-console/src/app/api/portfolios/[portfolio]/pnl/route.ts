import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** A non-financial tombstone only: do not forward aliases to the retired API. */
export async function GET(request: NextRequest, _context: { params: Promise<{ portfolio: string }> }) {
  return NextResponse.json({
    type: "https://api.fortem.local/problems/valuation-demo-retired",
    title: "Legacy P&L demonstration retired",
    status: 410,
    code: "valuation.demo_retired",
    detail: "The legacy calculator has been removed. The new valuation/P&L engine is not implemented yet.",
    instance: request.nextUrl.pathname,
  }, { status: 410, headers: { "Cache-Control": "no-store" } });
}
