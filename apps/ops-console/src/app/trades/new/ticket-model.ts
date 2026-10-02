import type { TradeBookingRequest, TradeBookingContext } from "@/lib/browser-api-client";
import { BffApiError } from "@/lib/api-errors";
import { buildTicketPayload, validateBasicTicketFields, type TicketListing, type TicketDraft } from "./trade-ticket";

export type EnrichedTicketDraft = TicketDraft & {
  executingBrokerOrganisationId?: string;
  traderPersonId?: string;
  counterpartyName?: string;
  executingBrokerName?: string;
  traderName?: string;
  tradePurpose: "INVESTMENT"|"REBALANCING"|"HEDGING"|"OTHER";
  marketActivity?: "PRIMARY"|"SECONDARY";
  properties: Record<string, string|boolean|undefined>;
  propertyLabels?: Record<string,string>;
  tagIds: string[];
  externalReferences: {referenceType:"SOURCE_TRADE_ID"|"CLIENT_REFERENCE"|"BROKER_REFERENCE";referenceValue:string;sourceSystemId?:string}[];
};
export type TicketError = {field:string;message:string};

export function freezeBookingSubmission(payload:TradeBookingRequest,key:string,expectedTenantId:string) {
  return {payload:structuredClone(payload),key,expectedTenantId};
}

export function bookingFailureMode(error:unknown):"RETRY_REQUIRED"|"BLOCKED"|"EDITING" {
  if(!(error instanceof BffApiError)||error.status>=500||error.status===408||error.status===429)return "RETRY_REQUIRED";
  return error.status===409?"BLOCKED":"EDITING";
}

export function grossConsideration(quantity:string, price:string):string {
  if (![quantity,price].every(value=>/^\d+(?:\.\d+)?$/.test(value) && value.length <= 80)) return "—";
  const scale = (quantity.split(".")[1]?.length ?? 0)+(price.split(".")[1]?.length ?? 0);
  const product = BigInt(quantity.replace(".",""))*BigInt(price.replace(".",""));
  const digits = product.toString().padStart(scale+1,"0");
  return scale ? `${digits.slice(0,-scale)}.${digits.slice(-scale)}`.replace(/0+$/,"").replace(/\.$/,"") : digits;
}

export function validateEnrichedTicketDraft(draft:EnrichedTicketDraft, context:TradeBookingContext):TicketError[] {
  const errors:TicketError[]=validateBasicTicketFields(draft);
  return [...errors,...validateTradeAnnotations(draft,context)];
}

export function validateTradeAnnotations(draft:Pick<EnrichedTicketDraft,"tradePurpose"|"comment"|"properties"|"externalReferences">, context:TradeBookingContext):TicketError[] {
  const errors:TicketError[]=[];
  if (draft.tradePurpose==="OTHER" && !draft.comment?.trim()) errors.push({field:"comment",message:"Explain the OTHER purpose in the comment."});
  for (const definition of context.properties) {
    const value = draft.properties[definition.definitionId];
    const empty = value===undefined || (typeof value === "string" && !value.trim());
    let message="";
    if (empty) { if(definition.required) message=`${definition.label} is required.`; }
    else if (definition.valueType==="BOOLEAN" && typeof value!=="boolean") message="Select true or false.";
    else if (definition.valueType==="CHOICE") message="This legacy dropdown has been replaced. Reopen the booking ticket.";
    else if (definition.valueType==="REFERENCE" && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value))) message="Select a governed catalogue entry.";
    else if (definition.valueType==="INTEGER" && !/^[+-]?\d{1,30}$/.test(String(value))) message="Enter an integer of at most 30 digits.";
    else if (definition.valueType==="DECIMAL" && (!/^[+-]?\d+(?:\.\d+)?$/.test(String(value)) || String(value).split(".")[0].replace(/^[+-]?0*/,"").length>18 || (String(value).split(".")[1]?.replace(/0+$/,"").length ?? 0)>12)) message="Enter a decimal with at most 18 integer and 12 fractional digits.";
    else if (definition.valueType==="DATE") {
      const text=String(value); const parsed=new Date(`${text}T00:00:00Z`);
      if(!/^\d{4}-\d{2}-\d{2}$/.test(text)||Number.isNaN(parsed.getTime())||parsed.toISOString().slice(0,10)!==text)message="Enter a valid YYYY-MM-DD date.";
    } else if (definition.valueType==="TEXT" && String(value).trim().length>2000) message="Use at most 2000 characters.";
    if(message)errors.push({field:`properties.${definition.definitionId}`,message});
  }
  const knownIds = new Set(context.properties.map(property=>property.definitionId));
  for (const id of Object.keys(draft.properties)) if(!knownIds.has(id)) errors.push({field:`properties.${id}`,message:"This property is unavailable. Reopen the ticket."});
  for(const [index,reference] of draft.externalReferences.entries()) if(!reference.referenceValue.trim())errors.push({field:`reference-${index}`,message:"Enter a reference value or remove this row."});
  return errors;
}

/** Identify real value changes, including removed or shifted reference rows. */
export function editedTicketFields(before:EnrichedTicketDraft,next:EnrichedTicketDraft,values:Partial<EnrichedTicketDraft>):string[] {
  const edited:string[]=[];
  for(const key of Object.keys(values) as (keyof EnrichedTicketDraft)[]) {
    if(!["properties","propertyLabels","externalReferences"].includes(key)&&!Object.is(before[key],next[key]))edited.push(key);
  }
  if(values.properties)for(const id of new Set([...Object.keys(before.properties),...Object.keys(next.properties)])) {
    if(before.properties[id]!==next.properties[id])edited.push(`properties.${id}`);
  }
  if(values.externalReferences)for(let i=0;i<Math.max(before.externalReferences.length,next.externalReferences.length);i++) {
    const previous=before.externalReferences[i],current=next.externalReferences[i];
    if(previous?.referenceType!==current?.referenceType||previous?.referenceValue!==current?.referenceValue||previous?.sourceSystemId!==current?.sourceSystemId)edited.push(`reference-${i}`);
  }
  if(edited.includes("tradePurpose"))edited.push("comment");
  return edited;
}

/** Revalidation is deliberately limited to already reported errors on edited fields. */
export function revalidateEditedFields(errors:TicketError[],draft:EnrichedTicketDraft,context:TradeBookingContext,editedFields:string[]):TicketError[] {
  const edited=new Set(editedFields);
  const affected=new Set(errors.filter(error=>edited.has(error.field)).map(error=>error.field));
  if(!affected.size)return errors;
  return [...errors.filter(error=>!affected.has(error.field)),...validateEnrichedTicketDraft(draft,context).filter(error=>affected.has(error.field))];
}

export function buildEnrichedTicketPayload(listing:TicketListing,draft:EnrichedTicketDraft,context:TradeBookingContext):TradeBookingRequest {
  const properties = context.properties.flatMap(definition=> {
    const value=draft.properties[definition.definitionId];
    return value===undefined || (typeof value === "string" && !value.trim()) ? [] : [{definitionId:definition.definitionId,value:typeof value==="string"?value.trim():value}];
  });
  return {...buildTicketPayload(listing,draft),tradePurpose:draft.tradePurpose,marketActivity:draft.marketActivity ?? null,
    executingBrokerOrganisationId:draft.executingBrokerOrganisationId || null,traderPersonId:draft.traderPersonId || null,
    properties,tagIds:draft.tagIds,externalReferences:draft.externalReferences.map(r=>({...r,referenceValue:r.referenceValue.trim(),sourceSystemId:r.sourceSystemId?.trim() || null}))};
}
