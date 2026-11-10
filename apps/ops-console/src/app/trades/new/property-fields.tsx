"use client";
import type { TradeBookingContext } from "@/lib/browser-api-client";
import type { EnrichedTicketDraft, TicketError } from "./ticket-model";
import {referenceRequest,type Page} from '@/features/tenant-reference/client';
import { GovernedSelector } from "./governed-selector";

const types: Record<string, string> = {TEXT: "Text", INTEGER: "Whole number", DECIMAL: "Decimal number", DATE: "Date", BOOLEAN: "Yes / no", REFERENCE: "Governed dropdown"};
const hints: Record<string, string> = {TEXT: "Up to 2,000 characters.", INTEGER: "A whole number, up to 30 digits; negative values are allowed.", DECIMAL: "Use a decimal point, without commas. Up to 18 whole-number and 12 decimal digits.", DATE: "Choose a calendar date.", BOOLEAN: "Choose Yes or No, or leave an optional value unspecified.", REFERENCE: "Search the tenant catalogue and select a published entry. Free text is not a saved value."};

type PropertyDraft=Pick<EnrichedTicketDraft,"properties"|"propertyLabels"|"tagIds">;
export function PropertyFields({context, draft, errors, onChange}: {context: TradeBookingContext; draft: PropertyDraft; errors: TicketError[]; onChange: (patch: Partial<PropertyDraft>) => void}) {
  function field(definition: TradeBookingContext["properties"][number]) {
    const id = `properties.${definition.definitionId}`;
    const value = draft.properties[definition.definitionId];
    const error = errors.find(e => e.field === id);
    const help = [definition.description, hints[definition.valueType]].filter(Boolean).join(" ");
    const describedBy = `${id}-help${error ? ` ${id}-error` : ""}`;
    const set = (value: string | boolean | undefined) => onChange({properties: {...draft.properties, [definition.definitionId]: value}});
    if(definition.inheritedOnly)return <div className="ticket-property" key={id}><strong>{definition.label}</strong><p>{draft.propertyLabels?.[definition.definitionId]??String(value??'Not supplied')}</p><p className="muted">Preserved from the original booking. This profile does not allow a new value for this field.</p><button type="button" onClick={()=>set(undefined)}>Clear inherited value</button></div>;
    if (definition.valueType === "CHOICE" || (definition.valueType === "REFERENCE" && !definition.catalogueId)) {
      return <div className="ticket-property ticket-property-error" id={id} tabIndex={-1} key={id} role="alert">{definition.label}: this field is unavailable. Reopen the booking ticket to refresh its configuration.</div>;
    }
    return <div className={`ticket-property${error ? " ticket-property-error" : ""}`} key={id}>
      {definition.valueType === "REFERENCE" ? <GovernedSelector tenantId={context.tenantId} catalogueId={definition.catalogueId!} id={id} label={definition.label} value={String(value ?? "")} displayValue={draft.propertyLabels?.[definition.definitionId]} required={definition.required} description={help} validationError={error?.message} onSelect={(value, label) => onChange({properties: {...draft.properties, [definition.definitionId]: value}, propertyLabels: {...draft.propertyLabels, [definition.definitionId]: label}})} loadOptions={async(query,offset)=>{
        if(!context.tradeProfile)throw new Error('Select a strategy and load its configuration first.');
        const page=await referenceRequest<Page<{id:string;recordId?:string;code?:string;label:string;versionNo?:number}>>(context.tenantId,`options?sourceKey=catalogue:${definition.catalogueId}&consumer=booking&strategyId=${context.tradeProfile.strategyId}&q=${encodeURIComponent(query)}&offset=${offset}&limit=26`);
        return page.items.map(r=>({recordVersionId:r.id,recordId:r.recordId??r.id,code:r.code??'',label:r.label,description:null,versionNo:r.versionNo??1,status:'ACTIVE' as const}));
      }} /> : <>
        <label htmlFor={id}>{definition.label} <span className="ticket-property-rule">{definition.required ? "(required)" : "(optional)"}</span></label>
        <small className="ticket-property-type">{types[definition.valueType]}</small>
        <p className="ticket-property-hint" id={`${id}-help`}>{help}</p>
        {error ? <p className="ticket-property-message" id={`${id}-error`}>{error.message}</p> : null}
        {definition.valueType === "BOOLEAN" ? <select id={id} aria-invalid={!!error} aria-describedby={describedBy} required={definition.required} value={value === undefined ? "" : String(value)} onChange={e => set(e.target.value === "" ? undefined : e.target.value === "true")}><option value="">Not specified</option><option value="true">Yes</option><option value="false">No</option></select> : <input id={id} aria-invalid={!!error} aria-describedby={describedBy} required={definition.required} type={definition.valueType === "DATE" ? "date" : "text"} inputMode={definition.valueType === "DECIMAL" || definition.valueType === "INTEGER" ? "decimal" : undefined} maxLength={definition.valueType === "TEXT" ? 2000 : 80} value={String(value ?? "")} onChange={e => set(e.target.value)} />}
      </>}
    </div>;
  }
  const required = context.properties.filter(p => p.required), optional = context.properties.filter(p => !p.required);
  return <section className="ticket-properties" aria-labelledby="ticket-properties-heading">
    <header><h2 id="ticket-properties-heading">Trade properties</h2><p>Additional information selected by this strategy’s trade profile. Complete required properties before reviewing the booking; optional values can be left blank.</p></header>
    {!context.properties.length ? <p className="muted">No custom trade properties selected for this strategy.</p> : null}
    {Object.keys(draft.properties).filter(id=>!context.properties.some(p=>p.definitionId===id)&&draft.properties[id]!==undefined).map(id=><p key={id} role="alert">A retained draft value is not used by this profile. <button type="button" onClick={()=>{const properties={...draft.properties};delete properties[id];onChange({properties});}}>Remove unavailable draft value</button></p>)}
    {required.length ? <fieldset className="ticket-section"><legend>Required properties</legend><div className="ticket-property-list">{required.map(field)}</div></fieldset> : null}
    {optional.length ? <fieldset className="ticket-section"><legend>Optional properties</legend><div className="ticket-property-list">{optional.map(field)}</div></fieldset> : null}
    <fieldset className="ticket-section"><legend>Trade tags (optional)</legend><p className="ticket-property-hint" id="ticket-tags-help">Select any applicable tenant tags. Tags are separate from property values.</p>{context.tags.length ? <div className="ticket-tags">{context.tags.map(tag => <label key={tag.tagId}><input type="checkbox" aria-describedby="ticket-tags-help" checked={draft.tagIds.includes(tag.tagId)} onChange={e => onChange({tagIds: e.target.checked ? [...draft.tagIds, tag.tagId] : draft.tagIds.filter(id => id !== tag.tagId)})} />{tag.label}</label>)}</div> : <p className="muted">No trade tags configured.</p>}</fieldset>
  </section>;
}
