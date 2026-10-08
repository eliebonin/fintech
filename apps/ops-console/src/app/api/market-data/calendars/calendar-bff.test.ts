import {NextRequest} from 'next/server';
import {it,expect,vi,beforeEach} from 'vitest';
const {get,post}=vi.hoisted(()=>({get:vi.fn(),post:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('@/lib/pricing-policy-api',()=>({pricingPolicyClient:async()=>({GET:get,POST:post})}));
import {GET,POST} from './[[...path]]/route';
beforeEach(()=>{get.mockReset();post.mockReset();});
it('requires bounded preview dates before querying a saved version',async()=>{
 const result=await GET(new NextRequest('http://ops.test/api/market-data/calendars/calendar/days'),{params:Promise.resolve({path:['calendar','days']})});
 expect(result.status).toBe(400);expect(get).not.toHaveBeenCalled();
});
it('forwards explicit dates to the selected-tenant typed calendar API',async()=>{
 get.mockResolvedValue({data:{calendarId:'calendar',days:[]},response:new Response(null,{status:200})});
 const result=await GET(new NextRequest('http://ops.test/api/market-data/calendars/calendar/days?fromDate=2026-08-28&toDate=2026-09-01'),{params:Promise.resolve({path:['calendar','days']})});
 expect(result.status).toBe(200);expect(get).toHaveBeenCalledWith('/v1/market-data/calendars/{calendar_id}/days',{params:{path:{calendar_id:'calendar'},query:{fromDate:'2026-08-28',toDate:'2026-09-01'}}});
});
it('preserves stable assignment submission keys and upstream rejection',async()=>{
 const context={params:Promise.resolve({path:['assignments']})};
 const missing=await POST(new NextRequest('http://ops.test/api/market-data/calendars/assignments',{method:'POST',body:'{}'}),context);
 expect(missing.status).toBe(400);expect(post).not.toHaveBeenCalled();
 post.mockResolvedValue({error:{detail:'Calendar unavailable'},response:new Response(null,{status:404})});
 const response=await POST(new NextRequest('http://ops.test/api/market-data/calendars/assignments',{method:'POST',headers:{'Idempotency-Key':'stable'},body:JSON.stringify({calendarId:'calendar'})}),context);
 expect(response.status).toBe(404);expect(post).toHaveBeenCalledWith('/v1/market-data/calendars/assignments',{body:{calendarId:'calendar'},params:{header:{'Idempotency-Key':'stable'}}});
});
