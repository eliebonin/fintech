import type {Batch,SourceCoverageRow} from './types';
import {displayAmount} from './presentation';

const statusLabels:Record<SourceCoverageRow['status'],string>={
 INCLUDED:'Included · recorded',PARTIAL:'Partial · missing interest',MISSING_INPUTS:'Missing inputs · Excluded',
 NOT_RECORDED:'No recorded entries',NOT_ASSESSED:'Not assessed'
};

function amountClass(value:string|null){
 if(value===null||!/^-?\d+(\.\d+)?$/.test(value)||!/[1-9]/.test(value))return 'pnl-amount';
 return `pnl-amount ${value.startsWith('-')?'pnl-negative':'pnl-positive'}`;
}

/** Present only server-projected stored amounts. Never derive cash earnings from stocks. */
export function PnlSourceCoverage({batch,currency,onInspect}:{batch:Batch;currency:string;onInspect:(row:SourceCoverageRow)=>void}){
 if(batch.summary.evidenceAccess==='DENIED')return null;
 const coverage=batch.presentation?.sourceCoverage;
 return <section className="pnl-surface pnl-source-coverage" aria-label="P&L sources and coverage">
  <div className="pnl-panel-heading"><h3>P&amp;L sources &amp; coverage</h3><span>{batch.summary.requiredInputsComplete===false?'Calculated subtotals':'Whole result'} · {currency}</span></div>
  {coverage?<>
   <div className="pnl-table-scroll"><table className="pnl-table pnl-source-table"><caption>P&amp;L sources · {currency}</caption>
    <thead><tr><th scope="col">Source</th><th scope="col">Recorded amount · {currency}</th><th scope="col">Coverage</th><th scope="col">Inspect</th></tr></thead>
    <tbody>{coverage.rows.map(row=><tr key={row.code}>
     <th scope="row">{row.label}<small>{row.description}</small></th>
     <td><span className={amountClass(row.amount)} title={row.amount??undefined}>{row.amount===null?'—':displayAmount(row.amount)}</span></td>
     <td className="pnl-source-status"><span className={`pnl-source-state pnl-source-${row.status.toLowerCase()}`}>{row.code==='CASH_BALANCE_FX'&&Boolean(batch.summary.cashCoverage?.missingFxCount)?'Incomplete · missing required FX':['PRICE','FX','PRICE_FX_CROSS'].includes(row.code)&&row.status==='PARTIAL'?'Partial · missing marks':row.code==='CARRY'&&row.status==='PARTIAL'?'Partial · accrued balance / FX inputs missing':row.code==='CARRY'&&row.status==='MISSING_INPUTS'?'Not calculated · missing balance / FX':row.code==='CASH_BALANCE_FX'&&row.status==='MISSING_INPUTS'?'Not supplied · Not included':row.status==='PARTIAL'&&row.code==='CASH_BALANCE_FX'?'Partial · missing cash inputs':statusLabels[row.status]}</span>
      {row.positionCount>0?<small>{row.positionCount} contributing {batch.summary.resultFormat==='TRADE_V1'?'attributions':'positions'}</small>:null}
      {row.cashAccountCount?<small>{row.cashAccountCount} cash account/currency attributions</small>:null}
      {row.missingCount>0?<small>{row.missingCount} missing {row.code==='CASH_BALANCE_FX'?'cash scope/date':'instrument/date'} inputs</small>:null}</td>
     <td>{row.positionCount>0||Boolean(row.cashAccountCount)?<button type="button" aria-label={`${row.cashAccountCount&&!row.positionCount?'Inspect cash accounts':'Inspect positions'}: ${row.label}`} onClick={()=>onInspect(row)}>{row.cashAccountCount&&!row.positionCount?'Inspect cash accounts':'Inspect positions'}</button>:row.code==='CASH_BALANCE_FX'?<a href="/valuation/cash-balances">Cash records</a>:<span className="pnl-muted">{row.status==='NOT_ASSESSED'?'Not assessed':'No recorded contributions'}</span>}</td>
    </tr>)}</tbody>
    <tfoot><tr><th scope="row">{batch.summary.requiredInputsComplete===false?'Calculated component subtotal':'Total included components'}</th><td className={amountClass(coverage.includedTotal)} title={coverage.includedTotal??undefined}>{displayAmount(coverage.includedTotal??undefined)}</td><td colSpan={2}>{coverage.reconciliation==='MATCH'?batch.summary.requiredInputsComplete===false?'Reconciles to calculated subtotal':'Reconciles to recorded total':coverage.reconciliation==='MISMATCH'?'Does not reconcile — investigate retained components':'Reconciliation not assessed for this historical result'}</td></tr></tfoot>
   </table></div>
   <details><summary>Exact source amounts &amp; definitions</summary><dl className="pnl-fact-grid">{coverage.rows.map(row=><div key={row.code}><dt>{row.label} · {currency}</dt><dd>{row.amount??statusLabels[row.status]}</dd></div>)}<div><dt>Stored net total · {currency}</dt><dd>{coverage.recordedNet??'Not recorded'}</dd></div></dl><p>Amounts are grouped from this result version’s stored components. Separate price, position FX and their interaction sum to Price/FX P&amp;L; do not add that subtotal again. Accrued-interest FX belongs to interest, not the position FX subtotal. Displays are rounded; exact values reconcile before display rounding.</p></details>
  </>:<p className="pnl-review-warning">Coverage breakdown unavailable for this response. Refresh the selected result against the updated API; no source amounts or zero coverage are inferred.</p>}
  <p className="pnl-muted">A dash is not a confirmed zero. &lt;0.01 and −&lt;0.01 mark positive and negative nonzero amounts that would round to zero at two decimal places; exact values remain inspectable. “Included” means recorded in this result, and does not certify that every income or cost due was supplied. No recorded dividend or reset is not proof that none was due. Coupon payment confirmations alone do not create additional P&amp;L.</p>
 </section>;
}
