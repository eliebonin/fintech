import {NextRequest,NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
type Context={params:Promise<{path?:string[]}>};
export async function GET(request:NextRequest,context:Context) {
 try{
  const path=(await context.params).path??[],client=await pricingPolicyClient();
  if(path.length===1&&path[0]==='options'){
   const result=await client.GET('/v1/market-data/calendars/options');return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
  }
  if(path.length===1){
   const result=await client.GET('/v1/market-data/calendars/{calendar_id}',{params:{path:{calendar_id:path[0]}}});return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
  }
  if(path.length===2&&path[1]==='days'){
   const fromDate=request.nextUrl.searchParams.get('fromDate'),toDate=request.nextUrl.searchParams.get('toDate');
   if(!fromDate||!toDate)return NextResponse.json({error:{message:'From and to dates are required.'}},{status:400});
   const result=await client.GET('/v1/market-data/calendars/{calendar_id}/days',{params:{path:{calendar_id:path[0]},query:{fromDate,toDate}}});return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
  }
  return NextResponse.json({error:{message:'Calendar route not found.'}},{status:404});
 }catch(error){return bffErrorResponse(error,'Calendar service is unavailable.',request);}
}
export async function POST(request:NextRequest,context:Context) {
 const key=request.headers.get('Idempotency-Key');
 if(!key?.trim()||key.length>255)return NextResponse.json({error:{message:'A stable submission key is required.'}},{status:400});
 try{
  const path=(await context.params).path??[],client=await pricingPolicyClient(),body=await request.json();
  if(path.length===0){const result=await client.POST('/v1/market-data/calendars',{body,params:{header:{'Idempotency-Key':key}}});return NextResponse.json(result.data??{error:result.error},{status:result.response.status});}
  if(path.length===1&&path[0]==='assignments'){const result=await client.POST('/v1/market-data/calendars/assignments',{body,params:{header:{'Idempotency-Key':key}}});return NextResponse.json(result.data??{error:result.error},{status:result.response.status});}
  return NextResponse.json({error:{message:'Calendar route not found.'}},{status:404});
 }catch(error){return bffErrorResponse(error,'Submission outcome is uncertain. Retry unchanged with the same key.',request);}
}
