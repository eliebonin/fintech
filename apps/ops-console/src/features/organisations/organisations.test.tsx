import {describe,it,expect,vi,afterEach} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {OrganisationConsole} from './organisation-console';
import {organisationRequest,saveBody,type OrganisationDetail} from './organisation-client';

afterEach(()=>vi.unstubAllGlobals());
describe('organisation command boundaries',()=>{
 it('retains both role versions and only edits explicitly curated lists',()=>{
  const detail:OrganisationDetail={organisationId:'party',versionNo:2,label:null,internalCode:null,notes:null,
   displayName:'Synthetic party',legalName:'Synthetic party Ltd',leis:[],status:'ACTIVE',history:[],
   policies:{COUNTERPARTY:{mode:'CURATED',versionNo:4},EXECUTING_BROKER:{mode:'LEGACY',versionNo:0}},
   roles:{COUNTERPARTY:true,EXECUTING_BROKER:false}};
  const data=new FormData();data.set('label','Tenant name');data.set('notes','Private');data.set('reason','Remove counterparty');
  expect(saveBody(detail,data)).toEqual({expectedVersion:2,expectedRoleVersions:{COUNTERPARTY:4,EXECUTING_BROKER:0},
   label:'Tenant name',internalCode:null,notes:'Private',reason:'Remove counterparty',roles:{COUNTERPARTY:false}});
 });
 it('does not treat a malformed successful response as a confirmed write',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({data:null}),{status:200})));
  await expect(organisationRequest('tenant','organisations/party',{})).rejects.toThrow(/confirmed/);
 });
 it('rejects incomplete detail responses before clearing the retained command',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({data:{organisationId:'party',displayName:'Party',versionNo:0,
   roles:{COUNTERPARTY:false,EXECUTING_BROKER:false},history:[],policies:{COUNTERPARTY:{mode:'LEGACY',versionNo:0},EXECUTING_BROKER:{mode:'LEGACY',versionNo:0}}}}),{status:200})));
  await expect(organisationRequest('tenant','organisations/party',{})).rejects.toThrow(/confirmed/);
 });
 it('keeps conflicts identifiable for reconciliation',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({error:{message:'Changed',code:'organisation.conflict'}}),{status:409})));
  await expect(organisationRequest('tenant','organisations/party',{})).rejects.toMatchObject({status:409,code:'organisation.conflict'});
 });
 it('shows loading rather than claiming the tenant has no organisations',()=>{
  const html=renderToStaticMarkup(<OrganisationConsole tenantId="tenant"/>);
  expect(html).toContain('Loading organisations');expect(html).not.toContain('No organisations match');
  expect(html).toContain('Counterparties');expect(html).toContain('Executing brokers');
 });
});
