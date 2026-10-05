import { NextRequest,NextResponse } from 'next/server';
import { bffErrorResponse } from '@/lib/bff-error';
import { bookOptionTrade } from '@/lib/reference-api-client';
import {readBookingWrite} from '@/lib/booking-write-guard';
export const dynamic='force-dynamic';
export async function POST(request:NextRequest) {
  const envelope=await readBookingWrite(request);if(envelope.response)return envelope.response;
  try{return NextResponse.json(await bookOptionTrade(envelope.payload as Parameters<typeof bookOptionTrade>[0],envelope.context,envelope.key),{status:201});}
  catch(error){return bffErrorResponse(error,'Option booking is unavailable',request,'TRADE_BOOKING_API_UNAVAILABLE');}
}
