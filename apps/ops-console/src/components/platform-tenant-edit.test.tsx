import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {PlatformTenants} from './platform-tenants';
const tenant={tenantId:'a',code:'ALPHA',name:'Alpha',status:'ACTIVE',contactName:'Operations',contactEmail:'ops@example.org',profileVersion:3,moduleCodes:['TRADING'],users:[]};
it('offers separate profile and status actions and displays the operational contact',()=>{
 const html=renderToStaticMarkup(<PlatformTenants initial={{tenants:[tenant],modules:[]}}/>);
 expect(html).toContain('Edit tenant');expect(html).toContain('Suspend tenant');
 expect(html).toContain('ops@example.org');
 expect(html).not.toContain('<form');
});
it('offers reactivation but not module edits for a suspended tenant',()=>{
 const html=renderToStaticMarkup(<PlatformTenants initial={{tenants:[{...tenant,status:'SUSPENDED'}],modules:[{code:'TRADING',name:'Trading'}]}}/>);
 expect(html).toContain('Reactivate tenant');
 expect(html).toMatch(/<fieldset[^>]*disabled/);
});
