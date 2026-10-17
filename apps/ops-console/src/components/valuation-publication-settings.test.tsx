import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
vi.mock('react',async original=>{const actual=await original<typeof import('react')>();return{...actual,useState:vi.fn(actual.useState)};});
import {useState} from 'react';
import {ValuationPublicationSettings} from './valuation-publication-settings';
it('explains standing and expiring opt-in without granting group permissions automatically',()=>{
 vi.mocked(useState).mockImplementationOnce(()=>[{enabled:false,active:false,validUntil:null,revision:0,reason:''},()=>{}] as any);
 const html=renderToStaticMarkup(<ValuationPublicationSettings tenantId="tenant" userId="admin"/>);
 expect(html).toContain('Independent review remains the default');expect(html).toContain('standing permission');
 expect(html.match(/<input[^>]*name="confirmChange"[^>]*>/)?.[0]).toContain('required');
 expect(html.match(/<textarea[^>]*name="reason"[^>]*>/)?.[0]).toContain('required');
 expect(html).toContain('Tenant opt-in — no automatic group grants');
});
