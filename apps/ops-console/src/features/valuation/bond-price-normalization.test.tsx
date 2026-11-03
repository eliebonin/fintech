import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {BondPriceNormalization} from './bond-price-normalization';

it('shows raw DIRTY, quoted accrued and derived CLEAN with their distinct dates',()=>{
 const selections=[{valuation_date:'2026-10-01',pricing_date_used:'2026-09-30',pricing_evidence:{bondPriceNormalization:{
  method:'DIRTY_MINUS_QUOTED_ACCRUAL_PER_100',marketDate:'2026-09-30',quoteSettlementDate:'2026-10-02',dirtyPrice:'101.02',accruedPer100:'1.02',cleanPrice:'100'}}}];
 const before=JSON.stringify(selections),html=renderToStaticMarkup(<BondPriceNormalization selections={selections}/>);
 for(const value of ['101.02','1.02','100','2026-09-30','2026-10-02'])expect(html).toContain(`>${value}<`);
 expect(html).toContain('DIRTY to CLEAN');expect(html).toContain('Daily interest');expect(JSON.stringify(selections)).toBe(before);
});
it('keeps explicit zero and negative source accrual visible without inferring missing values',()=>{
 const selections=['0','-0.2'].map(amount=>({pricing_evidence:{bondPriceNormalization:{method:'DIRTY_MINUS_QUOTED_ACCRUAL_PER_100',dirtyPrice:'100',accruedPer100:amount,cleanPrice:'100'}}}));
 const html=renderToStaticMarkup(<BondPriceNormalization selections={selections}/>);
 expect(html).toContain('>0<');expect(html).toContain('>-0.2<');expect(html).toContain('Not recorded');
});
it('adds no normalization section to a native CLEAN or non-bond quote',()=>{
 expect(renderToStaticMarkup(<BondPriceNormalization selections={[{selected_value:'100'}]}/>)).toBe('');
});
