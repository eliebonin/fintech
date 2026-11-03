import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,refs:[] as any[],refCursor:0}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),
 useState:(initial:unknown)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=initial;return[h.slots[i],(value:any)=>h.slots[i]=typeof value==='function'?value(h.slots[i]):value];},
 useRef:(initial:unknown)=>{const i=h.refCursor++;if(!(i in h.refs))h.refs[i]={current:initial};return h.refs[i];},useEffect:()=>{}}));
import {RunReport,runStatus} from './run-report';
it('distinguishes an incomplete candidate from a publishable staged result',()=>{
 expect(runStatus({status:'COMPLETED',batch_status:'STAGED',required_inputs_complete:false} as any)).toBe('Completed · Staged — not published · Incomplete');
});
const strategies=[{id:'read-only',label:'Read-permitted strategy',canCalculate:false}],policies=[{id:'p',label:'EOD · v3'}];
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;for(const child of[node.props?.children].flat(Infinity)){const result=find(child,predicate);if(result)return result;}}
const open=vi.fn();
function render(mode:'results'|'history'='results'){h.cursor=0;h.refCursor=0;return RunReport({mode,strategies,policies,currencies:[],busy:false,revision:0,onOpen:open});}
function change(name:string,value:string,mode:'results'|'history'='results'){find(render(mode),n=>n.props?.name===name).props.onChange({target:{value}});}
async function search(mode:'results'|'history'='results'){await find(render(mode),n=>n.type==='form').props.onSubmit({preventDefault(){}});}
afterEach(()=>{h.slots=[];h.cursor=0;h.refs=[];h.refCursor=0;open.mockReset();vi.unstubAllGlobals();});
it('requires a read-permitted strategy before requesting financial results',async()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);await search();expect(fetch).not.toHaveBeenCalled();
 const selector=find(render(),n=>n.props?.name==='strategy_id');
 expect(selector.props.initialChoices.some((choice:any)=>choice.id==='read-only'&&choice.canCalculate===false)).toBe(true);
 expect(selector.props.forCalculation).not.toBe(true);
 expect(find(render(),n=>n.props?.role==='alert')).toBeDefined();
});
it('uses the selected end date for both boundaries of the single-day shortcut',()=>{
 change('to_date','2026-10-07');find(render(),n=>n.type==='button'&&n.props.children==='Single day').props.onClick();
 expect(find(render(),n=>n.props?.name==='from_date').props.value).toBe('2026-10-07');
 expect(find(render(),n=>n.props?.name==='to_date').props.value).toBe('2026-10-07');
});
it('identifies a self-reviewed publication without implying an independent review',()=>{
 expect(runStatus({status:'COMPLETED',batch_status:'PUBLISHED',publication_review_mode:'SELF_REVIEWED'})).toBe('Completed · Published · Self-reviewed');
});
it('sends filters to the server and retains them on the next page',async()=>{
 const fetch=vi.fn(async(_path:string)=>Response.json({items:[],total:30}));vi.stubGlobal('fetch',fetch);
 change('strategy_id','read-only');change('from_date','2026-10-01');change('to_date','2026-10-07');change('publication_status','STAGED');await search();
 await find(render(),n=>n.type==='button'&&n.props.children==='Next').props.onClick();
 const query=new URL(String(fetch.mock.calls[1][0]),'http://local').searchParams;
 expect(query.get('strategy_id')).toBe('read-only');expect(query.get('from_date')).toBe('2026-10-01');expect(query.get('to_date')).toBe('2026-10-07');expect(query.get('publication_status')).toBe('STAGED');expect(query.get('offset')).toBe('25');expect(query.get('results_only')).toBe('true');
});
it('keeps failed attempts in the operational report and opens their logs',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({items:[{attempt_id:'failed',status:'FAILED',started_at:'2026-10-13T09:00:00Z',failure_reason:'Missing eligible EUR/GBP observation'}],total:1})));
 await search('history');expect(find(render('history'),n=>n.type==='td'&&n.props.children==='Missing eligible EUR/GBP observation')).toBeDefined();
 await find(render('history'),n=>n.type==='button'&&n.props.children==='View logs').props.onClick();expect(open).toHaveBeenCalledWith('failed');
});
it('discards an old report when its selection changes, without fetching a new result implicitly',async()=>{
 const fetch=vi.fn(async()=>Response.json({items:[{attempt_id:'recorded',status:'COMPLETED',batch_status:'STAGED',started_at:'2026-10-13T09:00:00Z',financial_summary:{netPnl:'99',reportingCurrencyId:'gbp'}}],total:1}));vi.stubGlobal('fetch',fetch);
 change('strategy_id','read-only');await search();expect(find(render(),n=>n.type==='button'&&n.props.children==='Open result')).toBeDefined();
 change('strategy_id','other');expect(find(render(),n=>n.type==='button'&&n.props.children==='Open result')).toBeUndefined();expect(fetch).toHaveBeenCalledOnce();
});
it('ignores a stale response after the selected strategy changes',async()=>{
 let resolve!:(response:Response)=>void;vi.stubGlobal('fetch',vi.fn(()=>new Promise<Response>(done=>{resolve=done;})));
 change('strategy_id','read-only');const pending=search();change('strategy_id','other');
 resolve(Response.json({items:[{attempt_id:'old',status:'COMPLETED',batch_status:'STAGED',started_at:'2026-10-13T09:00:00Z'}],total:1}));await pending;
 expect(find(render(),n=>n.type==='button'&&n.props.children==='Open result')).toBeUndefined();
});
it('does not render financial amounts when source display rights are denied',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({items:[{attempt_id:'restricted',status:'COMPLETED',batch_status:'STAGED',started_at:'2026-10-13T09:00:00Z',evidence_access:'DENIED',financial_summary:{netPnl:'999999'}}],total:1})));
 change('strategy_id','read-only');await search();
 expect(find(render(),n=>n.type==='td'&&n.props.children==='Restricted — display rights required')).toBeDefined();
 expect(find(render(),n=>n.props?.children==='999999')).toBeUndefined();
});
it.each([['COMPLETED','STAGED','Completed · Staged — not published'],['COMPLETED','PUBLISHED','Completed · Published'],['COMPLETED','SUPERSEDED','Completed · Superseded'],['FAILED',null,'Failed · No result'],['RUNNING',null,'Running · Calculation in progress'],['COMPLETED',null,'Completed · No result recorded']])('does not confuse calculation=%s and batch=%s with a final publication',(status,batch,want)=>expect(runStatus({status,batch_status:batch} as any)).toBe(want));
it('does not ask for reassessment again when a historical result was superseded',()=>{
 expect(runStatus({status:'COMPLETED',batch_status:'SUPERSEDED',source_health_status:'REASSESSMENT_REQUIRED'})).toBe('Completed · Superseded');
});
