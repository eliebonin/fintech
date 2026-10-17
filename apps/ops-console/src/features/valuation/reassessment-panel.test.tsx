import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {ReassessmentPanel} from './reassessment-panel';

it('retains published evidence with a visible correction warning and explicit reason',()=>{
 const html=renderToStaticMarkup(<ReassessmentPanel batch={{batch_id:'mock',sourceHealth:{status:'REASSESSMENT_REQUIRED',changes:[{tradeId:'trade',economicFrom:'2026-10-01',recordedAt:'2026-10-14',reason:'CANCELLED'}]}}} canCalculate onOpen={()=>{}}/>);
 expect(html).toContain('Reassessment required');expect(html).toContain('2026-10-01');expect(html).toContain('Recalculate');expect(html).toContain('required');
});
it('does not offer recalculation without calculation rights',()=>{
 const html=renderToStaticMarkup(<ReassessmentPanel batch={{batch_id:'mock',sourceHealth:{status:'REASSESSMENT_REQUIRED',changes:[]}}} canCalculate={false} onOpen={()=>{}}/>);
 expect(html).not.toContain('<form');expect(html).toContain('Calculation permission');
});
it('distinguishes unknown legacy source proof from a confirmed financial error',()=>{
 const html=renderToStaticMarkup(<ReassessmentPanel batch={{batch_id:'mock',sourceHealth:{status:'UNKNOWN_LEGACY',changes:[]}}} canCalculate onOpen={()=>{}}/>);
 expect(html).toContain('Legacy source proof unavailable');expect(html).toContain('does not by itself establish a financial error');
});
