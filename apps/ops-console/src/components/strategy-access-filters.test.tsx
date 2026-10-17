import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
const state=vi.hoisted(()=>({values:[] as any[],cursor:0}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),
 useState:(initial:any)=>{const i=state.cursor++;if(!(i in state.values))state.values[i]=initial;return [state.values[i],(v:any)=>state.values[i]=typeof v==='function'?v(state.values[i]):v];},
 useCallback:(fn:any)=>fn,useEffect:()=>{},
}));
import {StrategyAccessMatrix} from './strategy-access-matrix';
function find(node:any,test:(node:any)=>boolean):any {if(!node||typeof node!=='object')return;if(test(node))return node;for(const child of [node.props?.children].flat(Infinity)){const result=find(child,test);if(result)return result;}}
function render(){state.cursor=0;return StrategyAccessMatrix({initial:{strategies:[{strategyId:'s',name:'Fund',status:'ACTIVE'},{strategyId:'other',name:'Other',status:'ACTIVE'}],rows:[
 {userId:'a',name:'Alice',strategyId:'s',actions:['TRADE_READ'],grantSources:{TRADE_READ:['Readers']}},
 {userId:'b',name:'Bob',strategyId:'s',actions:[],grantSources:{}},
 {userId:'c',name:'Carol',strategyId:'other',actions:['TRADE_WRITE'],grantSources:{TRADE_WRITE:['Traders']}}
 ]}});}
const row=(tree:any,name:string)=>find(tree,n=>n.type==='th'&&n.props.scope==='row'&&n.props.children===name);
afterEach(()=>{state.values=[];state.cursor=0;});
it('filters without mixing rows from another strategy',()=>{
 expect(row(render(),'Alice')).toBeDefined();expect(row(render(),'Carol')).toBeUndefined();
 find(render(),n=>n.type==='select'&&n.props.value==='all').props.onChange({target:{value:'none'}});
 expect(row(render(),'Alice')).toBeUndefined();expect(row(render(),'Bob')).toBeDefined();
 find(render(),n=>n.type==='select'&&n.props.value==='none').props.onChange({target:{value:'all'}});
 find(render(),n=>n.type==='input'&&n.props.type==='search').props.onChange({target:{value:' ALICE '}});
 expect(row(render(),'Alice')).toBeDefined();expect(row(render(),'Bob')).toBeUndefined();
});
it('switches strategy and explains a filter with no matches',()=>{
 find(render(),n=>n.type==='select'&&n.props.value==='s').props.onChange({target:{value:'other'}});
 expect(row(render(),'Carol')).toBeDefined();expect(row(render(),'Alice')).toBeUndefined();
 find(render(),n=>n.type==='select'&&n.props.value==='all').props.onChange({target:{value:'none'}});
 expect(find(render(),n=>n.props?.role==='status'&&typeof n.props.children==='string'&&n.props.children.startsWith('No users match'))).toBeDefined();
});
