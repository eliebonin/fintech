import {NextRequest,NextResponse} from 'next/server';
import {contextFingerprint} from './lib/server/context-fingerprint';
import {securityHeaders} from './lib/security-headers';

export function proxy(request:NextRequest){
 const bytes=crypto.getRandomValues(new Uint8Array(18));
 const nonce=btoa(String.fromCharCode(...bytes));
 const protections=securityHeaders(nonce,request.nextUrl);
 const forwarded=new Headers(request.headers);
 forwarded.set('x-nonce',nonce);
 forwarded.set('Content-Security-Policy',protections['Content-Security-Policy']);
 const finish=(response:NextResponse)=>{Object.entries(protections).forEach(([key,value])=>response.headers.set(key,value));return response;};
 const path=request.nextUrl.pathname;
 if(!path.startsWith('/api/')||['GET','HEAD','OPTIONS'].includes(request.method)||['/api/session/context','/api/session/active-tenant'].includes(path))return finish(NextResponse.next({request:{headers:forwarded}}));
 const current=contextFingerprint(request.cookies.get('local_access_session')?.value,request.cookies.get('active_tenant')?.value);
 if(!current||request.headers.get('X-Page-Context')!==current)return finish(NextResponse.json({error:{
  code:'TENANT_CONTEXT_CHANGED',message:'Your tenant or user context changed, or this page is out of date. Reload before saving. This attempt was not forwarded.',retryable:false}},
  {status:409,headers:{'Cache-Control':'no-store'}}));
 return finish(NextResponse.next({request:{headers:forwarded}}));
}
export const config={matcher:['/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)']};
