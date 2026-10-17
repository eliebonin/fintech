import React from 'react';
import {expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {EffectiveAccessView} from './effective-access';
import type {EffectiveAccess} from '@/lib/access-administration';

const data:EffectiveAccess={tenantId:'t',userId:'u',name:'Alice',role:'MEMBER',accountStatus:'ACTIVE',membershipStatus:'ACTIVE',asOfDate:'2026-10-13',strategyScope:'All strategies in this tenant',groups:[{groupId:'g',name:'Old readers',status:'SUSPENDED',actions:['TRADE_READ']}],actions:[{code:'ACCESS_MANAGE',allowed:false,grantSources:[],blockers:['NO_ACTIVE_ACTION_GRANT'],moduleCodes:[]}],modules:[{code:'TRADING',name:'Trading',enabled:true,accessible:false,deliveryStatus:'BOUNDED_ALPHA',deliveryNote:'Booking, not accounting',actions:[{code:'TRADE_READ',allowed:false,grantSources:[],blockers:['NO_ACTIVE_ACTION_GRANT'],moduleCodes:['TRADING']}]},{code:'UCITS_CONTROLS',name:'UCITS controls',enabled:true,accessible:false,deliveryStatus:'PLANNED',deliveryNote:'Not delivered',actions:[]}]};

it('separates subscription, personal access and delivery; explains suspended grants',()=>{
 const html=renderToStaticMarkup(<EffectiveAccessView data={data}/>);
 expect(html).toContain('Alice');
 expect(html).toContain('Enabled');
 expect(html).toContain('No actions granted');
 expect(html).toContain('Planned');
 expect(html).toContain('No active group grants this action');
 expect(html).toContain('Old readers');
 expect(html).toContain('Suspended');
 expect(html).toContain('not accounting');
 expect(html).not.toContain('Unknown blocker');
});

it('renders allowed grant sources and inactive membership restrictions',()=>{
 const restricted={code:'TRADE_READ',allowed:false,grantSources:['Readers'],blockers:['MEMBERSHIP_INACTIVE'],moduleCodes:['TRADING']};
 const html=renderToStaticMarkup(<EffectiveAccessView data={{...data,membershipStatus:'SUSPENDED',actions:[restricted],modules:[{...data.modules[0],actions:[restricted]}]}}/>);
 expect(html).toContain('Membership is inactive');
 expect(html).toContain('Readers');
});
