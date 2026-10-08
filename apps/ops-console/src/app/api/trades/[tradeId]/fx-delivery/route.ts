import {NextRequest,NextResponse} from 'next/server';
import type {components} from 'api-contracts';
import {readBookingWrite} from '@/lib/booking-write-guard';
import {recordFxDelivery} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function POST(request:NextRequest,{params}:{params:Promise<{tradeId:string}>}) {
 const envelope=await readBookingWrite(request);if(envelope.response)return envelope.response;
 try{return NextResponse.json(await recordFxDelivery((await params).tradeId,envelope.payload as components['schemas']['DeliveryRequest'],envelope.context,envelope.key));}
 catch(error){return bffErrorResponse(error,'FX delivery service is unavailable',request,'FX_DELIVERY_API_UNAVAILABLE');}
}
