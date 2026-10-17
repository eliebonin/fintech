import {NextRequest,NextResponse} from 'next/server';
import {contextFingerprint} from './lib/server/context-fingerprint';

export function proxy(request:NextRequest){
 const path=request.nextUrl.pathname;
 if(['GET','HEAD','OPTIONS'].includes(request.method)||['/api/session/context','/api/session/active-tenant'].includes(path))return NextResponse.next();
 const current=contextFingerprint(request.cookies.get('local_access_session')?.value,request.cookies.get('active_tenant')?.value);
 if(!current||request.headers.get('X-Page-Context')!==current)return NextResponse.json({error:{
  code:'TENANT_CONTEXT_CHANGED',message:'Your tenant or user context changed, or this page is out of date. Reload before saving. This attempt was not forwarded.',retryable:false}},
  {status:409,headers:{'Cache-Control':'no-store'}});
 return NextResponse.next();
}
export const config={matcher:'/api/:path*'};
