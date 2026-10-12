import {NextRequest,NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {bffErrorResponse} from '@/lib/bff-error';
export async function GET(request:NextRequest){
 try{const access=await resolveWorkspaceAccess();if(access.kind!=='ready')return NextResponse.json({error:{code:'WORKSPACE_ACCESS_REQUIRED'}},{status:access.kind==='session-required'?401:access.kind==='forbidden'?403:503});if(!access.workspace.moduleCodes.includes('MARKET_DATA'))return NextResponse.json({error:{code:'MARKET_DATA_REQUIRED'}},{status:403});const q=(request.nextUrl.searchParams.get('q')??'').slice(0,250);const result=await(await pricingPolicyClient()).GET('/v1/reference-nodes/search',{params:{query:{q,reference_level:'ANY',limit:10,offset:0}}});
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});}
 catch(e){return bffErrorResponse(e,'Reference search is unavailable. No fixture references are used.',request);}
}
