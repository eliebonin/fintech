import { NextRequest, NextResponse } from "next/server";
import { bffErrorResponse } from "@/lib/bff-error";
import { bookFxForwardTrade } from "@/lib/reference-api-client";
import {readBookingWrite} from '@/lib/booking-write-guard';
export const dynamic = "force-dynamic";
export async function POST(request:NextRequest) {
  const envelope=await readBookingWrite(request);if(envelope.response)return envelope.response;
  try{return NextResponse.json(await bookFxForwardTrade(envelope.payload as Parameters<typeof bookFxForwardTrade>[0],envelope.context,envelope.key),{status:201});}
  catch(error){return bffErrorResponse(error,"FX-forward booking service is unavailable",request,"TRADE_BOOKING_API_UNAVAILABLE");}
}
