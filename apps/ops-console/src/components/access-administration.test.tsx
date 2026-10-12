import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ContextSelector} from './context-selector';
import {PlatformTenants} from './platform-tenants';
import {TenantAccessConsole,UserAccessEditor} from './tenant-access-console';
const registry={tenants:[{tenantId:'a',code:'A',name:'Alpha',status:'ACTIVE',moduleCodes:['TRADING'],users:[{userId:'u',name:'Trader Alice',role:'MEMBER'}]}],modules:[{code:'TRADING',name:'Trading'},{code:'MARKET_DATA',name:'Market data'}]};
it('shows platform and tenant/user selection as distinct contexts',()=>{
 const html=renderToStaticMarkup(<ContextSelector initial={registry}/>);
 expect(html).toContain('Platform administration');
 expect(html).toContain('Alpha');
 expect(html).toContain('User');
 expect(html).toContain('development');
});
it('makes enabled and disabled tenant subscriptions visible without listing trades',()=>{
 const html=renderToStaticMarkup(<PlatformTenants initial={registry}/>);
 expect(html).toContain('Alpha');expect(html).toContain('Trading');expect(html).toContain('Market data');
 expect(html).toContain('checked');expect(html).not.toContain('Book trade');
});
it('shows tenant-local groups and action permissions instead of role-name assumptions',()=>{
 const html=renderToStaticMarkup(<TenantAccessConsole initial={{tenantId:'a',userId:'admin',tenantModuleCodes:['TRADING'],
  users:[{userId:'u',name:'Trader Alice',role:'MEMBER',status:'ACTIVE',accountStatus:'ACTIVE',groupIds:['g'],permissions:['TRADE_READ','TRADE_WRITE']}],
  groups:[{groupId:'g',code:'TRADERS',name:'Traders',description:null,status:'ACTIVE',actions:['TRADE_READ','TRADE_WRITE']}],
  actions:[{code:'TRADE_READ',moduleCodes:['TRADING']},{code:'TRADE_WRITE',moduleCodes:['TRADING']}]}}/>);
 expect(html).toContain('Trader Alice');expect(html).toContain('Traders');expect(html).toContain('2 actions');
 expect(html).toContain('Groups');expect(html).toContain('Add user');
});
it('allows removing an existing suspended group assignment',()=>{
 const html=renderToStaticMarkup(<UserAccessEditor user={{userId:'u',name:'Alice',role:'MEMBER',status:'ACTIVE',accountStatus:'ACTIVE',groupIds:['g'],permissions:[]}}
  groups={[{groupId:'g',code:'OLD',name:'Old group',description:null,status:'SUSPENDED',actions:[]}]} busy={false} cancel={()=>{}} save={async()=>true} change={async()=>true}/>);
 const checked=html.match(/<input[^>]*type="checkbox"[^>]*>/g)?.find(input=>input.includes('checked'));
 expect(checked).toBeDefined();expect(checked).not.toContain('disabled');
});
