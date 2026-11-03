import type {Batch} from './types';
import {displayAmount} from './presentation';
import {CoverageReview,isPartialResult} from './coverage-review';
export function ReviewSummary({batch,currency,onInspectCoverage}:{batch:Batch;currency:string;onInspectCoverage?:(scope:'positions'|'cash')=>void}){
 const pending=batch.presentation?.pendingAmendments;
 const stale=batch.sourceHealth&&batch.sourceHealth.status!=='CURRENT';
 const incomplete=batch.summary.requiredInputsComplete===false;
 const visible=(value:string|null|undefined)=>batch.summary.hasCalculatedContributions===false?undefined:value;
 return <section className="pnl-review-summary" aria-label="Daily review summary">
  <div className="pnl-metrics">
   {[[incomplete?'Calculated subtotal · incomplete':isPartialResult(batch)?'Total included P&L · partial':'Total recorded P&L',batch.summary.netPnl??batch.summary.marketPnl],['Price/FX P&L',batch.summary.marketPnl],
    ['Supplied interest earned',batch.presentation?.totals.interest],[batch.summary.cashCoverage?'Other components (incl. cash FX)':'Other components',batch.presentation?.totals.other]].map(([name,value])=><div key={name}><span>{name} · {currency}</span><strong title={visible(value)??undefined}>{displayAmount(visible(value)??undefined)}</strong></div>)}
  </div>
  <p className="pnl-muted">Economic P&amp;L, not full fund NAV. Amounts include recorded price/FX movement, cash FX, income, costs and adjustments. A dash means no separate amount recorded, not confirmed zero.</p>
  <details><summary>{incomplete?'Exact calculated subtotals':'Exact batch totals'}</summary><dl className="pnl-fact-grid">{[['Price/FX P&L',batch.summary.marketPnl],['Gross P&L',batch.summary.grossPnl],['Net P&L',batch.summary.netPnl],['Supplied interest',batch.presentation?.totals.interest],['Other components',batch.presentation?.totals.other]].map(([label,value])=><div key={label}><dt>{label} · {currency}</dt><dd>{visible(value)??'Not separately recorded'}</dd></div>)}</dl></details>
  {(stale||Boolean(pending))?<div className="pnl-review-blocker"><strong>Publication blockers</strong><ul>{stale?<li>Source evidence changed or is unverified. Recalculate and review a new candidate.</li>:null}{pending?<li>{pending} pending amendment request{pending===1?'':'s'} must be resolved.</li>:null}</ul></div>:null}
  <CoverageReview key={batch.batch_id} batch={batch} onInspect={onInspectCoverage}/>
  <p className="pnl-muted">External comparison: {batch.summary.externalComparison==='NOT_COMPARED'?'Not performed':batch.summary.externalComparison}. {pending===undefined?'Pending-amendment check: not loaded. ':''}Final permissions, source revisions and financial checks are revalidated by the server on publication.</p>
 </section>;
}
