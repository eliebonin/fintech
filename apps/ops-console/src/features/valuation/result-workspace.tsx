'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {formatTradeExactDecimal} from '@/lib/trades';
import {useEffect,useId,useRef,useState,type ReactNode} from 'react';
import {ValuationPriceEvidence} from '@/components/valuation-price-evidence';
import {InputEvidence} from './input-evidence';
import {componentLabel,displayAmount} from './presentation';
import type {Batch,Item,SourceCoverageRow} from './types';
import {positionLabel,positionInstrumentType,positionContext,positionAttention,selectPositionRows} from './ops-review-model';
import {ReviewSummary} from './review-summary';
import {MissingPricePositions} from './missing-price-positions';
import {instrumentDisplayHref} from '@/lib/instrument-display';
import {InstrumentLabel} from '@/components/instrument-label';
import {TechnicalReference} from './technical-reference';
import {PositionFacts} from './position-facts';
import {PositionCalculation} from './position-calculation';
import {AccruedBalanceInspection} from './accrued-balance-inspection';
import {PnlSourceCoverage} from './source-coverage';
import {CashFxReport} from './cash-fx-report';
import {ReportTabs,ReportPanel} from './report-tabs';
import {reportViews,type ReportView} from './report-navigation';

function Amount({value}:{value:string|undefined}){return <span className={`pnl-amount ${value?.startsWith('-')?'pnl-negative':'pnl-positive'}`} title={value}>{displayAmount(value)}</span>;}

type ShareAdjustment={quantity_before:string;quantity_after:string;event:{effective_date:string;ratio:string;review_id:string}};
/** Exact quantities returned by the server; no browser-side action calculation. */
function ShareAdjustments({evidence}:{evidence:unknown}){
 if(!evidence||typeof evidence!=='object')return null;
 const raw=(evidence as {splitAdjustments?:unknown}).splitAdjustments;
 if(!Array.isArray(raw))return null;
 const rows=raw.filter((row):row is ShareAdjustment=>Boolean(row&&typeof row==='object'&&
  typeof row.quantity_before==='string'&&typeof row.quantity_after==='string'&&row.event&&
  typeof row.event.effective_date==='string'&&typeof row.event.ratio==='string'&&typeof row.event.review_id==='string'));
 if(!rows.length)return null;
 return <details><summary>Share quantity adjustments · {rows.length}</summary>
  <p>Reviewed basic share ratios only. Booked trades stay unchanged; no loyalty or fractional cash entitlement is inferred.</p>
  <dl>{rows.map((row,index)=><div key={`${row.event.review_id}-${index}`}><dt>{row.event.effective_date} · ratio {row.event.ratio}</dt>
   <dd>{`${formatTradeExactDecimal(row.quantity_before)} → ${formatTradeExactDecimal(row.quantity_after)}`}</dd><dd><TechnicalReference id={row.event.review_id} label="Review evidence ID"/></dd></div>)}</dl>
 </details>;
}

/** Selection and formatting only. No allocation, invented marks or client P&L. */
export function ResultWorkspace({batch,currency,onLabels,activeTab,onNavigate,reviewContent,logsContent}:{batch:Batch;currency:string;activeTab:ReportView;onNavigate:(view:ReportView)=>void;onLabels?:(labels:Record<string,string>)=>void;reviewContent?:ReactNode;logsContent?:ReactNode}){
 const [selected,setSelected]=useState<string|null>(null),[page,setPage]=useState(0);
 const [pageSize,setPageSize]=useState<'25'|'50'|'100'|'all'>('25');
 const [names,setNames]=useState<Record<string,string>>({});
 const [query,setQuery]=useState(''),[attentionOnly,setAttentionOnly]=useState(false),[sort,setSort]=useState('name');
 const [instrumentType,setInstrumentType]=useState('');
 const [source,setSource]=useState<SourceCoverageRow|null>(null);
 const [inspectorOpen,setInspectorOpen]=useState(false);
 const inspectorId=useId();
 const inspectorHeading=useRef<HTMLHeadingElement>(null);
 const inspectorTrigger=useRef<HTMLButtonElement|null>(null);
 const positionHeading=useRef<HTMLHeadingElement>(null);
 const cashHeading=useRef<HTMLHeadingElement>(null);
 const denied=batch.summary.evidenceAccess==='DENIED';
 const metadata=batch.presentation??{references:names,currencies:{},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0};
 const positions=batch.items.filter(item=>!item.cash_account_id);
 const instrumentTypes=[...new Map(positions.map(item=>{const type=positionInstrumentType(item,metadata);return [type.code,type] as const;})).values()].sort((a,b)=>a.label.localeCompare(b.label));
 const filtered=selectPositionRows(positions,metadata,{query,attentionOnly,sort,instrumentType,componentCodes:source?.componentCodes});
 const pageLength=pageSize==='all'?Math.max(1,filtered.length):Number(pageSize);
 const pageCount=Math.max(1,Math.ceil(filtered.length/pageLength));
 const currentPage=Math.min(page,pageCount-1);
 const rows=filtered.slice(currentPage*pageLength,(currentPage+1)*pageLength);
 useEffect(()=>{if(!denied&&batch.presentation)onLabels?.(batch.presentation.references);},[batch.presentation,denied,onLabels]);
 useEffect(()=>{
  if(denied||batch.presentation)return;
  const controller=new AbortController();
  // Keep the existing 20-ID authorized lookup bound even when displaying all rows.
  const ids=[...new Set(rows.map(r=>r.subject_id).filter((id):id is string=>Boolean(id)))].filter(id=>!Object.hasOwn(names,id));
  if(ids.length)void (async()=>{
   const labels:Record<string,string>={};
   for(let offset=0;offset<ids.length;offset+=20){
    const response=await fetch(`/api/market-data/references?ids=${encodeURIComponent(ids.slice(offset,offset+20).join(','))}`,{cache:'no-store',signal:controller.signal});
    if(!response.ok)continue;
    const body=await response.json() as {labels:Record<string,string>};Object.assign(labels,body.labels);
   }
   if(!controller.signal.aborted){setNames(current=>({...current,...labels}));onLabels?.(labels);}
  })().catch(()=>{/* Labels are optional; retained IDs remain available. */});
  return()=>controller.abort();
 },[batch.batch_id,batch.presentation,currentPage,pageSize,query,attentionOnly,sort,instrumentType,source?.code,denied,onLabels]);
 const item=rows.find(r=>r.attribution_id===selected)??rows[0];
 const label=(r:Item)=>positionLabel(r,metadata);
 function resetPage(){setPage(0);setSelected(null);}
 function closeInspector(){
  setInspectorOpen(false);
  (inspectorTrigger.current?.isConnected?inspectorTrigger.current:positionHeading.current)?.focus();
 }
 function inspectPosition(row:Item,trigger:HTMLButtonElement){
  inspectorTrigger.current=trigger;setSelected(row.attribution_id);setInspectorOpen(true);
  requestAnimationFrame(()=>inspectorHeading.current?.focus());
 }
 if(denied)return <><ReportTabs active={activeTab} onNavigate={onNavigate}/>{reportViews.map(view=><ReportPanel key={view} view={view} active={activeTab}>{view==='logs'?logsContent:<div role="status" className="pnl-notice">{batch.summary.reason??'Current dataset DISPLAY rights are required.'} The financial result is retained; review and publication are unavailable while its inputs are restricted.</div>}</ReportPanel>)}</>;
 return <>
  <ReviewSummary batch={batch} currency={currency} onInspectCoverage={scope=>{
   setSource(null);
   if(scope==='positions'){setQuery('');setInstrumentType('');setAttentionOnly(true);resetPage();setInspectorOpen(false);}
   onNavigate('positions');requestAnimationFrame(()=>(scope==='cash'?cashHeading:positionHeading).current?.focus());
  }}/>
  <ReportTabs active={activeTab} onNavigate={onNavigate} pendingAmendments={batch.presentation?.pendingAmendments}/>
  <ReportPanel view="breakdown" active={activeTab}>
  <h3>Breakdown</h3>
  <PnlSourceCoverage batch={batch} currency={currency} onInspect={row=>{setSource(row);setQuery('');setInstrumentType('');setAttentionOnly(false);resetPage();onNavigate('positions');requestAnimationFrame(()=>(row.cashAccountCount&&!row.positionCount?cashHeading:positionHeading).current?.focus());}}/>
  <details className="pnl-bridge"><summary>Valuation bridge & scope</summary><dl>{[['Opening securities value',batch.summary.openingValue],['Closing securities value',batch.summary.closingValue],['Signed period execution value',batch.summary.executionValue],['Storage rounding adjustment',batch.summary.marketRoundingAdjustment??'0'],['External comparison',batch.summary.externalComparison]].map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl><p>Reporting currency: {currency}. Scope: {batch.summary.scope}.</p><ul>{batch.summary.limitations?.map(item=><li key={item}>{item.replaceAll('_',' ').toLowerCase()}</li>)}</ul></details>
  </ReportPanel>
  <ReportPanel view="positions" active={activeTab}>
  <h3>Positions &amp; cash</h3>
  <MissingPricePositions batch={batch}/>
  {source?<p className="pnl-source-filter" role="status">Contributing source: <strong>{source.label}</strong>. Rows retain their full attribution P&amp;L, not just this source. <button type="button" onClick={()=>{setSource(null);resetPage();positionHeading.current?.focus();}}>Show all sources</button></p>:null}
  <CashFxReport batch={batch} currency={currency} metadata={metadata} componentCodes={source?.componentCodes} headingRef={cashHeading}/>
  <div className={`pnl-result-grid ${inspectorOpen&&item?'':'pnl-inspector-closed'}`}>
   <section className="pnl-surface" aria-label="Position attribution">
    <div className="pnl-panel-heading"><h3 ref={positionHeading} tabIndex={-1}>Position attribution</h3><span>{positions.length} {batch.summary.resultFormat==='TRADE_V1'?'historical trade attributions':'positions'} · amounts in {currency}</span></div>
    <div className="pnl-position-filters"><label>Search positions<input type="search" value={query} onChange={e=>{setQuery(e.target.value);resetPage();}}/></label><label>Instrument type<select value={instrumentType} onChange={e=>{setInstrumentType(e.target.value);resetPage();}}><option value="">All instrument types</option>{instrumentTypes.map(type=><option key={type.code} value={type.code}>{type.label}</option>)}</select></label><label>Sort positions<select value={sort} onChange={e=>{setSort(e.target.value);resetPage();}}><option value="name">Instrument name</option><option value="pnl-desc">Total P&amp;L · highest first</option></select></label><label><input type="checkbox" checked={attentionOnly} onChange={e=>{setAttentionOnly(e.target.checked);resetPage();}}/> Attention only</label></div>
    <p className="pnl-muted">{filtered.length} matching of {positions.length}. Headline amounts cover the whole result, not the filtered rows. {batch.summary.cashCoverage?'These search controls filter investment positions only.':''}</p>
    {positions.length===0?<p className="pnl-empty">{batch.summary.requiredInputsComplete===false?'No investment position has a complete set of required prices. See the unpriced positions above; no zero P&L is inferred.':batch.summary.cashCoverage?'No investment positions or period movements. Cash attribution and coverage are reported separately above.':'No relevant positions or period movements. This is a calculated, evidenced zero result.'}</p>:<>
     <div className="pnl-table-scroll"><table className="pnl-table pnl-ops-table"><caption>Position attribution</caption><thead><tr><th scope="col">Instrument / position</th><th scope="col" className="pnl-instrument-type">Instrument type</th><th scope="col">Price/FX P&amp;L</th><th scope="col">Interest earned</th><th scope="col">Other components</th><th scope="col">Total P&amp;L</th><th scope="col">Attention</th><th scope="col">Inspect</th></tr></thead>
      <tbody>{rows.map(r=><tr key={r.attribution_id} className={inspectorOpen&&r.attribution_id===item?.attribution_id?'pnl-selected':''}><th scope="row">{r.subject_id?<InstrumentLabel display={metadata.instrumentDisplays?.[r.subject_id]} fallbackName={label(r)} href={instrumentDisplayHref(metadata.instrumentDisplays?.[r.subject_id],r.subject_id)}/>:label(r)}</th><td className="pnl-instrument-type">{positionInstrumentType(r,metadata).label}</td><td><Amount value={r.market_pnl}/></td><td><Amount value={r.display?.interest??undefined}/></td><td><Amount value={r.display?.other??undefined}/></td><td><Amount value={r.net_pnl??r.market_pnl}/></td><td className="pnl-attention">{positionAttention(r).length?<button type="button" className="pnl-review-note-link" title={positionAttention(r).join('; ')} aria-label={`Review notes: ${positionAttention(r).join('; ')}`} aria-controls={inspectorId} aria-expanded={inspectorOpen&&r.attribution_id===item?.attribution_id} onClick={event=>inspectPosition(r,event.currentTarget)}>{positionAttention(r).length} {positionAttention(r).length===1?'note':'notes'}</button>:'—'}</td><td><button type="button" aria-pressed={inspectorOpen&&item?.attribution_id===r.attribution_id} aria-expanded={inspectorOpen&&item?.attribution_id===r.attribution_id} aria-controls={inspectorId} onClick={event=>inspectPosition(r,event.currentTarget)}>Inspect position</button></td></tr>)}</tbody></table></div>
     {!filtered.length?<p>No positions match these filters. No zero P&amp;L is inferred.</p>:null}
     <nav className="pnl-pagination pnl-position-pagination" aria-label="Position pagination"><label>Positions per page<select value={pageSize} onChange={e=>{setPageSize(e.target.value as typeof pageSize);resetPage();}}><option value="25">25</option><option value="50">50</option><option value="100">100</option><option value="all">All</option></select></label><button type="button" disabled={currentPage===0} onClick={()=>{setPage(currentPage-1);setSelected(null);}}>Previous positions</button><span role="status">{filtered.length?`${currentPage*pageLength+1}–${currentPage*pageLength+rows.length} of ${filtered.length}`:'0 of 0'} positions · Page {currentPage+1} of {pageCount}</span><button type="button" disabled={currentPage+1>=pageCount} onClick={()=>{setPage(currentPage+1);setSelected(null);}}>Next positions</button></nav>
    </>}
   </section>
   {item?<aside id={inspectorId} hidden={!inspectorOpen} className="pnl-surface pnl-inspector" aria-label="Position inspection">
    <div className="pnl-panel-heading"><div><p className="pnl-kicker">Position inspection</p><h3 ref={inspectorHeading} tabIndex={-1}><InstrumentLabel display={metadata.instrumentDisplays?.[item.subject_id??'']} fallbackName={label(item)}/></h3><p className="pnl-muted">{positionContext(item,metadata)}</p></div><div className="pnl-inspector-actions"><span className="pnl-muted">v{item.version}</span><button type="button" className="pnl-inspector-close" aria-label="Close position details" title="Close position details" onClick={closeInspector}><span aria-hidden="true">×</span></button></div></div>
    {positionAttention(item).length?<section className="pnl-position-review-notes" aria-label="Position review notes"><h4>Review notes</h4><ul>{positionAttention(item).map(note=><li key={note}>{note}</li>)}</ul></section>:null}
    <AccruedBalanceInspection item={item} currencies={metadata.currencies} currency={currency}/>
    {(item.evidence as {resultFormat?:string}|null)?.resultFormat!=='ACCRUED_RECEIVABLE_V1'?<PositionCalculation item={item} metadata={metadata} currency={currency}/>:<p>Outstanding interest receivable, separate from the closed security holding. No security quantity or price is invented.</p>}
    <table className="pnl-table pnl-components"><caption>P&L components · {currency}</caption><thead><tr><th scope="col">Component</th><th scope="col">Amount</th></tr></thead><tbody>{Object.entries(item.components).map(([name,amount])=><tr key={name}><th scope="row">{componentLabel(name)}</th><td><Amount value={amount}/></td></tr>)}</tbody></table>
    <InputEvidence evidence={item.evidence} metadata={metadata}/>
    <details className="pnl-inspector-proof"><summary>Sources, applied rules and technical proof</summary>
    <p className="pnl-muted">Position-owned attribution. Original trades stay unchanged; no per-trade P&L allocation is inferred.</p>
    {(item.evidence as {resultFormat?:string}|null)?.resultFormat!=='ACCRUED_RECEIVABLE_V1'?<PositionFacts item={item} metadata={metadata}/>:null}
    <section aria-label="Selected prices and FX"><ValuationPriceEvidence evidence={item.evidence} metadata={metadata}/></section>
    <ShareAdjustments evidence={item.evidence}/>
    <details><summary>Original ledger evidence · {item.lineage?.length??0} events</summary>{item.lineage?.length?<ul>{item.lineage.map((link,index)=><li key={link.event_id}><a href={`/trades/${encodeURIComponent(link.trade_id)}`}>Open contributing trade {index+1}</a><span className="pnl-muted"> · {link.role.replaceAll('_',' ').toLowerCase()}</span><TechnicalReference id={link.trade_id} label="Trade ID"/></li>)}</ul>:<p>No ledger links returned for this version.</p>}</details>
    <details><summary>Exact amounts & rounding</summary><dl>{Object.entries(item.components).map(([name,amount])=><div key={name}><dt>{componentLabel(name)}</dt><dd>{amount}</dd></div>)}</dl><pre>{JSON.stringify((item.evidence as {storageRounding?:unknown})?.storageRounding??{note:'No storage rounding evidence on this historical version.'},null,2)}</pre></details>
    <TechnicalReference id={item.subject_id} label="Instrument ID"/><TechnicalReference id={item.attribution_id} label="Attribution ID"/>
    <details><summary>Frozen inputs and method</summary><pre>{JSON.stringify(item.evidence,null,2)}</pre></details>
    </details>
   </aside>:null}
  </div>
  </ReportPanel>
  <ReportPanel view="review" active={activeTab}><h3>Review</h3>{reviewContent??<p>Review controls are not available in this standalone report.</p>}</ReportPanel>
  <ReportPanel view="logs" active={activeTab}><h3>Logs</h3>{logsContent??<p>Operational events are not supplied to this standalone report.</p>}</ReportPanel>
 </>;
}
