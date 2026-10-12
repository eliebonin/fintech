import {afterEach,expect,it,vi} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
const h=vi.hoisted(()=>({role:'OPERATIONS',modules:['SECURITY_MASTER','TRADING'],path:'/trades',booking:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('next/navigation',()=>({usePathname:()=>h.path,redirect:(path:string)=>{throw new Error('redirect:'+path);},useRouter:()=>({})}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor',source:'local-session'}),getActiveTenantWorkspace:async()=>({tenantName:'Test tenant',membershipRole:h.role,moduleCodes:h.modules})}));
vi.mock('@/lib/reference-api-client',async original=>({...await original<typeof import('@/lib/reference-api-client')>(),getTradeBookingContext:h.booking}));
import TradesPage from './trades/page';
import NewTradePage from './trades/new/page';
import RequestsPage from './instruments/requests/page';
import SwapPage from './instruments/swaps/new/page';
import FuturePage from './instruments/futures/new/page';
import FamilyPage from './instruments/future-families/page';
import OptionPage from './instruments/options/new/page';
import ConventionPage from './instruments/[instrumentId]/booking-conventions/page';
afterEach(()=>{h.role='OPERATIONS';h.modules=['SECURITY_MASTER','TRADING'];h.path='/trades';h.booking.mockReset();vi.unstubAllGlobals();});
function fakeReads(){vi.stubGlobal('fetch',async()=>Response.json({data:[],counts:{},items:[],meta:{total:0,source:'live-reference-api'}}));}
it('keeps read-only empty history without offering a first-booking link',async()=>{
 fakeReads();const html=renderToStaticMarkup(await TradesPage({searchParams:Promise.resolve({range:'all'})}));
 expect(html).toContain('No trades have been recorded');expect(html.includes('href="/trades/new"')).toBe(false);
});
it('hides request-page creation from an unqualified member',async()=>{
 h.path='/instruments/requests';fakeReads();const html=renderToStaticMarkup(await RequestsPage());
 expect(html).toContain('Pending instrument requests');expect(html.includes('href="/instruments/create"')).toBe(false);
});
it('explains a directly opened booking page instead of silently redirecting',async()=>{
 h.path='/trades/new';const html=renderToStaticMarkup(await NewTradePage({searchParams:Promise.resolve({})}));
 expect(html).toContain('permission');expect(html).toContain('TRADING');expect(html).toContain('administrator');
 expect(html.includes('Review booking')).toBe(false);expect(h.booking).not.toHaveBeenCalled();
});
it.each([
 ['/instruments/swaps/new',()=>SwapPage()],
 ['/instruments/futures/new',()=>FuturePage({searchParams:Promise.resolve({})})],
 ['/instruments/future-families',()=>FamilyPage({searchParams:Promise.resolve({})})],
 ['/instruments/options/new',()=>OptionPage()],
 ['/instruments/id/booking-conventions',()=>ConventionPage({params:Promise.resolve({instrumentId:'id'})})],
] as const)('explains instrument stewardship denial before opening any write form: %s',async(path,page)=>{
 h.path=path;const html=renderToStaticMarkup(await page());
 expect(html).toContain('permission');expect(html).toContain('SECURITY_MASTER');expect(html).toContain('administrator');
 expect(html.includes('<form')).toBe(false);
});
