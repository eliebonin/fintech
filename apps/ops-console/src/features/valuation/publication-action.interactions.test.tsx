import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({open:false}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:()=>[h.open,(value:boolean)=>{h.open=value;}],useRef:()=>({current:null})}));
import {PublicationAction} from './publication-action';
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;for(const child of[node.props?.children].flat(Infinity)){const result=find(child,predicate);if(result)return result;}}
afterEach(()=>{h.open=false;});
it('opens a required review form and cancels without publishing',()=>{
 const publish=vi.fn();const render=()=>PublicationAction({status:'STAGED',stagedBy:'maker',actorId:'reviewer',canReview:true,busy:false,onPublish:publish});
 find(render(),n=>n.type==='button'&&n.props.children==='Publish valuation').props.onClick();
 expect(find(render(),n=>n.type==='textarea').props.required).toBe(true);
 expect(typeof find(render(),n=>n.type==='form').props.onSubmit).toBe('function');
 expect(publish).not.toHaveBeenCalled();
 find(render(),n=>n.type==='button'&&n.props.children==='Cancel').props.onClick();
 expect(find(render(),n=>n.type==='form')).toBeUndefined();expect(publish).not.toHaveBeenCalled();
});
it('requires a self-review acknowledgement and sends the explicit mode to its publication handler',()=>{
 const publish=vi.fn();const render=()=>PublicationAction({status:'STAGED',stagedBy:'maker',actorId:'maker',canReview:true,canSelfPublish:true,requiresSelfReview:true,busy:false,onPublish:publish});
 find(render(),n=>n.type==='button'&&n.props.children==='Publish without independent review').props.onClick();
 expect(find(render(),n=>n.props?.name==='confirmSelfPublication').props.required).toBe(true);
 expect(find(render(),n=>n.type==='textarea').props.required).toBe(true);
 const event={preventDefault(){}};find(render(),n=>n.type==='form').props.onSubmit(event);
 expect(publish).toHaveBeenCalledWith(event,true);
});
