'use client';
import type {TradeBookingContext} from '@/lib/browser-api-client';
import {referenceRequest,type Page} from '@/features/tenant-reference/client';
import type {ProfileContext} from '@/features/trade-profiles/client';
import type {EnrichedTicketDraft,TicketError} from './ticket-model';
import {ValuationRecognitionFields} from './valuation-recognition-fields';
import {GovernedSelector} from './governed-selector';
type PartyDraft=Pick<EnrichedTicketDraft,'counterpartyOrganisationId'|'counterpartyName'|'executingBrokerOrganisationId'|'executingBrokerName'|'traderPersonId'|'traderName'|'tradeDatetime'|'valuationEffectiveDate'|'valuationOverrideReason'>;
const fields=[
 {key:'COUNTERPARTY',attribute:'counterpartyOrganisationId',name:'counterpartyName',label:'Counterparty'},
 {key:'EXECUTING_BROKER',attribute:'executingBrokerOrganisationId',name:'executingBrokerName',label:'Executing broker'},
 {key:'TRADER',attribute:'traderPersonId',name:'traderName',label:'Trader'},
] as const;
export function PartyFields({draft,actor,onChange,errors=[],tenantId,profile,counterpartyRequired=false}:{draft:PartyDraft;actor:string;tenantId?:string;profile?:TradeBookingContext['tradeProfile'];counterpartyRequired?:boolean;errors?:TicketError[];onChange:(patch:Partial<PartyDraft>)=>void}){
 return <><ValuationRecognitionFields draft={draft} onChange={onChange}/><fieldset className="ticket-section"><legend>Parties and responsibility</legend><p className="muted">Choose from your tenant's eligible organisations and active traders. This selection is not credit approval.</p><div className="ticket-grid">{fields.map(field=>{
  const rule=(profile as ProfileContext|null)?.fields.find(r=>r.standardFieldKey===field.key);
  const native=field.key==='COUNTERPARTY'&&counterpartyRequired;
  if(!native&&(!rule||rule.requirement==='NOT_USED'))return draft[field.attribute]?<div className="ticket-party" key={field.key}><strong>{field.label}</strong><p>{draft[field.name]||'Retained draft selection'}</p><p className="muted">This profile does not use this field. Only an unchanged original value can be kept on a linked correction.</p><button type="button" onClick={()=>onChange({[field.attribute]:'',[field.name]:''})}>Clear {field.label.toLowerCase()}</button></div>:null;
  const required=native||rule?.requirement==='REQUIRED';
  return <GovernedSelector key={field.key} tenantId={tenantId??''} catalogueId="" id={field.attribute} label={field.label} value={draft[field.attribute]??''} displayValue={draft[field.name]} required={required} description="Select an eligible entry. The server rechecks it at booking." validationError={errors.find(issue=>issue.field===field.attribute)?.message} onSelect={(id,name)=>onChange({[field.attribute]:id,[field.name]:name})} loadOptions={async(query,offset)=>{
   if(!tenantId||!profile)throw new Error('Select a strategy and load its trade configuration first.');
   const page=await referenceRequest<Page<{id:string;label:string}>>(tenantId,`options?sourceKey=standard:${field.key}&consumer=booking&strategyId=${profile.strategyId}&q=${encodeURIComponent(query)}&offset=${offset}&limit=26`);
   return page.items.map(r=>({recordVersionId:r.id,recordId:r.id,code:'',label:r.label,description:null,versionNo:1,status:'ACTIVE' as const}));
  }}/>;
 })}</div><p className="muted">Booked by: {actor||'Authenticated account'} (assigned by the server)</p></fieldset></>;
}
