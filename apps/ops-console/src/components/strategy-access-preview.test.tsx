import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
const state=vi.hoisted(()=>({values:[] as any[],cursor:0}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),
 useState:(initial:any)=>{const i=state.cursor++;if(!(i in state.values))state.values[i]=initial;return [state.values[i],(v:any)=>state.values[i]=typeof v==='function'?v(state.values[i]):v];},
 useRef:(value:any)=>{const i=state.cursor++;if(!(i in state.values))state.values[i]={current:value};return state.values[i];},
 useEffect:()=>{},
}));
import {GroupForm} from './tenant-access-console';
function find(node:any,test:(node:any)=>boolean):any {if(!node||typeof node!=='object')return;if(test(node))return node;for(const child of [node.props?.children].flat(Infinity)){const result=find(child,test);if(result)return result;}}
afterEach(()=>{state.values=[];state.cursor=0;vi.unstubAllGlobals();});
it('previews first, confirms the captured revision, and invalidates preview on edits',async()=>{
 const save=vi.fn().mockResolvedValue(undefined);
 const fetcher=vi.fn().mockResolvedValue(Response.json({changes:[],impactHash:'a'.repeat(64),includesFutureStrategies:true,unassignedNewGroup:false}));
 vi.stubGlobal('fetch',fetcher);
 vi.stubGlobal('FormData',class {get(name:string){return ({code:'READERS',name:'Readers',status:'ACTIVE',description:''} as any)[name];}});
 const render=()=>{state.cursor=0;return GroupForm({group:{groupId:'g',code:'READERS',name:'Readers',description:null,status:'ACTIVE',actions:['TRADE_READ'],scopeMode:'ALL',strategyIds:[],versionNo:3},data:{tenantId:'t',userId:'u',users:[],groups:[],tenantModuleCodes:['TRADING'],actions:[]},busy:false,cancel:()=>{},save});};
 await render().props.onSubmit({preventDefault(){},currentTarget:{}});
 expect(save).not.toHaveBeenCalled();
 const reviewed=render();
 expect(find(reviewed,n=>n.type==='dl')).toBeDefined();
 expect(find(reviewed,n=>n.type==='button'&&n.props.children==='Edit configuration')).toBeDefined();
 find(render(),n=>n.type==='button'&&n.props.children==='Confirm and save group').props.onClick();
 expect(save).toHaveBeenCalledWith(expect.objectContaining({expectedVersion:3,expectedImpactHash:'a'.repeat(64),scopeMode:'ALL',strategyIds:[]}));
 render().props.onChange();
 expect(find(render(),n=>n.type==='button'&&n.props.children==='Confirm and save group')).toBeUndefined();
});
