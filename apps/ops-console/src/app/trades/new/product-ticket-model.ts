import {recognitionPayload} from '@/lib/valuation-recognition';
import type {components} from 'api-contracts';
import type {TradeBookingContext} from '@/lib/browser-api-client';
import {validateTradeAnnotations,type EnrichedTicketDraft,type TicketError} from './ticket-model';
import {parseBookingDecimal as part, exactBookingAmount, formatBookingDecimal, type BookingDecimal as DecimalPart} from '@/lib/booking-decimal';
export type ProductTerms=components['schemas']['ProductBookingContextView'];
export type ProductRequest=components['schemas']['ProductBookingRequest'];
export type ProductDraft=EnrichedTicketDraft&{positionEffect:'OPEN'|'CLOSE';priceType?:'CLEAN'|'DIRTY'|'';accruedInterestAmount?:string;settlementEvidence?:string};
export function createProductDraft():ProductDraft {
  return {strategyId:'',side:'BUY',positionEffect:'OPEN',quantity:'',executionPrice:'',tradeDatetime:new Date().toISOString(),settlementDate:'',tradePurpose:'INVESTMENT',properties:{},tagIds:[],externalReferences:[]};
}
/** Exact preview in supported database precision; never use binary floats for money. */
export function productAmount(terms:ProductTerms,quantity:string,price:string):string {
  const c=terms.convention;if(!c)return '—';
  return exactBookingAmount([quantity,price,String(c.kind==='FUTURE'?c.monetaryMultiplier:c.priceBasis==='PCT_OF_PAR'&&c.quantityUnit==='UNITS'?c.denomination??'': '1')],String(c.quoteFactor));
}
function aligned(value:string,step:string,minimum='0') {
  const parts=[value,step,minimum].map(text=>part(text));if(parts.some(v=>!v))return false;
  const [v,s,m]=parts as DecimalPart[],scale=Math.max(v.scale,s.scale,m.scale);
  const integer=(p:DecimalPart)=>p.value*BigInt(10)**BigInt(scale-p.scale);
  return integer(s)>0&&integer(v)>=integer(m)&&(integer(v)-integer(m))%integer(s)===BigInt(0);
}
/** Accrual is a signed total in trade currency; DIRTY quotes already include it. */
export function bondAmounts(terms:ProductTerms,draft:ProductDraft):{clean:string;dirty:string}|null {
  const quoted=part(productAmount(terms,draft.quantity,draft.executionPrice)),accrued=part(draft.accruedInterestAmount??'');
  if(!quoted||!accrued||!['CLEAN','DIRTY'].includes(draft.priceType??''))return null;
  const scaled=(p:DecimalPart)=>p.value*BigInt(10)**BigInt(12-p.scale);
  const q=scaled(quoted),a=scaled(accrued),clean=draft.priceType==='CLEAN'?q:q-a,dirty=draft.priceType==='DIRTY'?q:q+a;
  if(clean<0||dirty<0||clean>=BigInt(10)**BigInt(30)||dirty>=BigInt(10)**BigInt(30))return null;
  const text=(n:bigint)=>formatBookingDecimal(n,12);
  return {clean:text(clean),dirty:text(dirty)};
}
export function validateProductDraft(terms:ProductTerms,draft:ProductDraft,context:TradeBookingContext):TicketError[] {
  const errors=validateTradeAnnotations(draft,context),c=terms.convention;
  if(!terms.bookingEligible||!terms.termsFingerprint||!c)errors.push({field:'instrumentId',message:terms.ineligibilityMessage??'Select approved booking terms.'});
  if(!draft.strategyId)errors.push({field:'strategyId',message:'Select a strategy.'});
  const qty=part(draft.quantity),price=part(draft.executionPrice);
  if(!qty||qty.value<=0||!c||(c.kind==='FUTURE'?!/^\d{1,18}$/.test(draft.quantity):!aligned(draft.quantity,String(c.quantityIncrement),String(c.quantityMinimum))))errors.push({field:'quantity',message:'Enter a positive quantity matching the approved minimum and increment.'});
  if(!price||productAmount(terms,draft.quantity,draft.executionPrice)==='—'||(price.value<0&&c?.kind!=='SWAP'&&(c?.kind!=='FUTURE'||!c.allowNegativePrice)))errors.push({field:'executionPrice',message:'Enter an exact supported price under the approved convention.'});
  if(c?.kind==='FUTURE'&&price){const positive=draft.executionPrice.replace(/^-/, '');if(!aligned(positive,String(c.tickSize)))errors.push({field:'executionPrice',message:'Single-fill price must match the approved tick increment.'});}
  const time=new Date(draft.tradeDatetime),validTime=/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(draft.tradeDatetime)&&!Number.isNaN(time.getTime());
  if(!validTime||(c?.kind==='FUTURE'&&time>new Date(c.lastTradingAtUtc)))errors.push({field:'tradeDatetime',message:'Enter an execution timestamp with timezone within the contract trading period.'});
  if(c?.kind==='FUTURE'&&!['OPEN','CLOSE'].includes(draft.positionEffect))errors.push({field:'positionEffect',message:'Select OPEN or CLOSE execution intent.'});
  if(c?.kind==='SWAP'&&!draft.counterpartyOrganisationId)errors.push({field:'counterpartyOrganisationId',message:'Select the OTC swap counterparty.'});
  if(c?.kind==='SWAP'&&validTime&&(!terms.swapDetails||time.toISOString().slice(0,10)<terms.swapDetails.effectiveDate||!terms.maturityDate||time.toISOString().slice(0,10)>=terms.maturityDate))errors.push({field:'tradeDatetime',message:'Execution must be within the swap effective and maturity dates. Reselect terms if the date changed.'});
  if(c?.kind==='STRUCTURED_PRODUCT'||c?.kind==='BOND'){
    const date=new Date(`${draft.settlementDate}T00:00:00Z`);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(draft.settlementDate)||Number.isNaN(date.getTime())||date.toISOString().slice(0,10)!==draft.settlementDate||(validTime&&draft.settlementDate<time.toISOString().slice(0,10)))errors.push({field:'settlementDate',message:'Enter the actual security settlement date on or after execution.'});
    if(terms.executionRoute==='OTC'&&!draft.counterpartyOrganisationId)errors.push({field:'counterpartyOrganisationId',message:'Select the OTC execution counterparty.'});
  }
  if(c?.kind==='BOND'){
    if(!bondAmounts(terms,draft)||(terms.couponType==='ZERO'&&part(draft.accruedInterestAmount??'')?.value!==BigInt(0)))errors.push({field:'accruedInterestAmount',message:'Confirm CLEAN/DIRTY and total signed accrued interest; zero-coupon bonds require zero.'});
    if(!draft.settlementEvidence?.trim())errors.push({field:'settlementEvidence',message:'Record the source confirming accrued interest and actual settlement eligibility.'});
    if(!terms.maturityDate||draft.settlementDate>=terms.maturityDate)errors.push({field:'settlementDate',message:'Settlement must precede bond maturity.'});
  }
  return errors;
}
export function buildProductPayload(terms:ProductTerms,draft:ProductDraft):ProductRequest {
  return {...recognitionPayload(draft),...(terms.kind==='BOND'?{priceType:draft.priceType as 'CLEAN'|'DIRTY',accruedInterestAmount:draft.accruedInterestAmount,settlementEvidence:draft.settlementEvidence?.trim()}:{}),instrumentId:terms.instrumentId,listingId:terms.listingId??null,executionRoute:terms.executionRoute,
    expectedTermsFingerprint:terms.termsFingerprint??'',strategyId:draft.strategyId,side:draft.side,quantity:draft.quantity,
    executionPrice:draft.executionPrice,tradeDatetime:draft.tradeDatetime,settlementDate:terms.kind==='FUTURE'||terms.kind==='SWAP'?null:draft.settlementDate,
    positionEffect:terms.kind==='FUTURE'?draft.positionEffect:null,tradePurpose:draft.tradePurpose,marketActivity:draft.marketActivity||null,
    counterpartyOrganisationId:draft.counterpartyOrganisationId||null,executingBrokerOrganisationId:draft.executingBrokerOrganisationId||null,
    traderPersonId:draft.traderPersonId||null,comment:draft.comment?.trim()||null,tagIds:draft.tagIds,
    properties:Object.entries(draft.properties).flatMap(([definitionId,value])=>value===undefined||(typeof value==='string'&&!value.trim())?[]:[{definitionId,value:typeof value==='string'?value.trim():value}]),
    externalReferences:draft.externalReferences.map(r=>({...r,referenceValue:r.referenceValue.trim(),sourceSystemId:r.sourceSystemId?.trim()||null}))};
}
