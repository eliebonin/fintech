import { NextRequest, NextResponse } from "next/server";

import { getPortfolioPnl } from "@/lib/mvp-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

const PORTFOLIO_ALIASES: Record<string, string> = {
  uk: "MVP_UK_PORTFOLIO",
  us: "MVP_US_PORTFOLIO",
};

export async function GET(request: NextRequest, { params }: { params: Promise<{ portfolio: string }> }) {
  const context = resolveLocalTenantContext();
  const { portfolio } = await params;
  const asOfDate = request.nextUrl.searchParams.get("asOfDate") ?? "2026-08-28";
  try {
    const portfolioCode = PORTFOLIO_ALIASES[portfolio.toLowerCase()] ?? portfolio;
    return NextResponse.json(await getPortfolioPnl(context, portfolioCode, asOfDate));
  } catch (error) {
    return bffErrorResponse(error, "Portfolio P&L service is unavailable.", request, "PORTFOLIO_PNL_API_UNAVAILABLE");
  }
}
