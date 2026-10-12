import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {TenantAccessConsole} from './tenant-access-console';
import {ContextSelector} from './context-selector';
import type {TenantAccess} from '@/lib/access-administration';

const access:TenantAccess={tenantId:'a',userId:'admin',tenantModuleCodes:['TRADING'],users:[{userId:'u',name:'Alice',role:'MEMBER',status:'ACTIVE',accountStatus:'ACTIVE',groupIds:['g'],permissions:['TRADE_READ']}],groups:[{groupId:'g',code:'TRADERS',name:'Traders',description:null,status:'ACTIVE',actions:['TRADE_READ']}],actions:[{code:'TRADE_READ',moduleCodes:['TRADING']}]};
it('browses members without exposing editable role and assignment controls',()=>{
 const html=renderToStaticMarkup(<TenantAccessConsole initial={access}/>);
 expect(html).toContain('type="search"');
 expect(html).toContain('Manage Alice');
 expect(html).not.toContain('Save groups');
 expect(html).not.toContain('<form');
});
it('connects the selected user tab to its accessible panel',()=>{
 const html=renderToStaticMarkup(<TenantAccessConsole initial={access}/>);
 expect(html).toContain('aria-controls="access-users-panel"');
 expect(html).toContain('role="tabpanel"');
 expect(html).toContain('aria-labelledby="access-users-tab"');
});
it('offers compact group browsing without automatically opening a creation form',()=>{
 const html=renderToStaticMarkup(<TenantAccessConsole initial={access} initialTab="groups"/>);
 expect(html).toContain('TRADERS');
 expect(html).toContain('Edit Traders');
 expect(html).not.toContain('<form');
});
it('explains why entering a workspace is unavailable before choosing a tenant and user',()=>{
 const html=renderToStaticMarkup(<ContextSelector initial={{tenants:[],modules:[]}}/>);
 expect(html).toContain('Choose a tenant and user to continue');
 expect(html).toContain('No active tenants');
 expect(html).toContain('role="status"');
});
