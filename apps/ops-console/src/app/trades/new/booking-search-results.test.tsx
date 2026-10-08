import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
import {ReadinessResults,readinessLabel,type BookingSearchItem} from './booking-search-results';

it('uses the raw page cursor when revoked matches are omitted',()=>{
  const html=renderToStaticMarkup(<ReadinessResults {...props} items={[]} total={25} hasMore={false}/>);
  expect(html).not.toContain('Load more matches');
  expect(html).toContain('No matching instruments.');
});

const items:BookingSearchItem[]=[
  {id:'ready',instrumentId:'parent',label:'Eligible security',bookingEligible:true},
  {id:'draft',instrumentId:'draft-parent',label:'Draft security',bookingEligible:false,readinessStatus:'MISSING_CONFIGURATION',ineligibilityMessage:'Approved definition required.'},
  {id:'btc',instrumentId:'btc-parent',label:'Physical BTC',bookingEligible:false,readinessStatus:'CREATION_ONLY',ineligibilityMessage:'Physical booking is deferred.'},
];
const props={items,loading:false,searched:true,total:30,showUnavailable:false,onShowUnavailable:vi.fn(),onSelect:vi.fn(),onLoadMore:vi.fn()};
function html(changes:Partial<typeof props>={}){return renderToStaticMarkup(<ReadinessResults {...props} {...changes}/>);}
function find(node:any,test:(n:any)=>boolean):any{
  if(!node||typeof node!=='object')return;
  if(test(node))return node;
  for(const child of [node.props?.children].flat(Infinity)){const found=find(child,test);if(found)return found;}
}

it('defaults to ready results without losing the raw pagination cursor',()=>{
  const output=html();
  expect(output).toContain('Eligible security');
  expect(output).not.toContain('Draft security');
  expect(output).toContain('1 shown');
  expect(output).toContain('2 unavailable in 3 loaded matches');
  expect(output).toContain('Load more matches');
});
it('makes unavailable reasons inspectable without offering selection',()=>{
  const output=html({showUnavailable:true});
  expect(output).toContain('Missing configuration');expect(output).toContain('Creation-only');
  expect(output).toContain('Approved definition required.');
  expect(output).toContain('/instruments/draft-parent');
  expect(output.match(/Select instrument/g)).toHaveLength(1);
});
it('distinguishes unavailable loaded matches from an empty search and keeps paging',()=>{
  const output=html({items:items.slice(1)});
  expect(output).toContain('none of the loaded matches are ready');
  expect(output).toContain('Load more matches');
  expect(html({items:[],total:0})).toContain('No matching instruments.');
});
it('announces loading without marking the whole list as a live region',()=>{
  expect(html({loading:true})).toContain('role="status">Checking readiness');
  expect(html()).not.toContain('aria-live="assertive"');
});
it('passes the checkbox, raw paging and selection actions to the correct handlers',()=>{
  const selected=vi.fn(),more=vi.fn(),filter=vi.fn();
  const tree=ReadinessResults({...props,onSelect:selected,onLoadMore:more,onShowUnavailable:filter});
  find(tree,n=>n.type==='input').props.onChange({target:{checked:true}});
  find(tree,n=>n.type==='button'&&n.props.children==='Load more matches').props.onClick();
  find(tree,n=>n.type==='button'&&n.props.children==='Select instrument').props.onClick();
  expect(filter).toHaveBeenCalledWith(true);expect(more).toHaveBeenCalledOnce();expect(selected).toHaveBeenCalledWith('ready');
});
it('does not guess categories from messages or unknown codes',()=>{
  expect(readinessLabel({...items[0],bookingEligible:false,ineligibilityMessage:'physical future'})).toBe('Not ready');
  expect(readinessLabel({...items[0],readinessStatus:'FUTURE_UNKNOWN_STATUS'})).toBe('Not ready');
  expect(readinessLabel({...items[0],bookingEligible:false,readinessStatus:'READY'})).toBe('Not ready');
});
