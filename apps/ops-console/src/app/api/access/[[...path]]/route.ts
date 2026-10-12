import {NextRequest,NextResponse} from 'next/server';
import {accessProxy,sameOrigin} from '@/lib/server/access-proxy';
import {getActiveTenantContext} from '@/lib/tenant-session';
type Context={params:Promise<{path?:string[]}>};
async function handle(request:NextRequest,context:Context) {
  try {
    if(request.method!=='GET'){
      sameOrigin(request);
      const active=await getActiveTenantContext();
      if(request.headers.get('X-Expected-Tenant-Id')!==active.tenantId || request.headers.get('X-Expected-User-Id')!==active.userAccountId)
        return NextResponse.json({error:{message:'Tenant or user context changed. Reload before saving.'}},{status:409});
    }
    const {path=[]}=await context.params;
    const response=await accessProxy('/v1/access'+(path.length?'/'+path.map(encodeURIComponent).join('/'):''),{
      method:request.method,body:request.method==='GET'?undefined:await request.text()});
    return NextResponse.json(await response.json(),{status:response.status,headers:{'Cache-Control':'no-store'}});
  } catch {return NextResponse.json({error:{message:'Tenant administration is unavailable or not permitted for this user.'}},{status:403});}
}
export const GET=handle;
export const POST=handle;
export const PUT=handle;
