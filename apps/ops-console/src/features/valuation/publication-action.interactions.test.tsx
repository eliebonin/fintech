import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({open:false}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:()=>[h.open,(value:boolean)=>{h.open=value;}],useRef:()=>({current:null})}));
import {PublicationAction} from './publication-action';
import {renderToStaticMarkup} from 'react-dom/server';
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;for(const child of[node.props?.children].flat(Infinity)){const result=find(child,predicate);if(result)return result;}}
afterEach(()=>{h.open=false;});
it('repeats the selected run and warnings before the consequential publication',()=>{
 h.open=true;
 const html=renderToStaticMarkup(<PublicationAction status="STAGED" stagedBy="maker" actorId="reviewer" canReview busy={false} onPublish={()=>{}}
  context={{strategy:'FCAGF',period:'19 Oct → 20 Oct',policy:'EOD v3',currency:'GBP',total:'22274.22',warnings:['Interest not supplied']}}/>);
 expect(html).toContain('FCAGF');expect(html).toContain('22,274.22');expect(html).toContain('Interest not supplied');
 expect(html).toContain('EOD v3');expect(html).toContain('Confirm publication');
});
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
