import {expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {InstrumentLabel} from './instrument-label';
import {instrumentDisplayText,instrumentDisplayHref,type InstrumentDisplay} from '@/lib/instrument-display';

const bond:InstrumentDisplay={primaryName:'UK Treasury Bill',identifier:{scheme:'ISIN',value:'GB00BSGRV302'},context:['GBP denomination'],searchText:'UK Treasury Bill GB00BSGRV302 RECON_BOND_20828',basis:'CURRENT_ACCESSIBLE_METADATA'};
it('renders a readable business name, identifier and currency with an exact link',()=>{
 const html=renderToStaticMarkup(<InstrumentLabel display={bond} href="/instruments/exact-listing"/>);
 expect(html).toContain('UK Treasury Bill');expect(html).toContain('ISIN GB00BSGRV302');
 expect(html).toContain('GBP denomination');expect(html).toContain('href="/instruments/exact-listing"');
 expect(html).not.toContain('RECON_BOND_20828');
 expect(html.indexOf('UK Treasury Bill')).toBeLessThan(html.indexOf('GB00BSGRV302'));
});
it('makes missing identifiers explicit, without promoting an internal alias',()=>{
 const html=renderToStaticMarkup(<InstrumentLabel display={{...bond,identifier:null}} fallbackName="RECON_BOND_20828"/>);
 expect(html).toContain('Identifier not supplied');expect(html).not.toContain('RECON_BOND_20828');
});
it('keeps a native ticker and venue distinct without inventing a contract description',()=>{
 const display={...bond,primaryName:'S&P 500 future',identifier:{scheme:'CONTRACT_SYMBOL',value:'ESZ6'},context:['CME','USD quote']};
 expect(instrumentDisplayText(display)).toBe('S&P 500 future · ESZ6 · CME · USD quote');
 expect(renderToStaticMarkup(<InstrumentLabel display={display}/>)).not.toContain('2026');
});
it('uses flow content inside headings and preserves names containing punctuation',()=>{
 const html=renderToStaticMarkup(<h3><InstrumentLabel display={{...bond,primaryName:'AT&T <Class A>'}}/></h3>);
 expect(html).not.toMatch(/<(div|p|h[1-6])[^>]*>.*<h3/);
 expect(html).not.toContain('<p');expect(html).not.toContain('<div');expect(html).toContain('AT&amp;T &lt;Class A&gt;');
});
it('uses an explicit fallback only when structured metadata is absent',()=>{
 expect(instrumentDisplayText(undefined,'Stored name')).toBe('Stored name');
 expect(instrumentDisplayText(undefined)).toBe('Instrument name unavailable');
 expect(instrumentDisplayText({...bond,primaryName:'Instrument name unavailable'})).not.toContain('RECON');
});
it('does not repeat a native contract symbol when that is also its existing name',()=>{
 const display={...bond,primaryName:'ESZ6',identifier:{scheme:'CONTRACT_SYMBOL',value:'ESZ6'},context:['CME','USD quote']};
 expect(instrumentDisplayText(display)).toBe('ESZ6 · CME · USD quote');
 expect(renderToStaticMarkup(<InstrumentLabel display={display}/>).match(/ESZ6/g)).toHaveLength(1);
});
it('links two listings to distinct anchors on their canonical instrument, never conflating them',()=>{
 const display={...bond,instrumentId:'parent'};
 expect(instrumentDisplayHref(display,'listing-a')).toBe('/instruments/parent#listing-listing-a');
 expect(instrumentDisplayHref(display,'listing-b')).toBe('/instruments/parent#listing-listing-b');
 expect(instrumentDisplayHref(display,'parent')).toBe('/instruments/parent');
});
