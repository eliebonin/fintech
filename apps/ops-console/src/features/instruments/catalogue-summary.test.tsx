import {expect,it,vi} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
vi.mock('server-only',()=>({}));
import {loadCatalogue} from './catalogue-data';
import {InstrumentCatalogue} from '@/components/instrument-catalogue';

it('requests the compact catalogue endpoint rather than full search details',async()=>{
  const fetchImpl=vi.fn(async()=>Response.json({data:[],meta:{source:'live-reference-api',total:0}}));
  await loadCatalogue('HSBC',{tenantId:'tenant',userAccountId:'actor',limit:25,fetchImpl});
  const [url,init]=fetchImpl.mock.calls[0] as unknown as [URL,RequestInit];
  expect(url.pathname).toBe('/v1/instruments/catalogue');
  expect(url.searchParams.get('limit')).toBe('25');
  expect(init.headers).toMatchObject({'X-Tenant-Id':'tenant','X-User-Account-Id':'actor'});
});

it('renders listing counts and detail links from compact rows without detail arrays',()=>{
  const row={instrumentId:'instrument',canonicalName:'Compact instrument',instrumentType:'EQUITY',assetClass:'EQUITY',status:'ACTIVE',baseCurrency:'GBP',listingCount:2};
  const html=renderToStaticMarkup(<InstrumentCatalogue initialResults={[row] as any}/>);
  expect(html).toContain('Compact instrument');
  expect(html).toContain('href="/instruments/instrument"');
  expect(html).toContain('>2</td>');
});
