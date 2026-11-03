import type {Batch} from './types';
import {positionAttention} from './ops-review-model';
import {useRef} from 'react';

export function isPartialResult(batch:Batch){
 return batch.summary.requiredInputsComplete===false||batch.summary.pnlCompleteness==='PARTIAL'||[batch.summary.accrualCoverage,batch.summary.accruedBalanceCoverage,batch.summary.cashCoverage].some(c=>(c?.missingCount??0)>0);
}

/** One persistent, quiet disclosure. Missing optional inputs never become gates. */
export function CoverageReview({batch,onInspect}:{batch:Batch;onInspect?:(scope:'positions'|'cash')=>void}){
 const disclosure=useRef<HTMLDetailsElement>(null);
 if(batch.summary.evidenceAccess==='DENIED')return null;
 const {accrualCoverage:interest,accruedBalanceCoverage:stock,cashCoverage:cash}=batch.summary;
 const affected=batch.items.filter(item=>!item.cash_account_id&&positionAttention(item).length>0);
 const notes=[...new Set(affected.flatMap(positionAttention))];
 const partial=isPartialResult(batch),cashMissing=cash?.missingCount??0;
 if(!partial&&!notes.length&&!stock?.warnings?.length)return null;
 const references=batch.presentation?.references??{},accounts=batch.presentation?.cashAccounts??{},currencies=batch.presentation?.currencies??{};
 function inspect(scope:'positions'|'cash'){disclosure.current?.removeAttribute('open');onInspect?.(scope);}
 return <details ref={disclosure} className="pnl-coverage-review">
  <summary><span aria-hidden="true">△ </span><span role="status" aria-live="polite" aria-atomic="true"><strong>Inputs to review</strong> · {partial?'partial coverage':'review notes'}{batch.summary.inputCoverage?.missingCount?` · ${batch.summary.inputCoverage.missingCount} required marks`:''}{affected.length?` · ${affected.length} position${affected.length===1?'':'s'}`:''}{cashMissing?` · ${cashMissing} cash input${cashMissing===1?'':'s'}`:''}</span></summary>
  <div className="pnl-coverage-content">
   <p>{batch.summary.requiredInputsComplete===false?'Required price inputs are missing. Amounts are calculated subtotals; publication requires supplied marks or reviewed manual marks followed by recalculation.':'Included components remain usable. Missing inputs are not zero. Publication remains available for these optional omissions; separate publication blockers still apply.'}</p>
   {batch.summary.inputCoverage?.missingCount?<p>{batch.summary.inputCoverage.missingCount} required price / FX input{batch.summary.inputCoverage.missingCount===1?'':'s'} missing · {batch.summary.inputCoverage.affectedPositionCount} unpriced position{batch.summary.inputCoverage.affectedPositionCount===1?'':'s'}{batch.summary.inputCoverage.unpricedCashAccounts?.length?` · ${batch.summary.inputCoverage.unpricedCashAccounts.length} unpriced cash account/currency scopes`:''}.</p>:null}
   <ul>{interest?.missingCount?<li>{interest.missingCount} daily-interest / FX input{interest.missingCount===1?'':'s'} not included.</li>:null}
    {stock?.missingCount?<li>{stock.missingCount} accrued-balance / FX input{stock.missingCount===1?'':'s'} not calculated.</li>:null}
    {cashMissing?<li>{cashMissing} cash account/currency/date input{cashMissing===1?'':'s'} missing.</li>:null}
    {notes.map(note=><li key={note}>{note}</li>)}
    {stock?.warnings?.length&&!notes.includes('Accrued balance mismatch')?<li>Accrued-balance reconciliation needs review.</li>:null}
   </ul>
   <div className="pnl-review-actions">{onInspect&&affected.length?<button type="button" onClick={()=>inspect('positions')}>Show affected positions</button>:null}{onInspect&&cashMissing?<button type="button" onClick={()=>inspect('cash')}>Show cash coverage</button>:null}</div>
   {(interest?.missing.length||stock?.missing.length||cash?.missing.length)?<details><summary>Missing dates and scopes</summary><ul>
    {interest?.missing.map((r,index)=><li key={`interest-${index}`}>{r.valueDate} · <a href={`/instruments/${encodeURIComponent(r.instrumentId)}`}>{references[r.instrumentId]??'Instrument'}</a> · daily interest / FX</li>)}
    {stock?.missing.map((r,index)=><li key={`stock-${index}`}>{r.valueDate} · <a href={`/instruments/${encodeURIComponent(r.instrumentId)}`}>{references[r.instrumentId]??'Instrument'}</a> · {r.reason.replaceAll('_',' ').toLowerCase()}</li>)}
    {cash?.missing.map((r,index)=><li key={`cash-${index}`}>{r.valueDate} · {accounts[r.accountId]??'Cash account'} · {currencies[r.currencyId]??'Currency'} · missing {r.missingOpening&&r.missingClosing?'opening and closing':r.missingOpening?'opening':'closing'} snapshot</li>)}
   </ul></details>:null}
  </div>
 </details>;
}
