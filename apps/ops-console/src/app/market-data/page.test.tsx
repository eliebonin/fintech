import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';

vi.mock('server-only',()=>({}));
vi.mock('next/navigation',()=>({redirect:(url:string)=>{throw new Error(`redirect:${url}`);},usePathname:()=>'/market-data'}));
const mocks=vi.hoisted(()=>({context:vi.fn(),series:vi.fn(),workspace:vi.fn()}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:mocks.context,getActiveTenantWorkspace:mocks.workspace}));
vi.mock('@/lib/mvp-api-client',()=>({getMarketDataSeries:mocks.series,describeMvpError:()=> 'Market data could not be loaded'}));
vi.mock('@/components/market-data-resolution-form',()=>({MarketDataResolutionForm:()=>null}));
vi.mock('@/components/workspace-shell',()=>({WorkspaceShell:({children}:{children:React.ReactNode})=>children}));
afterEach(()=>{vi.useRealTimers();vi.clearAllMocks();});
beforeEach(()=>mocks.workspace.mockResolvedValue({tenantName:'Personal workspace',membershipRole:'TENANT_ADMIN',moduleCodes:['MARKET_DATA']}));

it('uses selected tenant, rolling dates and source-specific personal labels',async()=>{
 vi.setSystemTime(new Date('2026-10-06T12:00:00Z'));
 mocks.context.mockResolvedValue({tenantId:'chosen-personal-tenant',userAccountId:'user',source:'local-session'});
 mocks.series.mockResolvedValue({data:[{seriesId:'series',referenceNodeId:'listing',referenceNodeName:'Apple',seriesType:'CLOSE',valueType:'PRICE',currency:'USD',datasetCode:'YAHOO_PERSONAL_EQUITY_DAILY',providerCode:'YAHOO_FINANCE_PERSONAL',expectedFrequency:'BUSINESS_DAILY',observations:[],observationTotal:0}],meta:{total:1}});
 const {default:Page}=await import('./page');
 const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({})}));
 expect(mocks.series.mock.calls[0][0].tenantId).toBe('chosen-personal-tenant');
 expect(mocks.series.mock.calls[0][1].fromDate).toBe('2026-09-22');
 expect(mocks.series.mock.calls[0][1].toDate).toBe('2026-10-05');
 expect(html).toContain('PERSONAL PROJECT');expect(html).not.toContain('LIVE API · DEMO DATA');
 expect(html).toContain('split adjusted');
 expect(html).not.toContain('Series &amp;amp; provenance');
});

it('requires explicit tenant selection without falling back to a demo tenant',async()=>{
 mocks.context.mockRejectedValue(new Error('No selected tenant'));
 const {default:Page}=await import('./page');
 await expect(Page({searchParams:Promise.resolve({})})).rejects.toThrow('redirect:/select-tenant');
 expect(mocks.series).not.toHaveBeenCalled();
});

it('explains a missing module without querying prices or claiming an outage',async()=>{
 mocks.context.mockResolvedValue({tenantId:'restricted-tenant',userAccountId:'user',source:'local-session'});
 mocks.workspace.mockResolvedValue({tenantName:'Restricted workspace',membershipRole:'READ_ONLY',moduleCodes:['SECURITY_MASTER']});
 const {default:Page}=await import('./page');
 const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({})}));
 expect(html).toContain('ACCESS RESTRICTED');expect(html).toContain('tenant administrator');
 expect(html).not.toContain('API UNAVAILABLE');expect(mocks.series).not.toHaveBeenCalled();
});
