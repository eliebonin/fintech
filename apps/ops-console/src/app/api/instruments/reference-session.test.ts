import {NextRequest} from 'next/server';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
const session=vi.hoisted(()=>({get:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:session.get}));
import {POST as bond} from './bond-proposals/route';
import {POST as crypto} from './crypto-assets/route';
import {GET as cryptoDetail} from './crypto-assets/[proposalId]/route';
import {POST as cryptoDecision} from './crypto-assets/[proposalId]/decision/route';
import {POST as equity} from './equities/route';
import {POST as etp} from './etps/route';
import {POST as fx} from './fx-forwards/route';
import {POST as family} from './index-families/route';
import {POST as familyDecision} from './index-families/[proposalId]/decision/route';
import {POST as index} from './indices/route';
import {POST as structured} from './structured-products/route';
import {GET as queue} from '../work-queue/route';

const cases=[
 {name:'bond',handler:bond,path:'/v1/bond-proposals'},
 {name:'crypto',handler:crypto,path:'/v1/crypto-asset-proposals'},
 {name:'crypto detail',handler:cryptoDetail,path:'/v1/crypto-asset-proposals/proposal',read:true},
 {name:'crypto decision',handler:cryptoDecision,path:'/v1/crypto-asset-proposals/proposal/decision'},
 {name:'equity',handler:equity,path:'/v1/equity-proposals'},
 {name:'ETP',handler:etp,path:'/v1/etp-proposals'},
 {name:'FX',handler:fx,path:'/v1/fx-forward-proposals'},
 {name:'index family',handler:family,path:'/v1/index-family-proposals'},
 {name:'index family decision',handler:familyDecision,path:'/v1/index-family-proposals/proposal/decision'},
 {name:'index',handler:index,path:'/v1/index-proposals'},
 {name:'structured',handler:structured,path:'/v1/structured-product-proposals'},
 {name:'work queue',handler:queue,path:'/v1/work-queue',read:true},
];
function invoke(test:typeof cases[number]){
 const request=new NextRequest('http://test/api/instruments/probe',{method:test.read?'GET':'POST',headers:{'X-Tenant-Id':'forged-tenant','X-User-Account-Id':'forged-actor'},...(!test.read?{body:JSON.stringify({canonicalName:'Synthetic',decision:'APPROVED',reason:'Synthetic'})}:{})});
 return test.handler(request,{params:Promise.resolve({proposalId:'proposal'})});
}
beforeEach(()=>session.get.mockResolvedValue({tenantId:'selected-tenant',userAccountId:'session-actor',source:'local-session'}));
afterEach(()=>{session.get.mockReset();vi.unstubAllGlobals();});
describe.each(cases)('$name adapter',test=>{
 it('forwards selected session identity, never forged or environment identity',async()=>{
  let observedPath='',observedHeaders=new Headers();
  vi.stubGlobal('fetch',async(url:URL,init:RequestInit)=>{observedPath=url.pathname;observedHeaders=new Headers(init.headers);return Response.json({data:{proposalId:'proposal',status:'PENDING'}});});
  expect((await invoke(test)).ok).toBe(true);
  expect(observedPath).toBe(test.path);
  expect(observedHeaders.get('X-Tenant-Id')).toBe('selected-tenant');
  expect(observedHeaders.get('X-User-Account-Id')).toBe('session-actor');
 });
 it('rejects a missing selected session without contacting the API',async()=>{
  session.get.mockRejectedValue(new Error('No active tenant'));
  const fetchSpy=vi.fn();vi.stubGlobal('fetch',fetchSpy);
  const response=await invoke(test);
  expect(response.status).toBe(401);expect(fetchSpy).not.toHaveBeenCalled();
 });
 it('preserves upstream authority denial rather than returning success',async()=>{
  vi.stubGlobal('fetch',async()=>Response.json({type:'about:blank',title:'Forbidden',status:403,detail:'Tenant membership is not permitted to perform this action',code:'TENANT_ACTION_FORBIDDEN',requestId:'authority-probe'},{status:403}));
  const response=await invoke(test);
  expect(response.status).toBe(403);expect((await response.json()).error.retryable).toBe(false);
 });
});
