import {expect,it,vi} from 'vitest';
import {searchOptionBookingListingsFromBff,getOptionBookingListingFromBff,searchFxForwardBookingInstrumentsFromBff,getFxForwardBookingInstrumentFromBff} from './browser-api-client';
it('carries explicit historical search and selection dates for options and FX',async()=>{
 const paths:string[]=[];const fetch=vi.fn(async(url:RequestInfo|URL)=>{paths.push(String(url));return Response.json({data:[],meta:{}});});
 await searchOptionBookingListingsFromBff('Call',fetch,25,'2026-09-30');
 await getOptionBookingListingFromBff('listing',fetch,'2026-09-30');
 await searchFxForwardBookingInstrumentsFromBff('EUR',fetch,25,'2026-09-30');
 await getFxForwardBookingInstrumentFromBff('instrument',fetch,'2026-09-30');
 expect(paths.map(path=>new URL(path,'http://test').searchParams.get('asOfDate'))).toEqual(['2026-09-30','2026-09-30','2026-09-30','2026-09-30']);
 expect(new URL(paths[0],'http://test').searchParams.get('offset')).toBe('25');
});
