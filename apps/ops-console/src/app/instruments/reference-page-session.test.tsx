import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
const session=vi.hoisted(()=>({get:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:session.get}));
import FxPage from './fx-forwards/new/page';
import CryptoPage from './crypto/new/page';
import CryptoReview from './crypto/review/[proposalId]/page';
import FamilyPage from './index-families/new/page';
import IndexPage from './indices/new/page';
const cases=[
 {name:'FX catalogue',run:()=>FxPage()},
 {name:'crypto catalogue',run:()=>CryptoPage()},
 {name:'crypto proposal detail',run:()=>CryptoReview({params:Promise.resolve({proposalId:'proposal'})})},
 {name:'index family catalogue',run:()=>FamilyPage()},
 {name:'index catalogues',run:()=>IndexPage()},
];
beforeEach(()=>session.get.mockResolvedValue({tenantId:'selected-tenant',userAccountId:'session-actor',source:'local-session'}));
afterEach(()=>{session.get.mockReset();vi.unstubAllGlobals();});
describe.each(cases)('$name',test=>{
 it('loads reference facts only under the selected session identity',async()=>{
  const identities:string[][]=[];
  vi.stubGlobal('fetch',async(_url:URL,init:RequestInit)=>{const headers=new Headers(init.headers);identities.push([headers.get('X-Tenant-Id')!,headers.get('X-User-Account-Id')!]);return Response.json({data:[],meta:{}});});
  await test.run();expect(identities.length).toBeGreaterThan(0);
  for(const identity of identities)expect(identity).toEqual(['selected-tenant','session-actor']);
 });
 it('does not load default-tenant facts without a selected session',async()=>{
  session.get.mockRejectedValue(new Error('No active tenant'));
  const send=vi.fn();vi.stubGlobal('fetch',send);
  await test.run();expect(send).not.toHaveBeenCalled();
 });
});
