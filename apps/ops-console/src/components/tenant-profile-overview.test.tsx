import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect,vi} from 'vitest';
vi.mock('server-only',()=>({}));
import {TenantProfileOverview} from './tenant-profile-overview';
it('distinguishes tenant subscriptions from the selected user access without exposing administrator links',()=>{
 const html=renderToStaticMarkup(<TenantProfileOverview workspace={{tenantId:'a',tenantCode:'ALPHA',tenantName:'Alpha',membershipRole:'MEMBER',userName:'Alice',moduleCodes:['TRADING'],tenantModuleCodes:['TRADING','MARKET_DATA'],permissionCodes:['TRADE_READ']}}/>);
 expect(html).toContain('Alice');
 expect(html).toContain('Market data');
 expect(html).toContain('Not assigned to you');
 expect(html).not.toContain('Manage users and groups');
 expect(html).not.toContain('Manage trade configuration');
});
it('exposes management navigation only for granted actions',()=>{
 const html=renderToStaticMarkup(<TenantProfileOverview workspace={{tenantId:'a',tenantCode:'A',tenantName:'Alpha',membershipRole:'TENANT_ADMIN',moduleCodes:[],permissionCodes:['ACCESS_MANAGE','TRADE_CONFIGURE']}}/>);
 expect(html).toContain('Manage users and groups');
 expect(html).toContain('Manage trade configuration');
 expect(html).toContain('No modules enabled');
});
