import {NextRequest,NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {bffErrorResponse} from '@/lib/bff-error';
export async function GET(request:NextRequest){
 try{const access=await resolveWorkspaceAccess();if(access.kind!=='ready')return NextResponse.json({error:{code:'WORKSPACE_ACCESS_REQUIRED'}},{status:access.kind==='session-required'?401:access.kind==='forbidden'?403:503});if(!access.workspace.moduleCodes.includes('MARKET_DATA'))return NextResponse.json({error:{code:'MARKET_DATA_REQUIRED'}},{status:403});
  const raw=request.nextUrl.searchParams.get('ids');
  if(raw!==null){
   const ids=[...new Set(raw.split(','))];
   if(!ids.length||ids.length>20||ids.some(id=>!/^\b[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)))return NextResponse.json({error:{code:'INVALID_REFERENCE_IDS'}},{status:400});
   const client=await pricingPolicyClient();const labels:Record<string,string>={};
   // Bounded fan-out reuses one access/client context. Upstream still checks each read.
   for(let index=0;index<ids.length;index+=4){await Promise.all(ids.slice(index,index+4).map(async id=>{
    const result=await client.GET('/v1/reference-nodes/search',{params:{query:{q:id,reference_level:'ANY',limit:10,offset:0}}});
    if(!result.response.ok)return;const exact=result.data?.data.find(row=>row.referenceNodeId===id);if(exact)labels[id]=exact.canonicalName;
   }));}
   return NextResponse.json({labels},{headers:{'Cache-Control':'no-store'}});
  }
  const q=(request.nextUrl.searchParams.get('q')??'').slice(0,250);const result=await(await pricingPolicyClient()).GET('/v1/reference-nodes/search',{params:{query:{q,reference_level:'ANY',limit:10,offset:0}}});
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});}
 catch(e){return bffErrorResponse(e,'Reference search is unavailable. No fixture references are used.',request);}
}
