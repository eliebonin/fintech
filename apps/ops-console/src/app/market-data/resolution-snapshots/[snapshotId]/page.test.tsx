import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect,vi,afterEach} from 'vitest';
const mocks=vi.hoisted(()=>({context:vi.fn(),get:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('next/navigation',()=>({redirect:(url:string)=>{throw new Error('redirect:'+url);}}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:mocks.context,getActiveTenantWorkspace:async()=>({tenantName:'Selected tenant',membershipRole:'TENANT_ADMIN',moduleCodes:['MARKET_DATA']})}));
vi.mock('@/lib/pricing-policy-api',()=>({pricingPolicyClient:async()=>({GET:mocks.get})}));
vi.mock('@/components/workspace-shell',()=>({WorkspaceShell:({children}:{children:React.ReactNode})=>children}));
afterEach(()=>vi.resetAllMocks());
it('reads frozen evidence directly under selected tenant without an internal-cookie loopback',async()=>{
 mocks.context.mockResolvedValue({tenantId:'selected-tenant'});
 mocks.get.mockResolvedValue({data:{status:'PARTIAL',marketDataAsOfUtc:'2026-10-07T22:00:00Z',items:[]},response:new Response(null,{status:200})});
 const {default:Page}=await import('./page');
 const html=renderToStaticMarkup(await Page({params:Promise.resolve({snapshotId:'snapshot-id'})}));
 expect(mocks.get).toHaveBeenCalledWith('/v1/market-data-resolution-snapshots/{snapshot_id}',{params:{path:{snapshot_id:'snapshot-id'}}});
 expect(html).toContain('Frozen pricing targets');
});
it('requires explicit tenant selection for snapshot evidence',async()=>{
 mocks.context.mockRejectedValue(new Error('No tenant'));
 const {default:Page}=await import('./page');
 await expect(Page({params:Promise.resolve({snapshotId:'snapshot-id'})})).rejects.toThrow('redirect:/select-tenant');
 expect(mocks.get).not.toHaveBeenCalled();
});
