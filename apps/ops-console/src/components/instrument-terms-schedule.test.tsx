import {expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {InstrumentTermsSchedule} from './instrument-terms-schedule';
import type {TermsSchedule} from '@/lib/instrument-terms-schedule';

it('renders separate swap and reference schedules without editable fields or fabricated reset dates',()=>{
  const data:TermsSchedule={instrumentId:'swap',basis:'CURRENT_APPROVED_TERMS',referenceLabels:{index:'S&P 500'},layers:[
    {instrumentId:'swap',canonicalName:'Autocall swap',instrumentType:'SWAP',relation:'Selected instrument',version:1,issuer:null,currency:'GBP',dates:{maturity_date:'2032-09-16'},economics:{performanceResetFrequency:'QUARTERLY'},facts:{scheduleEvents:[]}},
    {instrumentId:'note',canonicalName:'Reference autocall',instrumentType:'STRUCTURED_PRODUCT',relation:'Swap performance reference',version:1,issuer:'Issuer',currency:'GBP',dates:{maturity_date:'2032-09-20'},economics:{notional_amount:'1'},facts:{shareCalls:[{observation_date:'2027-09-09',payment_date:'2027-09-16',trigger_level:'105',redemption_rate:'110.450000000000'}],initialFixings:[{underlying_reference_node_id:'index',fixing_value:'7636.360000000000'}]}},
  ]};
  const html=renderToStaticMarkup(<InstrumentTermsSchedule data={data}/>);
  for(const value of ['Terms &amp; Schedule','Swap performance reference','2032-09-16','2032-09-20','2027-09-09','2027-09-16','110.450000000000','S&amp;P 500','No explicit reset or payment dates recorded'])expect(html).toContain(value);
  expect(html).not.toMatch(/<input|<select|<textarea/);
});

it('preserves unbounded terminal ranges instead of labelling them missing',()=>{
  const data:TermsSchedule={instrumentId:'share',basis:'CURRENT_APPROVED_TERMS',referenceLabels:{},layers:[{instrumentId:'share',canonicalName:'Share',instrumentType:'STRUCTURED_PRODUCT',relation:'Selected instrument',version:1,issuer:null,currency:'GBP',dates:{},economics:{},facts:{terminalBranches:[{lower_bound:null,upper_bound:'65',formula:'PERFORMANCE'},{lower_bound:'65',upper_bound:null,formula:'FIXED'}]}}]};
  const html=renderToStaticMarkup(<InstrumentTermsSchedule data={data}/>);
  expect(html).toContain('No lower bound');expect(html).toContain('No upper bound');
});
