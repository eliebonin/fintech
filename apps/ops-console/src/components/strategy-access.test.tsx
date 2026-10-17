import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {GroupForm,TenantAccessConsole} from './tenant-access-console';
import {StrategyAccessMatrix} from './strategy-access-matrix';
import {StrategyConsole} from '@/app/strategies/strategy-console';

it('requires an explicit strategy scope and explains empty/future selections',()=>{
 const html=renderToStaticMarkup(<GroupForm data={{tenantId:'t',userId:'u',users:[],groups:[],tenantModuleCodes:['TRADING'],actions:[],strategies:[{strategyId:'s',name:'Equity Fund',status:'ACTIVE'}]}} busy={false} save={async()=>{}} cancel={()=>{}}/>);
 expect(html).toContain('Selected strategies only');
 expect(html).toContain('empty selection grants no strategy access');
 expect(html).toContain('Equity Fund');
 expect(html).toContain('including future ones');
 expect(html).toContain('Preview access changes');
 expect(html).not.toContain('Confirm and save group');
});
it('shows a strategy-specific access matrix with grant sources and denied users',()=>{
 const html=renderToStaticMarkup(<StrategyAccessMatrix initial={{strategies:[{strategyId:'s',name:'Equity Fund',status:'ACTIVE'}],rows:[{userId:'u',name:'Alice',strategyId:'s',actions:['TRADE_READ'],grantSources:{TRADE_READ:['Readers']}},{userId:'v',name:'Bob',strategyId:'s',actions:[],grantSources:{}}]}}/>);
 expect(html).toContain('Alice');expect(html).toContain('Readers');expect(html).toContain('No strategy access');
 expect(html).toContain('does not grant access to trades or valuations');
});
it('explains that the matrix is loading before results arrive',()=>{
 expect(renderToStaticMarkup(<StrategyAccessMatrix/>)).toContain('Loading strategy access');
});
it('exposes group strategy scope in the register without opening an editor',()=>{
 const html=renderToStaticMarkup(<TenantAccessConsole initialTab="groups" initial={{tenantId:'t',userId:'u',users:[],tenantModuleCodes:['TRADING'],actions:[],strategies:[],groups:[
  {groupId:'a',code:'ALL',name:'Everyone',description:null,status:'ACTIVE',actions:[],scopeMode:'ALL'},
  {groupId:'b',code:'NONE',name:'Unassigned',description:null,status:'ACTIVE',actions:[],scopeMode:'SELECTED',strategyIds:[]}
 ]}}/>);
 expect(html).toContain('Strategy scope');expect(html).toContain('Current and future strategies');expect(html).toContain('No strategies selected');
});
it('keeps matrix access status visible while making evidence expandable',()=>{
 const html=renderToStaticMarkup(<StrategyAccessMatrix initial={{strategies:[{strategyId:'s',name:'Fund',status:'ACTIVE'}],rows:[{userId:'u',name:'Alice',strategyId:'s',actions:['TRADE_READ'],grantSources:{TRADE_READ:['Readers']}}]}}/>);
 expect(html).toContain('Search users');expect(html).toContain('Access filter');
 expect(html).toContain('View trades');expect(html).toContain('<details');expect(html).toContain('Why this access?');
});
it('offers explicit initial selected groups without pretending creation grants ownership',()=>{
 const html=renderToStaticMarkup(<StrategyConsole initialStrategies={[]} canWrite createOnly accessGroups={[{groupId:'s',name:'Equity Traders',scopeMode:'SELECTED'},{groupId:'a',name:'All operations',scopeMode:'ALL'}]}/>);
 expect(html).toContain('initialAccessGroupIds');expect(html).toContain('Equity Traders');
 expect(html).not.toContain('All operations');
 expect(html).toContain('does not automatically grant you operational access');
});
