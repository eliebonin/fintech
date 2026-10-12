import { SessionRequiredError } from '@/lib/server/workspace-errors';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';

vi.mock('server-only',()=>({}));
vi.mock('next/navigation',()=>({redirect:(url:string)=>{throw new Error(`redirect:${url}`);},usePathname:()=>'/market-data'}));
const mocks=vi.hoisted(()=>({context:vi.fn(),series:vi.fn(),workspace:vi.fn(),sources:vi.fn(),catalogue:vi.fn()}));
vi.mock('@/lib/pricing-policy-api',()=>({pricingPolicyClient:async()=>({GET:mocks.sources})}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:mocks.context,getActiveTenantWorkspace:mocks.workspace}));
vi.mock('@/lib/mvp-api-client',()=>({getMarketDataSeries:mocks.series,getMarketDataCatalogue:mocks.catalogue,describeMvpError:()=> 'Market data could not be loaded'}));
vi.mock('@/components/market-data-resolution-form',()=>({MarketDataResolutionForm:()=>null}));
vi.mock('@/components/workspace-shell',()=>({WorkspaceShell:({children}:{children:React.ReactNode})=>children}));
afterEach(()=>{vi.useRealTimers();vi.clearAllMocks();});
beforeEach(()=>mocks.workspace.mockResolvedValue({tenantName:'Personal workspace',membershipRole:'TENANT_ADMIN',moduleCodes:['MARKET_DATA']}));

it('opens an operational overview without loading observation history',async()=>{
 mocks.context.mockResolvedValue({tenantId:'chosen-tenant',userAccountId:'user',source:'local-session'});
 mocks.sources.mockResolvedValue({data:{sources:[],priorities:[],instrumentTypes:[]}});
 const {default:Page}=await import('./page');
 const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({})}));
 expect(mocks.series).not.toHaveBeenCalled();
 expect(html).toContain('Market data overview');expect(html).toContain('Check coverage');
 expect(html).toContain('Not checked');expect(html).not.toContain('<svg');
});
it('preserves instrument-history bookmarks through the explorer',async()=>{
 const {default:Page}=await import('./page');
 await expect(Page({searchParams:Promise.resolve({referenceNodeId:'listing',fromDate:'2026-09-01',toDate:'2026-09-30'})})).rejects.toThrow('redirect:/market-data/explorer?');
 expect(mocks.series).not.toHaveBeenCalled();
});

it('requires explicit tenant selection without falling back to a demo tenant',async()=>{
 mocks.context.mockRejectedValue(new SessionRequiredError());
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

it('searches compact series metadata without loading history for the explorer',async()=>{
 mocks.context.mockResolvedValue({tenantId:'chosen-tenant',userAccountId:'user',source:'local-session'});
 mocks.catalogue.mockResolvedValue({data:[{seriesId:'series',referenceNodeId:'listing',referenceNodeName:'HSBC XLON',seriesType:'CLOSE',closingMethod:'UNKNOWN',valueType:'PRICE',currency:'GBP',datasetName:'Recorded feed',expectedFrequency:'BUSINESS_DAILY',latestMarketDate:null,latestValue:null,latestReceivedAt:null,latestDatasetName:null,latestValueBasis:null}],meta:{total:1}});
 const {default:Page}=await import('./explorer/page');
 const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({q:'HSBC',asOf:'2026-08-28'})}));
 expect(mocks.catalogue).toHaveBeenCalledWith(expect.objectContaining({tenantId:'chosen-tenant'}),{q:'HSBC',asOf:'2026-08-28',limit:25,offset:0});
 expect(mocks.series).not.toHaveBeenCalled();expect(html).toContain('No permitted dated observation');expect(html).toContain('Check this input');expect(html).toContain('seriesId=series');
});
it('anchors the historical window to the chosen end date rather than today',async()=>{
 vi.setSystemTime(new Date('2026-10-09T12:00:00Z'));
 mocks.context.mockResolvedValue({tenantId:'chosen-tenant',userAccountId:'user',source:'local-session'});
 mocks.series.mockResolvedValue({data:[{seriesId:'series',referenceNodeId:'listing',referenceNodeName:'Apple',seriesType:'CLOSE',valueType:'PRICE',currency:'USD',datasetCode:'YAHOO_PERSONAL_EQUITY_DAILY',providerCode:'YAHOO_FINANCE_PERSONAL',expectedFrequency:'BUSINESS_DAILY',observations:[],observationTotal:0}],meta:{total:1}});
 const {default:Page}=await import('./explorer/page');
 const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({referenceNodeId:'listing',toDate:'2026-08-28'})}));
 expect(mocks.series.mock.calls[0][1].fromDate).toBe('2026-08-15');expect(mocks.series.mock.calls[0][1].toDate).toBe('2026-08-28');
 expect(html).toContain('PERSONAL PROJECT');expect(html).toContain('split adjusted');
});

it('preserves the exact series selection in history requests, refresh and pagination',async()=>{
 mocks.context.mockResolvedValue({tenantId:'chosen-tenant',userAccountId:'user',source:'local-session'});
 mocks.series.mockResolvedValue({data:[{seriesId:'raw-series',referenceNodeId:'listing',referenceNodeName:'AMZN',seriesType:'CLOSE',valueType:'PRICE',currency:'USD',expectedFrequency:'BUSINESS_DAILY',observations:[],observationTotal:250}],meta:{total:1}});
 const {default:Page}=await import('./explorer/page');
 const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({referenceNodeId:'listing',seriesId:'raw-series',toDate:'2026-10-09',observationOffset:'100'})}));
 expect(mocks.series.mock.calls[0][1]).toMatchObject({referenceNodeId:'listing',seriesId:'raw-series',observationOffset:100,observationLimit:25});
 expect(html).toContain('name="seriesId" value="raw-series"');
 expect(html.match(/seriesId=raw-series/g)).toHaveLength(2);
});

it('charts the complete period independently of the 25/50/100 price pages',async()=>{
 mocks.context.mockResolvedValue({tenantId:'chosen-tenant',userAccountId:'user',source:'local-session'});
 const chartPoints=Array.from({length:120},(_,i)=>({marketDate:'2026-10-01',value:String(i+1)}));
 const observations=Array.from({length:50},(_,i)=>({observationId:String(i),marketDate:'2026-10-01',observedAt:'2026-10-01T00:00:00Z',receivedAt:'2026-10-02T00:00:00Z',value:String(i+51),valueBasis:'RAW',qualityStatus:'ACCEPTED'}));
 mocks.series.mockResolvedValue({data:[{seriesId:'raw-series',referenceNodeId:'listing',referenceNodeName:'AMZN',seriesType:'CLOSE',valueType:'PRICE',currency:'USD',expectedFrequency:'BUSINESS_DAILY',observations,chartPoints,observationTotal:120}],meta:{total:1}});
 const {default:Page}=await import('./explorer/page');
 const html=renderToStaticMarkup(await Page({searchParams:Promise.resolve({referenceNodeId:'listing',seriesId:'raw-series',toDate:'2026-10-09',observationOffset:'50',observationLimit:'50'})}));
 expect(mocks.series.mock.calls[0][1]).toMatchObject({includeChart:true,observationLimit:50,observationOffset:50});
 expect(html).toContain('120 observations');
 expect(html).toContain('51-100 of 120');
 expect(html).toContain('name="observationLimit"');
 for(const size of [25,50,100])expect(html).toContain(`value="${size}"`);
 expect(html).toContain('observationLimit=50');
 expect(html).not.toContain('Charts show this page only');
 expect(html.match(/quality-accepted/g)).toHaveLength(50);
 expect(html.indexOf('Price table pages')).toBeGreaterThan(html.indexOf('history chart'));
 const chart=html.match(/<polyline[^>]*points="([^"]*)"/);
 expect(chart?.[1].split(' ')).toHaveLength(120);
});
