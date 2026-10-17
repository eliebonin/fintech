import Link from 'next/link';
import type {Fact, TermsSchedule} from '@/lib/instrument-terms-schedule';

const referenceFields = new Set(['underlying_reference_node_id','component_reference_node_id','target_reference_node_id','reference_node_id']);
const hidden = (key:string) => (key.endsWith('_id') && !referenceFields.has(key)) || key.endsWith('Id') || ['created_at_utc','recorded_at_utc','source_payload_id','source_system_id','underlyings','calls','terminalBranches','earlyRedemptions','canonicalName','internalCode'].includes(key);
const fieldLabels:Record<string,string>={underlying_reference_node_id:'Underlying',component_reference_node_id:'Component',target_reference_node_id:'Target',reference_node_id:'Reference',trigger_level:'Trigger (% of initial)',redemption_rate:'Redemption (% of payoff base)',payout_rate:'Payout rate (%)',payment_rate:'Payment rate (%)'};
const label = (key:string) => fieldLabels[key]??key.replace(/([a-z])([A-Z])/g,'$1 $2').replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
const operators:Record<string,string>={GE:'≥',GT:'>',LE:'≤',LT:'<'};
const titles:Record<string,string> = {scheduleEvents:'Observation / reset / payment dates',initialFixings:'Underlyings & initial fixings',conditions:'Contractual conditions',barriers:'Barrier predicates',actions:'Conditional outcomes',componentTerms:'Component payouts',optionTerms:'Option components & strikes',composition:'Payoff components',couponProgrammes:'Coupon terms',couponPeriods:'Coupon schedule',shareCalls:'Autocall schedule',terminalBranches:'Final redemption branches',swapTerms:'Swap terms',swapLegs:'Swap legs',rangeAccrual:'Range accrual terms',supertracker:'Supertracker terms'};

function text(value:unknown,labels:Record<string,string>):string {
  if(value===null || value===undefined)return 'Not recorded';
  if(typeof value==='boolean')return value?'Yes':'No';
  if(Array.isArray(value))return value.map(v=>text(v,labels)).join('; ');
  if(typeof value==='object')return Object.entries(value as Fact).filter(([k])=>!hidden(k)).map(([k,v])=>`${label(k)}: ${text(v,labels)}`).join('; ');
  return labels[String(value)]??operators[String(value)]??String(value);
}

function FactsTable({rows,labels}:{rows:Fact[];labels:Record<string,string>}) {
  const columns=[...new Set(rows.flatMap(row=>Object.keys(row)))].filter(key=>!hidden(key)&&rows.some(row=>row[key]!=null));
  if(!rows.length || !columns.length)return null;
  return <div style={{overflowX:'auto'}}><table style={{borderCollapse:'collapse',width:'100%'}}><thead><tr>{columns.map(key=><th key={key} style={{textAlign:'left',padding:8,borderBottom:'1px solid #ccd4df'}}>{label(key)}</th>)}</tr></thead><tbody>{rows.map((row,index)=><tr key={index}>{columns.map(key=><td key={key} style={{padding:8,borderBottom:'1px solid #e4e8ef',verticalAlign:'top'}}>{row[key]==null&&key==='lower_bound'?'No lower bound':row[key]==null&&key==='upper_bound'?'No upper bound':text(row[key],labels)}</td>)}</tr>)}</tbody></table></div>;
}

function Values({values,labels}:{values:Fact;labels:Record<string,string>}) {
  return <dl style={{display:'grid',gridTemplateColumns:'minmax(160px,1fr) 3fr',gap:8}}>{Object.entries(values).filter(([k,v])=>!hidden(k)&&v!=null).map(([k,v])=><div key={k} style={{display:'contents'}}><dt>{label(k)}</dt><dd style={{margin:0,overflowWrap:'anywhere'}}>{text(v,labels)}</dd></div>)}</dl>;
}

export function InstrumentTermsSchedule({data}:{data:TermsSchedule}) {
  const labels=data.referenceLabels;
  return <main style={{maxWidth:1280,margin:'auto',padding:24}}>
    <Link href={`/instruments/${data.instrumentId}`}>← Instrument details</Link>
    <h1>Terms &amp; Schedule</h1>
    <p>Read-only current approved contractual terms. Dates and conditional payouts are recorded obligations; this view does not evaluate triggers or show paid cashflows.</p>
    {data.layers.map(layer=>{
      const events=layer.facts.scheduleEvents??[];
      const eventById=new Map(events.map(e=>[String(e.schedule_event_id),e]));
      const groups=new Map((layer.facts.conditions??[]).map(g=>[String(g.condition_group_id),g]));
      const outcomes=(layer.facts.actions??[]).map(action=>{
        const group=groups.get(String(action.condition_group_id));
        const event=eventById.get(String(group?.schedule_event_id));
        const component=(layer.facts.componentTerms??[]).find(c=>c.instrument_composition_id===action.target_composition_id);
        const predicates=(layer.facts.barriers??[]).filter(b=>b.condition_group_id===action.condition_group_id).map(b=>`${text(b.underlying_reference_node_id,labels)} ${b.comparison_operator} ${text(b.lower_level_value,labels)}${b.upper_level_value!=null?` to ${text(b.upper_level_value,labels)}`:''} (${text(b.level_reference_type,labels)})`).join('; ');
        return {observation_date:event?.event_date,condition:group?.group_code,aggregation:group?.underlying_aggregation,logical_operator:group?.logical_operator,predicates,
          action:action.action_type,target:labels[String(action.target_reference_node_id)]??'Not recorded',
          payment_date:action.payment_date??event?.payment_date,payout_rate:action.payment_rate??component?.payout_rate,
          payout_amount:action.payment_amount??component?.payout_amount,payout_basis:action.payment_basis??component?.payout_basis,
          multiplicity:action.payout_multiplicity,execution_sequence:action.execution_sequence};
      }).sort((a,b)=>String(a.observation_date??'').localeCompare(String(b.observation_date??''))||Number(a.execution_sequence)-Number(b.execution_sequence));
      const enriched=(key:string,rows:Fact[])=>rows.map(row=>{
        const group=key==='conditions'?row:groups.get(String(row.condition_group_id));
        const event=eventById.get(String(group?.schedule_event_id??row.observation_event_id));
        return {...(event?{observation_date:event.event_date}:{}),...(group&&key!=='conditions'?{condition:group.group_code}:{}),...row};
      });
      return <section key={layer.instrumentId} style={{background:'white',border:'1px solid #dde3ed',borderRadius:10,padding:20,marginTop:24}}>
        <p>{layer.relation} · {layer.instrumentType} · Approved definition v{layer.version}</p>
        <h2><Link href={`/instruments/${layer.instrumentId}`}>{layer.canonicalName}</Link></h2>
        <Values values={{issuer:layer.issuer,currency:layer.currency,...layer.dates}} labels={labels}/>
        <details open><summary>Contractual terms</summary><Values values={Object.fromEntries(Object.entries(layer.economics).filter(([key])=>!['issueDate','initialValuationDate','finalValuationDate','maturityDate','effectiveFrom','is_current','version_no'].includes(key)))} labels={labels}/></details>
        {outcomes.length?<section><h3>Schedule &amp; conditional outcomes</h3><FactsTable rows={outcomes} labels={labels}/></section>:null}
        {layer.instrumentType==='SWAP'&&!events.length?<p>No explicit reset or payment dates recorded. Any recorded frequencies or source descriptions appear above; the referenced product schedule below belongs to that product.</p>:null}
        {Array.isArray(layer.economics.earlyRedemptions)&&layer.economics.earlyRedemptions.length?<section><h3>Note early redemption dates</h3><FactsTable rows={layer.economics.earlyRedemptions as Fact[]} labels={labels}/></section>:null}
        {Object.entries(titles).map(([key,title])=>{
          const rows=layer.facts[key]??[];
          return rows.length?<section key={key}><h3>{title}</h3><FactsTable rows={enriched(key,rows)} labels={labels}/></section>:null;
        })}
        {layer.instrumentType==='STRUCTURED_PRODUCT'&&!events.length&&!(layer.facts.shareCalls??[]).length?<p>The note’s schedule is recorded in its dates and early redemption terms. See the linked layer below for underlying payoff observations.</p>:null}
      </section>;
    })}
  </main>;
}
