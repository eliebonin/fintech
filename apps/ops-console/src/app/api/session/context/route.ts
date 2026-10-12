import {NextRequest,NextResponse} from 'next/server';
import {accessProxy,requireLocalMode,sameOrigin} from '@/lib/server/access-proxy';

export async function GET() {
  try {
    const response=await accessProxy('/v1/local-session/options',{},'operator');
    return NextResponse.json(await response.json(),{status:response.status,headers:{'Cache-Control':'no-store'}});
  } catch {return NextResponse.json({error:{message:'Context selection is unavailable. This is a local-development feature.'}},{status:403});}
}

export async function POST(request:NextRequest) {
  try {requireLocalMode();sameOrigin(request);} catch {return NextResponse.json({error:{message:'Local same-origin context selection is required.'}},{status:403});}
  try {
    const body=await request.json();
    const response=await accessProxy('/v1/local-session',{method:'POST',body:JSON.stringify(body)},'operator');
    const result=await response.json() as {token?:string;context?:unknown;error?:unknown};
    if (!response.ok) return NextResponse.json(result,{status:response.status});
    if (!result.token) return NextResponse.json({error:{message:'Context could not be verified.'}},{status:502});
    const output=NextResponse.json({context:result.context});
    output.cookies.set('local_access_session',result.token,{httpOnly:true,sameSite:'strict',path:'/',maxAge:4*60*60});
    output.cookies.set('active_tenant','',{httpOnly:true,path:'/',maxAge:0});
    output.headers.set('X-Tenant-Context-Changed','1');
    return output;
  } catch {return NextResponse.json({error:{message:'Context switch failed; your existing context is unchanged.'}},{status:503});}
}

export async function DELETE(request:NextRequest) {
  try {
    requireLocalMode();sameOrigin(request);
    const response=await accessProxy('/v1/local-session',{method:'DELETE'},'operator');
    if (!response.ok) return NextResponse.json(await response.json(),{status:response.status});
    const output=NextResponse.json({ended:true});
    output.cookies.set('local_access_session','',{httpOnly:true,sameSite:'strict',path:'/',maxAge:0});
    output.cookies.set('active_tenant','',{httpOnly:true,path:'/',maxAge:0});
    return output;
  } catch { return NextResponse.json({error:{message:'Unable to reset the local testing session.'}},{status:403}); }
}
