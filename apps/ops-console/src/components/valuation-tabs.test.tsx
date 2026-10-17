import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as unknown[],cursor:0,refs:[] as unknown[],refCursor:0,effects:[] as (()=>unknown)[]}));
// This repository has no DOM test runtime. Exercise the real component handlers
// with persistent hook state; do not substitute valuation logic or child results.
vi.mock('react',async original=>({...await original<typeof import('react')>(),
 useState:(initial:unknown)=>{const index=h.cursor++;if(!(index in h.slots))h.slots[index]=initial;
  return [h.slots[index],(value:unknown)=>h.slots[index]=typeof value==='function'?value(h.slots[index]):value];},
 useRef:(initial:unknown)=>{const index=h.refCursor++;if(!(index in h.refs))h.refs[index]={current:initial};return h.refs[index];},
 useEffect:(effect:()=>unknown)=>{if(!h.effects.length)h.effects.push(effect);}
}));
import {ValuationConsole} from './valuation-console';
import {RunReport} from '@/features/valuation/run-report';
import {PagedValuationChoice} from '@/features/valuation/paged-choice';
function find(node:any,predicate:(node:any)=>boolean):any{
 if(!node||typeof node!=='object')return;if(predicate(node))return node;
 for(const child of [node.props?.children].flat(Infinity)){const result=find(child,predicate);if(result)return result;}
}
const render=()=>{h.cursor=0;h.refCursor=0;return ValuationConsole({canCalculate:true,canReview:true,actorId:'operator'});};
const tab=(tree:any,id:string)=>find(tree,node=>node.props?.id===`pnl-${id}-tab`);
const panel=(tree:any,id:string)=>find(tree,node=>node.props?.id===`pnl-${id}-panel`);
const click=(id:string)=>tab(render(),id).props.onClick();
const detail={attempt:{attempt_id:'run',status:'COMPLETED',started_at:'2026-10-13T19:38:11Z',correlation_id:'recorded'},events:[],
 batch:{batch_id:'batch',status:'STAGED',staged_by:'operator',items:[],reviews:[],summary:{reportingCurrencyId:'gbp',request:{strategy_id:'s1',policy_id:'p1',reporting_currency_id:'gbp',opening_cutoff:'2026-10-06T00:00:00Z',closing_cutoff:'2026-10-07T00:00:00Z'}}}};
async function load(){
 vi.stubGlobal('document',{getElementById:()=>({focus:vi.fn()})});
 vi.stubGlobal('fetch',vi.fn(async(path:string)=>Response.json(path.endsWith('/options')?
  {strategies:[{id:'s1',label:'Recorded strategy'},{id:'s2',label:'Draft strategy'}],policies:[{id:'p1',label:'Flexible EOD · v3',cutId:'cut'}],currencies:[{id:'gbp',label:'GBP'}]}:
  path.includes('?')?{items:[{...detail.attempt,request_payload:detail.batch.summary.request}],total:1}:detail)));
 render();h.effects[0]();await vi.waitFor(()=>expect(find(render(),n=>n.type===RunReport&&n.props.mode==='results').props.strategies).toHaveLength(2));
 await find(render(),n=>n.type===RunReport&&n.props.mode==='results').props.onOpen('run');
}
afterEach(()=>{h.slots=[];h.cursor=0;h.refs=[];h.refCursor=0;h.effects=[];vi.unstubAllGlobals();});
it('separates input, results and history into labelled, locally mounted panels',()=>{
 const tree=render();
 for(const id of ['input','results','history']){
  expect(tab(tree,id).props.role).toBe('tab');expect(tab(tree,id).props['aria-controls']).toBe(`pnl-${id}-panel`);
  expect(panel(tree,id).props.role).toBe('tabpanel');expect(panel(tree,id).props['aria-labelledby']).toBe(`pnl-${id}-tab`);
  expect(panel(tree,id).props.hidden).toBe(id!=='input');
 }
 const form=find(panel(tree,'input'),n=>n.props?.className==='pnl-calculation-form');click('history');
 expect(panel(render(),'input').props.hidden).toBe(true);
 expect(find(panel(render(),'input'),n=>n.props?.className==='pnl-calculation-form').key).toBe(form.key);
 expect(find(panel(render(),'history'),n=>n.props?.className==='pnl-calculation-form')).toBeUndefined();
});
it('supports arrows, wrapping and Home/End with roving keyboard focus',()=>{
 const focus=vi.fn();vi.stubGlobal('document',{getElementById:()=>({focus})});
 for(const [from,key,to] of [['input','ArrowRight','results'],['results','End','history'],['history','ArrowRight','input'],['input','ArrowLeft','history'],['history','Home','input']]){
  const preventDefault=vi.fn();tab(render(),from).props.onKeyDown({key,preventDefault});
  expect(tab(render(),to).props['aria-selected']).toBe(true);expect(tab(render(),to).props.tabIndex).toBe(0);expect(preventDefault).toHaveBeenCalledOnce();
 }
 expect(focus).toHaveBeenCalledTimes(5);
});
it('opens recorded runs from history in Results, with their frozen policy version',async()=>{
 await load();click('history');await find(panel(render(),'history'),n=>n.type===RunReport).props.onOpen('run');
 expect(panel(render(),'results').props.hidden).toBe(false);
 expect(find(panel(render(),'results'),n=>n.type==='dd'&&n.props.children==='Flexible EOD · v3')).toBeDefined();
});
it('opens an authoritative calculation response in Results and releases the frozen retry',async()=>{
 await load();vi.stubGlobal('FormData',class{get(name:string){return ({openingDate:'2026-10-06',closingDate:'2026-10-07'} as Record<string,string>)[name];}});
 vi.stubGlobal('fetch',vi.fn(async(path:string)=>Response.json(path.endsWith('/attempts')?detail:{items:[],total:0})));
 await find(panel(render(),'input'),n=>n.props?.className==='pnl-calculation-form').props.onSubmit({preventDefault(){},currentTarget:{}});
 expect(panel(render(),'results').props.hidden).toBe(false);
 expect(find(panel(render(),'input'),n=>n.type==='fieldset').props.disabled).toBe(false);
});
it('does not replace recorded Results with an edited input draft',async()=>{
 await load();const select=find(panel(render(),'input'),n=>n.type===PagedValuationChoice&&n.props.kind==='strategies');select.props.onChange({target:{value:'s2'}});
 click('results');expect(find(panel(render(),'results'),n=>n.type==='h2'&&n.props.children==='Recorded strategy')).toBeDefined();
 expect(find(panel(render(),'input'),n=>n.type===PagedValuationChoice&&n.props.value==='s2')).toBeDefined();
});
it('prepares a linked corrected-input request in Input form without changing the result',async()=>{
 await load();click('results');find(render(),n=>n.type==='button'&&n.props.children==='Prepare corrected-input recalculation').props.onClick();
 expect(panel(render(),'input').props.hidden).toBe(false);
 expect(find(panel(render(),'input'),n=>n.props?.name==='recalculationReason').props.required).toBe(true);
 expect(find(panel(render(),'input'),n=>n.props?.name==='openingDate').props.defaultValue).toBe('2026-10-06');
 expect(find(panel(render(),'results'),n=>n.type==='h2'&&n.props.children==='Recorded strategy')).toBeDefined();
});
it('retains the frozen retry key and payload across tab navigation after a network error',async()=>{
 await load();vi.stubGlobal('FormData',class{get(name:string){return ({openingDate:'2026-10-06',closingDate:'2026-10-07'} as Record<string,string>)[name];}});
 const send=vi.fn(async(path:string,_init?:RequestInit)=>{if(path.endsWith('/attempts'))throw new Error('Network unavailable');return Response.json({items:[],total:0});});vi.stubGlobal('fetch',send);
 const submit=()=>find(panel(render(),'input'),n=>n.props?.className==='pnl-calculation-form').props.onSubmit({preventDefault(){},currentTarget:{}});
 await submit();click('history');click('results');click('input');await submit();
 const calls=send.mock.calls.filter(call=>call[0].endsWith('/attempts')) as unknown as [string,RequestInit][];
 expect(calls).toHaveLength(2);expect(calls[0][1].body).toBe(calls[1][1].body);expect(calls[0][1].headers).toEqual(calls[1][1].headers);
 expect(find(render(),n=>n.type==='fieldset').props.disabled).toBe(true);
});
