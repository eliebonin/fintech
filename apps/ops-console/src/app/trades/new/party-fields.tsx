"use client";
import { useRef, useState } from "react";
import { listOrganisationsFromBff, searchTradeTradersFromBff } from "@/lib/browser-api-client";
import type { EnrichedTicketDraft, TicketError } from "./ticket-model";
import { configurationRequest } from "@/lib/trade-configuration-client";
type Option = {id:string;name:string};
type PartyDraft=Pick<EnrichedTicketDraft,"counterpartyOrganisationId"|"counterpartyName"|"executingBrokerOrganisationId"|"executingBrokerName"|"traderPersonId"|"traderName">;
function PartySearch({label,selected,onSelect,people=false,field,fieldError,tenantId,required=false}:{label:string;selected?:string;onSelect:(id:string,name:string)=>void;people?:boolean;field:string;fieldError?:string;tenantId?:string;required?:boolean}) {
  const [query,setQuery]=useState(""); const [options,setOptions]=useState<Option[]>([]);
  const [loading,setLoading]=useState(false); const [error,setError]=useState(""); const sequence=useRef(0);
  async function search() {
    const serial=++sequence.current;setLoading(true);setError("");
    try {
      const role=people?"TRADER":field==="counterpartyOrganisationId"?"COUNTERPARTY":"EXECUTING_BROKER";
      const found:Option[] = tenantId ? (await configurationRequest<{id:string;label:string}[]>(tenantId,`candidates/${role}?q=${encodeURIComponent(query.trim())}`)).map(r=>({id:r.id,name:r.label})) : people ? (await searchTradeTradersFromBff(query.trim())).data.map(p=>({id:p.personId,name:p.displayName})) : (await listOrganisationsFromBff(fetch,query.trim())).data.map(o=>({id:o.organisationId,name:o.displayName}));
      if(serial===sequence.current)setOptions(found);
    }catch(caught){if(serial===sequence.current)setError(caught instanceof Error?caught.message:"Search failed.");}
    finally{if(serial===sequence.current)setLoading(false);}
  }
  return <div className="ticket-party"><label>{label} ({required?"required":"optional"})<input id={field} aria-invalid={!!fieldError} aria-describedby={`${field}-error`} aria-label={`Search ${label.toLowerCase()}`} value={query} maxLength={250} onChange={e=>{sequence.current++;setQuery(e.target.value);setOptions([]);setLoading(false);}} placeholder={people?"Find a tenant member":"Find a shared organisation"} /></label><button type="button" onClick={search} disabled={loading}>{loading?"Searching…":`Search ${label.toLowerCase()}`}</button>{selected?<p>{selected} <button type="button" onClick={()=>onSelect("","")}>Clear {label.toLowerCase()}</button></p>:<p className="muted">Not specified</p>}<small id={`${field}-error`}>{fieldError}</small><ul className="ticket-options">{options.map(o=><li key={o.id}><button type="button" onClick={()=>{onSelect(o.id,o.name);setOptions([]);setQuery("");}}>{o.name}</button></li>)}</ul>{error?<p role="alert">{error}</p>:null}<span role="status" className="muted">{!loading&&options.length?`${options.length} matching results`:""}</span></div>;
}
export function PartyFields({draft,actor,onChange,errors=[],tenantId,counterpartyRequired=false}:{draft:PartyDraft;actor:string;tenantId?:string;counterpartyRequired?:boolean;errors?:TicketError[];onChange:(patch:Partial<PartyDraft>)=>void}) {
  return <fieldset className="ticket-section"><legend>Parties and responsibility</legend><p className="muted">Tenant eligibility is applied where a curated list has been published. This is not credit approval. Traders must also remain active tenant members.</p><div className="ticket-grid"><PartySearch tenantId={tenantId} field="counterpartyOrganisationId" required={counterpartyRequired} fieldError={errors.find(issue=>issue.field==="counterpartyOrganisationId")?.message} label="Counterparty" selected={draft.counterpartyName} onSelect={(id,name)=>onChange({counterpartyOrganisationId:id,counterpartyName:name})}/><PartySearch tenantId={tenantId} field="executingBrokerOrganisationId" fieldError={errors.find(issue=>issue.field==="executingBrokerOrganisationId")?.message} label="Executing broker" selected={draft.executingBrokerName} onSelect={(id,name)=>onChange({executingBrokerOrganisationId:id,executingBrokerName:name})}/><PartySearch tenantId={tenantId} field="traderPersonId" fieldError={errors.find(issue=>issue.field==="traderPersonId")?.message} label="Trader" people selected={draft.traderName} onSelect={(id,name)=>onChange({traderPersonId:id,traderName:name})}/></div><p className="muted">Booked by: {actor || "Authenticated account"} (assigned by the server)</p></fieldset>;
}
