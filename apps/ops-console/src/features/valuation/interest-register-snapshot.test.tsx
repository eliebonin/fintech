import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {beforeEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({paths:[] as string[]}));
vi.mock('react',async importOriginal=>{
 const actual=await importOriginal<typeof import('react')>();
 return {...actual,useState:(initial:unknown)=>actual.useState(initial==='daily'?'balances':initial)};
});
vi.mock('./use-interest-data',()=>({useInterestData:(path:string|null)=>{
 if(path)h.paths.push(path);
 const data=path?.startsWith('interest-options')?{bonds:[],currencies:[],canWrite:false,strategyLabel:'Example strategy'}:
  path?.startsWith('balance-history')?{items:[],total:0,limit:25,offset:0}:{items:[]};
 return {data,loading:false,error:''};
}}));
import {InterestRegister} from './interest-register';
beforeEach(()=>{h.paths=[];});
it('requests only the To-date balance snapshot before server pagination, while source windows retain From/To',()=>{
 renderToStaticMarkup(<InterestRegister canWrite={false} initialContext={{strategyId:'strategy',strategyLabel:'Example strategy',from:'2026-09-18',to:'2026-10-20'}}/>);
 const history=new URL(h.paths.find(path=>path.startsWith('balance-history'))!,'http://local/');
 expect(history.searchParams.get('fromDate')).toBe('2026-10-20');
 expect(history.searchParams.get('toDate')).toBe('2026-10-20');
 expect(history.searchParams.get('limit')).toBe('25');
 for(const source of ['accrual-inputs','balance-inputs']){
  const query=new URL(h.paths.find(path=>path.startsWith(source))!,'http://local/');
  expect(query.searchParams.get('fromDate')).toBe('2026-09-18');expect(query.searchParams.get('toDate')).toBe('2026-10-20');
 }
});
it('explains the snapshot date and the separate chart window without implying prior values are current',()=>{
 const html=renderToStaticMarkup(<InterestRegister canWrite={false} initialContext={{strategyId:'strategy',strategyLabel:'Example strategy',from:'2026-09-18',to:'2026-10-20'}}/>);
 expect(html).toContain('Charts cover 2026-09-18 to 2026-10-20');
 expect(html).toContain('No maintained balances on 2026-10-20');expect(html).not.toContain('balance datapoints');
});
