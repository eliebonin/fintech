import {NextRequest} from 'next/server';
import {describe,it,expect,vi,afterEach} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'selected-tenant',userAccountId:'selected-actor',source:'local-session'})}));
import {GET,POST} from './route';
const context=(path:string)=>({params:Promise.resolve({path:path.split('/')})});
afterEach(()=>vi.unstubAllGlobals());
describe('trade import transport',()=>{
 it('rejects stale tenant context before any write',async()=>{
  const upstream=vi.fn();vi.stubGlobal('fetch',upstream);
  const result=await POST(new NextRequest('http://test/api/trade-imports/create',{method:'POST',headers:{'X-Expected-Tenant-Id':'old-tenant','Idempotency-Key':'same-key'},body:'{}'}),context('create'));
  expect(result.status).toBe(409);expect(upstream).not.toHaveBeenCalled();
 });
 it('forwards exact write intent and trusted identity',async()=>{
  let sent:RequestInit|undefined;
  vi.stubGlobal('fetch',async(_input:unknown,init:RequestInit)=>{sent=init;return new Response(JSON.stringify({jobId:'retained'}),{status:201,headers:{'X-Request-Id':'upstream-id'}});});
  const result=await POST(new NextRequest('http://test/api/trade-imports/create',{method:'POST',headers:{'X-Expected-Tenant-Id':'selected-tenant','Idempotency-Key':'retained-key','X-User-Account-Id':'forged'},body:JSON.stringify({source:'my-source'})}),context('create'));
  expect(result.status).toBe(201);expect(result.headers.get('X-Request-Id')).toBe('upstream-id');
  expect(new Headers(sent?.headers).get('X-User-Account-Id')).toBe('selected-actor');
  expect(new Headers(sent?.headers).get('Idempotency-Key')).toBe('retained-key');
  expect(sent?.body).toBe('{"source":"my-source"}');
 });
 it('preserves private binary downloads instead of trying to parse JSON',async()=>{
  vi.stubGlobal('fetch',async()=>new Response(new Uint8Array([0,1,2]),{headers:{'Content-Type':'application/octet-stream','Content-Disposition':'attachment; filename="template.xlsx"'}}));
  const result=await GET(new NextRequest('http://test/api/trade-imports/template?strategyId=s'),context('template'));
  expect(result.headers.get('Cache-Control')).toBe('private, no-store');
  expect([...new Uint8Array(await result.arrayBuffer())]).toEqual([0,1,2]);
 });
 it('allows no arbitrary upstream paths',async()=>{
  const upstream=vi.fn();vi.stubGlobal('fetch',upstream);
  const result=await GET(new NextRequest('http://test/api/trade-imports/secm/private'),context('secm/private'));
  expect(result.status).toBe(404);expect(upstream).not.toHaveBeenCalled();
 });
});
