import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
vi.mock('@/app/trades/new/product-ticket',()=>({ProductFacts:()=>null}));
vi.mock('./swap-terms-facts',()=>({SwapTermsFacts:()=>null}));
import {InstrumentDetail} from './instrument-detail';
import {searchInstruments} from '@/lib/instrument-data';
it('renders identifier scope badges without block elements inside paragraphs',()=>{
 const instrument=searchInstruments('HSBC')[0];
 const html=renderToStaticMarkup(<InstrumentDetail instrument={instrument}/>);
 expect(html).toContain('GB0005405286');expect(html).toContain('INSTRUMENT');
 const paragraphs=html.match(/<p\b[^>]*>[\s\S]*?<\/p>/g)??[];
 expect(paragraphs.length).toBeGreaterThan(0);
 for(const paragraph of paragraphs)expect(paragraph).not.toMatch(/<(?:div|table|section|ul|ol)\b/);
});
