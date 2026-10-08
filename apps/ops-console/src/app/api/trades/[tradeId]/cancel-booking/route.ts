import {NextRequest,NextResponse} from 'next/server';
import {readBookingWrite} from '@/lib/booking-write-guard';
import {cancelBookingRecord} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function POST(request:NextRequest,{params}:{params:Promise<{tradeId:string}>}) {
 const envelope=await readBookingWrite(request);if(envelope.response)return envelope.response;
 try{return NextResponse.json(await cancelBookingRecord((await params).tradeId,envelope.payload as {expectedSequenceNo:number;reason:string},envelope.context,envelope.key));}
 catch(error){return bffErrorResponse(error,'Booking correction service is unavailable',request,'TRADE_CORRECTION_API_UNAVAILABLE');}
}
