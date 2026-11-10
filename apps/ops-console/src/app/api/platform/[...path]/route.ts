import {NextRequest,NextResponse} from 'next/server';
import {accessProxy,sameOrigin} from '@/lib/server/access-proxy';
type Context={params:Promise<{path:string[]}>};
async function handle(request:NextRequest,context:Context) {
  try {
    if(request.method!=='GET')sameOrigin(request);
    const {path}=await context.params;
    const response=await accessProxy('/v1/platform/'+path.map(encodeURIComponent).join('/'),{
      method:request.method,body:request.method==='GET'?undefined:await request.text()},'platform');
    return NextResponse.json(await response.json(),{status:response.status,headers:{'Cache-Control':'no-store'}});
  } catch {return NextResponse.json({error:{message:'Platform administration requires platform context and a same-origin request.'}},{status:403});}
}
export const GET=handle;
export const PUT=handle;

export async function POST(request:NextRequest,context:Context){
 const parts=(await context.params).path;
 if(!/^tenants\/[0-9a-fA-F-]{36}\/lifecycle-subscription\/preview$/.test(parts.join('/')))return NextResponse.json({error:{message:'Unknown platform preview.'}},{status:404});
 return handle(request,context);
}
