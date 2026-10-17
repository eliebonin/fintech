import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as unknown[],cursor:0}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),
 useState:(initial:unknown)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=initial;
  return [h.slots[i],(next:unknown)=>{h.slots[i]=typeof next==='function'?next(h.slots[i]):next;}];}}));
import {StrategyConsole} from './strategy-console';

const context={tenantId:'tenant-a',userAccountId:'user-a'};
function find(node:any,predicate:(node:any)=>boolean):any{
 if(!node||typeof node!=='object')return;if(predicate(node))return node;
 for(const child of [node.props?.children].flat(Infinity)){const match=find(child,predicate);if(match)return match;}
}
function render(){h.cursor=0;return StrategyConsole({initialStrategies:[],canWrite:true,createOnly:true,writeContext:context});}
function formEvent(){
 const values=new FormData();values.set('strategyCode','ALPHA');values.set('displayName','Alpha');values.set('strategyType','FUND');
 const reset=vi.fn();const form={reset};
 // Node has no HTMLFormElement; retain real FormData iteration/getAll behaviour.
 vi.stubGlobal('FormData',class {constructor(){return values;}});
 return {preventDefault(){},currentTarget:form,reset};
}
afterEach(()=>{h.slots=[];h.cursor=0;vi.unstubAllGlobals();});

it('binds a strategy creation to the identity that prepared the form',async()=>{
 let submitted:RequestInit|undefined;
 let finish!:(response:Response)=>void;
 vi.stubGlobal('fetch',(_input:unknown,init:RequestInit)=>{submitted=init;return new Promise<Response>(resolve=>{finish=resolve;});});
 const event=formEvent();const pending=find(render(),n=>n.type==='form').props.onSubmit(event);
 // React clears currentTarget after dispatch; a successful response must use the captured form.
 (event as {currentTarget:unknown}).currentTarget=null;
 finish(Response.json({data:{strategyId:'s',displayName:'Alpha'}}));await pending;
 expect(new Headers(submitted?.headers).get('X-Expected-Tenant-Id')).toBe('tenant-a');
 expect(new Headers(submitted?.headers).get('X-Expected-User-Id')).toBe('user-a');
 expect(JSON.parse(String(submitted?.body))).toEqual({strategyCode:'ALPHA',displayName:'Alpha',strategyType:'FUND',initialAccessGroupIds:[]});
 expect(event.reset).toHaveBeenCalledOnce();
});
it('keeps the draft and blocks resubmission after a context conflict',async()=>{
 vi.stubGlobal('fetch',async()=>Response.json({error:{code:'TENANT_CONTEXT_CHANGED',message:'Reload this page before saving.'}},{status:409}));
 const event=formEvent();await find(render(),n=>n.type==='form').props.onSubmit(event);
 expect(event.reset).not.toHaveBeenCalled();
 const tree=render();
 expect(find(tree,n=>n.type==='button'&&n.props.type==='submit').props.disabled).toBe(true);
 expect(find(tree,n=>n.props?.role==='alert')).toBeDefined();
});
