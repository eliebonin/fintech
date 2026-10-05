import { NextRequest, NextResponse } from "next/server";

import { bffErrorResponse } from "@/lib/bff-error";
import { bookListedCashTrade, type TradeBookingRequest } from "@/lib/reference-api-client";
import {readBookingWrite} from '@/lib/booking-write-guard';

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const envelope=await readBookingWrite(request,true);
  if(envelope.response)return envelope.response;
  try {
    return NextResponse.json(await bookListedCashTrade(envelope.payload as TradeBookingRequest, envelope.context, envelope.key), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Trade booking service is unavailable", request, "TRADE_BOOKING_API_UNAVAILABLE");
  }
}
