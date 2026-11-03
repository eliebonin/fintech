'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import Link from 'next/link';
import type {components,ReferenceNodeOption,Currency,DayCountConvention} from 'api-contracts';
import {bffGet,bffPost,searchReferenceNodesFromBff} from '@/lib/browser-api-client';
import {withProposalRetry,confirmProposalRetry,rejectProposalRetry,type ProposalRetry} from '@/lib/proposal-retry';
import {useRetainedNavigation} from '@/lib/use-retained-navigation';
import {parseBookingDecimal,formatBookingDecimal} from '@/lib/booking-decimal';
import {SwapTermsFacts} from './swap-terms-facts';

type Request=components['schemas']['SwapProposalRequest'];
type Leg=components['schemas']['RateSwapLeg-Input'];
type Prefix='pay'|'receive';
const frequencies=['AT_MATURITY','MONTHLY','QUARTERLY','SEMIANNUAL','ANNUAL','CUSTOM'];
const prefixes:Prefix[]=['pay','receive'];

export function RateSwapCreationForm({tenantId}:{tenantId:string}){
  const retry=useRef<ProposalRetry|null>(null);useRetainedNavigation(retry);
  const originalTenant=useRef(tenantId),flight=useRef(false),sequences=useRef({pay:0,receive:0});
  const [draft,setDraft]=useState<Record<string,string>>({quantityUnit:'NOMINAL',quoteFactor:'1',principalExchange:'UNSPECIFIED'});
  const [currencies,setCurrencies]=useState<Currency[]>([]),[days,setDays]=useState<DayCountConvention[]>([]),[loaded,setLoaded]=useState(false);
  const [selected,setSelected]=useState<Partial<Record<Prefix,ReferenceNodeOption>>>({}),[results,setResults]=useState<Record<Prefix,ReferenceNodeOption[]>>({pay:[],receive:[]});
  const [searching,setSearching]=useState({pay:false,receive:false}),[review,setReview]=useState<Request>(),[saving,setSaving]=useState(false),[error,setError]=useState(''),[proposal,setProposal]=useState('');
  const stale=originalTenant.current!==tenantId;
  useEffect(()=>{
    let current=true;
    Promise.all([bffGet<components['schemas']['CurrencyResponse']>('/api/currencies?groups=REGULAR'),bffGet<components['schemas']['DayCountConventionResponse']>('/api/day-count-conventions')])
      .then(([c,d])=>{if(current){setCurrencies(c.data.flatMap(g=>g.items));setDays(d.data);setLoaded(true);}})
      .catch(e=>{if(current)setError(e instanceof Error?e.message:'Governed catalogues unavailable. Reload this page.');});
    return()=>{current=false;sequences.current.pay++;sequences.current.receive++;};
  },[]);
  const patch=(name:string,value:string)=>{setDraft(d=>({...d,[name]:value}));setError('');};
  async function search(prefix:Prefix){
    const serial=++sequences.current[prefix];setSearching(p=>({...p,[prefix]:true}));setError('');
    try{const found=await searchReferenceNodesFromBff(draft[`${prefix}RateQuery`]??'',{nodeType:'RATE_INDEX',referenceLevel:'ECONOMIC'});
      if(serial===sequences.current[prefix])setResults(r=>({...r,[prefix]:found.data.filter(n=>n.nodeType==='RATE_INDEX'&&n.status==='ACTIVE')}));
    }catch(e){if(serial===sequences.current[prefix])setError(e instanceof Error?e.message:'Rate search failed.');}
    finally{if(serial===sequences.current[prefix])setSearching(p=>({...p,[prefix]:false}));}
  }
  function prepare(event:FormEvent){
    event.preventDefault();if(stale||saving)return;
    try{
      if(!loaded)throw new Error('Load the governed catalogues before review.');
      const required=(name:string)=>{const value=draft[name]?.trim();if(!value)throw new Error(`Complete ${name.replace(/([A-Z])/g,' $1').toLowerCase()}.`);return value;};
      const positive=(name:string)=>{const value=required(name),p=parseBookingDecimal(value);if(!p||p.value<=BigInt(0))throw new Error(`Enter a positive exact decimal for ${name}.`);return value;};
      const currency=(name:string)=>{const value=required(name);if(!currencies.some(c=>c.currencyId===value))throw new Error('Choose a governed currency.');return value;};
      const legs:Leg[]=prefixes.map(prefix=>{
        const rate=selected[prefix];if(!rate)throw new Error(`Select the ${prefix} rate reference.`);
        const bp=parseBookingDecimal(required(`${prefix}SpreadBp`));if(!bp||bp.scale>4)throw new Error('Use a spread in basis points with up to four decimal places.');
        const day=required(`${prefix}DayCountConventionId`);if(!days.some(d=>d.dayCountConventionId===day))throw new Error('Choose a governed day count for each leg.');
        const reset=required(`${prefix}ResetFrequency`) as Leg['resetFrequency'],payment=required(`${prefix}PaymentFrequency`) as Leg['paymentFrequency'];
        return {direction:prefix==='pay'?'PAY':'RECEIVE',rateReferenceId:rate.referenceNodeId,currencyId:currency(`${prefix}CurrencyId`),contractualNotional:positive(`${prefix}Notional`),
          spread:formatBookingDecimal(bp.value,bp.scale+4),dayCountConventionId:day,interestCalculationMethod:required(`${prefix}InterestCalculationMethod`),observationDescription:required(`${prefix}ObservationDescription`),
          resetFrequency:reset,paymentFrequency:payment,...(reset==='CUSTOM'?{resetScheduleDescription:required(`${prefix}ResetScheduleDescription`)}:{}),...(payment==='CUSTOM'?{paymentScheduleDescription:required(`${prefix}PaymentScheduleDescription`)}:{})};
      });
      const effective=required('effectiveDate'),maturity=required('maturityDate');if(effective>=maturity)throw new Error('Maturity must follow the effective date.');
      const principal=required('principalExchange') as components['schemas']['RateSwapTerms-Input']['principalExchange'];
      const description=principal==='CUSTOM'||principal==='UNSPECIFIED'?required('principalExchangeDescription'):draft.principalExchangeDescription?.trim()||undefined;
      const basis=currency('notionalCurrencyId'),identifier=draft.tenantIdentifier?.trim()||null;
      setReview({canonicalName:required('canonicalName'),tenantIdentifier:identifier,terms:{schemaVersion:1,swapKind:'RATE_EXCHANGE',tenantIdentifier:identifier,
        contractualNotional:positive('contractualNotional'),notionalCurrencyId:basis,quantityUnit:draft.quantityUnit==='UNITS'?'UNITS':'NOMINAL',
        ...(draft.quantityUnit==='UNITS'?{contractualUnits:positive('contractualUnits'),notionalPerUnit:positive('notionalPerUnit')}:{}),
        quoteCurrencyId:basis,quoteFactor:positive('quoteFactor'),effectiveDate:effective,maturityDate:maturity,sourceReference:required('sourceReference'),
        principalExchange:principal,principalExchangeDescription:description,legs}});setError('');
    }catch(e){setError(e instanceof Error?e.message:'Check the contract fields.');}
  }
  async function submit(){
    if(!review||flight.current||stale)return;flight.current=true;setSaving(true);setError('');
    try{const response=await bffPost<components['schemas']['ReferenceDataProposalResponse']>('/api/instruments/swaps',withProposalRetry(review,retry),undefined,fetch,{'X-Expected-Tenant-Id':originalTenant.current});setProposal(confirmProposalRetry(retry,response));}
    catch(e){rejectProposalRetry(retry,e);setError(e instanceof Error?e.message:'Swap submission failed.');}
    finally{flight.current=false;setSaving(false);}
  }
  const labels=Object.fromEntries([...currencies.map(c=>[c.currencyId,c.currencyCode]),...days.map(d=>[d.dayCountConventionId,d.displayName]),...prefixes.flatMap(p=>selected[p]?[[selected[p]!.referenceNodeId,selected[p]!.canonicalName]]:[])]);
  const input=(name:string,label:string,type='text',required=true)=><label>{label}<input name={name} type={type} required={required} maxLength={250} value={draft[name]??''} onChange={e=>patch(name,e.target.value)}/></label>;
  const text=(name:string,label:string,required=true)=><label>{label}<textarea name={name} required={required} maxLength={name==='sourceReference'||name.endsWith('InterestCalculationMethod')?1000:2000} value={draft[name]??''} onChange={e=>patch(name,e.target.value)}/></label>;
  const select=(name:string,label:string,options:[string,string][])=> <label>{label}<select name={name} required value={draft[name]??''} onChange={e=>patch(name,e.target.value)}><option value="">Select {label.toLowerCase()}</option>{options.map(([id,title])=><option key={id} value={id}>{title}</option>)}</select></label>;
  if(stale)return <p role="alert">The active tenant changed. Reopen swap creation in the current tenant.</p>;
  if(proposal)return <section className="detail-card"><h2>Swap request pending approval</h2><p>The two-leg contract is awaiting Operations approval. No trade has been booked.</p><Link href="/instruments/requests">Open instrument requests</Link> · <Link href="/operations">Review in Operations</Link></section>;
  return <>{error?<p role="alert" className="strategy-error">{error}</p>:null}{review?<><h2>Review rate-exchange contract</h2><p>{review.canonicalName}</p><SwapTermsFacts terms={review.terms} labels={labels}/><div className="ticket-actions"><button disabled={saving} onClick={submit}>{saving?'Submitting…':retry.current?'Retry unchanged submission':'Submit swap for approval'}</button><button disabled={saving||!!retry.current} onClick={()=>setReview(undefined)}>Edit terms</button></div></>:<form onSubmit={prepare} className="strategy-form">
    <fieldset disabled={!loaded||saving}><legend>1. Contract and booking basis</legend>{input('canonicalName','Display name')}{input('tenantIdentifier','Tenant identifier','text',false)}
      {select('quantityUnit','Booking quantity',[['NOMINAL','Notional amount'],['UNITS','Units']])}{input('contractualNotional','Contractual reference notional')}{select('notionalCurrencyId','Booking and quote currency',currencies.map(c=>[c.currencyId,c.currencyCode]))}
      {draft.quantityUnit==='UNITS'?<>{input('contractualUnits','Contractual units')}{input('notionalPerUnit','Reference notional per unit')}</>:null}{input('effectiveDate','Effective date','date')}{input('maturityDate','Maturity date','date')}{input('quoteFactor','Whole-swap quote divisor')}
      <p>Each contract keeps its own bank price series. The booking basis scales its two leg notionals; the whole-swap mark already includes both legs.</p></fieldset>
    {prefixes.map(prefix=><fieldset className="ticket-section" disabled={!loaded||saving} key={prefix}><legend>{prefix==='pay'?'2. Pay leg':'3. Receive leg'}</legend>
      <label>Search {prefix} rate<input name={`${prefix}RateQuery`} maxLength={250} value={draft[`${prefix}RateQuery`]??''} onChange={e=>{sequences.current[prefix]++;patch(`${prefix}RateQuery`,e.target.value);setSelected(s=>({...s,[prefix]:undefined}));setResults(r=>({...r,[prefix]:[]}));setSearching(s=>({...s,[prefix]:false}));}}/></label>
      <button type="button" disabled={searching[prefix]||!draft[`${prefix}RateQuery`]?.trim()} onClick={()=>search(prefix)}>Search {prefix} rate</button>
      {selected[prefix]?<p>Selected: {selected[prefix]!.canonicalName}</p>:null}<ul className="ticket-options">{results[prefix].map(node=><li key={node.referenceNodeId}><button type="button" onClick={()=>{setSelected(s=>({...s,[prefix]:node}));setResults(r=>({...r,[prefix]:[]}));}}>{node.canonicalName}</button></li>)}</ul>
      {input(`${prefix}Notional`,'Contractual leg notional')}{select(`${prefix}CurrencyId`,'Leg currency',currencies.map(c=>[c.currencyId,c.currencyCode]))}{input(`${prefix}SpreadBp`,'Spread over rate (bps; explicit zero allowed)')}
      {select(`${prefix}DayCountConventionId`,'Day-count convention',days.map(d=>[d.dayCountConventionId,d.displayName]))}
      {select(`${prefix}ResetFrequency`,'Reset frequency',frequencies.map(f=>[f,f.replaceAll('_',' ')]))}{select(`${prefix}PaymentFrequency`,'Payment frequency',frequencies.map(f=>[f,f.replaceAll('_',' ')]))}
      {text(`${prefix}InterestCalculationMethod`,'Interest calculation method')}{text(`${prefix}ObservationDescription`,'Observation conventions / source evidence')}
      {draft[`${prefix}ResetFrequency`]==='CUSTOM'?text(`${prefix}ResetScheduleDescription`,'Custom reset schedule evidence'):null}{draft[`${prefix}PaymentFrequency`]==='CUSTOM'?text(`${prefix}PaymentScheduleDescription`,'Custom payment schedule evidence'):null}
    </fieldset>)}
    <fieldset disabled={!loaded||saving}><legend>4. Principal and evidence</legend>{select('principalExchange','Principal exchange',[['NONE','None'],['INITIAL_FINAL','Initial and final'],['FINAL','Final only'],['CUSTOM','Custom'],['UNSPECIFIED','Not established from evidence']])}
      {text('principalExchangeDescription','Principal exchange evidence / limitations',['CUSTOM','UNSPECIFIED'].includes(draft.principalExchange))}{text('sourceReference','Source / confirmation evidence')}
      <p>These are contractual facts for review. Approval does not generate interest, principal exchanges or payments.</p></fieldset>
    <div className="ticket-actions"><button disabled={!loaded||saving}>Review swap</button><Link href="/instruments/create">Cancel</Link></div>
  </form>}</>;
}
