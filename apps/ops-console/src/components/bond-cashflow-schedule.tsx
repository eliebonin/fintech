'use client';
import {useState} from 'react';
import {formatTradeExactDecimal} from '@/lib/trades';

export type Cashflow={cashflow_id:string;cashflow_key:string;cashflow_type:'COUPON'|'PRINCIPAL';accrual_start:string|null;accrual_end:string|null;payment_date:string;record_date?:string|null;ex_date?:string|null;coupon_rate:string|null;amount_per_100:string|null;amount_formula:string|null};
export type Schedule={schedule_id:string;revision:number;source_reference:string;currencyCode:string;calendar_id?:string|null;day_count_convention_id?:string|null;business_day_convention?:string|null;cashflows:Cashflow[]};
type CashflowDraft={cashflowKey:string;cashflowType:'COUPON'|'PRINCIPAL';accrualStart:string;accrualEnd:string;paymentDate:string;recordDate:string;exDate:string;couponRate:string;amountPer100:string;amountFormula:string};
const blankCashflow=():CashflowDraft=>({cashflowKey:'',cashflowType:'COUPON',accrualStart:'',accrualEnd:'',paymentDate:'',recordDate:'',exDate:'',couponRate:'',amountPer100:'',amountFormula:''});

export function BondCashflowScheduleTable({cashflows,currency}:{cashflows:Cashflow[];currency:string}){
 return <><p>Amounts in {currency}, per 100 original nominal. These contractual amounts are independent of your strategy holding.</p>
  <div className="workspace-table-scroll"><table><caption>Contractual expectations — not payment confirmations</caption><thead><tr><th scope="col">Payment type</th><th scope="col">Reference</th><th scope="col">Scheduled payment</th><th scope="col">Accrual period</th><th scope="col">Amount per 100 ({currency})</th><th scope="col">Rate / formula</th></tr></thead><tbody>{cashflows.map(row=><tr key={row.cashflow_id}>
   <td>{row.cashflow_type==='COUPON'?'Coupon':'Principal'}</td><th scope="row">{row.cashflow_key}</th><td>{row.payment_date}</td>
   <td>{row.cashflow_type==='COUPON'?`${row.accrual_start} → ${row.accrual_end}`:'Not applicable'}</td>
   <td>{row.amount_per_100===null?'Not fixed / unknown':formatTradeExactDecimal(row.amount_per_100)}</td>
   <td>{row.coupon_rate!==null&&<span>Rate (decimal): {row.coupon_rate}<br/></span>}{row.amount_formula??(row.coupon_rate===null?'—':'')}</td>
  </tr>)}</tbody></table></div></>;
}

export function ScheduleEditor({schedule,disabled,onSave}:{schedule:Schedule|null;disabled:boolean;onSave:(fields:Record<string,unknown>)=>void}){
 const [rows,setRows]=useState<CashflowDraft[]>(schedule?.cashflows.map(row=>({cashflowKey:row.cashflow_key,cashflowType:row.cashflow_type,accrualStart:row.accrual_start??'',accrualEnd:row.accrual_end??'',paymentDate:row.payment_date,recordDate:row.record_date??'',exDate:row.ex_date??'',couponRate:row.coupon_rate??'',amountPer100:row.amount_per_100??'',amountFormula:row.amount_formula??''}))??[blankCashflow()]);
 function update(index:number,field:keyof CashflowDraft,value:string){
  setRows(current=>current.map((row,i)=>i!==index?row:field==='cashflowType'
   ?{...blankCashflow(),cashflowKey:row.cashflowKey,paymentDate:row.paymentDate,cashflowType:value as CashflowDraft['cashflowType']}
   :{...row,[field]:value}));
 }
 return <form className="bond-cashflow-editor" onSubmit={event=>{event.preventDefault();const data=new FormData(event.currentTarget);onSave({sourceReference:data.get('source'),reason:data.get('reason'),calendarId:data.get('calendar')||null,dayCountConventionId:data.get('dayCount')||null,businessDayConvention:data.get('convention')||null,cashflows:rows.map(row=>Object.fromEntries(Object.entries(row).filter(([,value])=>value!==''))),confirmSchedule:true});}}>
  <fieldset disabled={disabled}><legend>Sourced bond cashflows</legend>
   <div className="bond-cashflow-fields"><label>Source / document reference<input name="source" required maxLength={2000}/></label><label>Reason<input name="reason" required maxLength={2000}/></label></div>
   <details><summary>Contract conventions (optional sourced metadata)</summary><div className="bond-cashflow-fields">
    <label>Calendar UUID<input name="calendar" defaultValue={schedule?.calendar_id??''}/></label><label>Day-count convention UUID<input name="dayCount" defaultValue={schedule?.day_count_convention_id??''}/></label>
    <label>Business-day convention<select name="convention" defaultValue={schedule?.business_day_convention??''}><option value="">Not supplied</option>{['UNADJUSTED','FOLLOWING','MODIFIED_FOLLOWING','PRECEDING','MODIFIED_PRECEDING'].map(c=><option key={c}>{c}</option>)}</select></label>
   </div><p>These describe explicit sourced dates. Saving does not generate or adjust dates.</p></details>
   {rows.map((row,index)=><fieldset className="bond-cashflow-row" key={index}><legend>Cashflow {index+1}</legend><div className="bond-cashflow-fields">
    <label>Payment type<select value={row.cashflowType} onChange={event=>update(index,'cashflowType',event.target.value)}><option value="COUPON">Coupon</option><option value="PRINCIPAL">Principal</option></select></label>
    <label>Cashflow reference<input required maxLength={100} value={row.cashflowKey} onChange={event=>update(index,'cashflowKey',event.target.value)}/></label>
    <label>Scheduled payment<input type="date" required value={row.paymentDate} onChange={event=>update(index,'paymentDate',event.target.value)}/></label>
    <label>Amount per 100 original nominal<input inputMode="decimal" placeholder={row.cashflowType==='PRINCIPAL'?'Use the contractual redemption amount':'Unknown until fixed, if applicable'} value={row.amountPer100} onChange={event=>update(index,'amountPer100',event.target.value)}/></label>
    {row.cashflowType==='COUPON'&&<>
     <label>Accrual start<input type="date" required value={row.accrualStart} onChange={event=>update(index,'accrualStart',event.target.value)}/></label>
     <label>Accrual end<input type="date" required value={row.accrualEnd} onChange={event=>update(index,'accrualEnd',event.target.value)}/></label>
     <label>Coupon rate (decimal fraction, optional)<input inputMode="decimal" placeholder="0.05 means 5%" value={row.couponRate} onChange={event=>update(index,'couponRate',event.target.value)}/></label>
    </>}
    <label>Payment formula (if not fixed)<input maxLength={2000} value={row.amountFormula} onChange={event=>update(index,'amountFormula',event.target.value)}/></label>
   </div>{row.cashflowType==='COUPON'&&<details><summary>Record and ex-coupon dates</summary><div className="bond-cashflow-fields"><label>Record date<input type="date" value={row.recordDate} onChange={event=>update(index,'recordDate',event.target.value)}/></label><label>Ex-coupon date<input type="date" value={row.exDate} onChange={event=>update(index,'exDate',event.target.value)}/></label></div></details>}
    <button type="button" disabled={rows.length===1} onClick={()=>setRows(current=>current.filter((_,i)=>i!==index))}>Remove cashflow {index+1}</button>
   </fieldset>)}
   <button type="button" disabled={rows.length>=500} onClick={()=>setRows(current=>[...current,blankCashflow()])}>Add cashflow</button>
   <p>Enter final coupon and principal as separate rows, even on the same date. Use sourced amounts per 100 original nominal; never assume redemption at par. A rate or formula keeps an unknown amount unknown.</p>
   <label className="bond-cashflow-confirm"><input type="checkbox" required/>I verified these dates and economics against the source.</label><button>Save new schedule revision</button>
  </fieldset>
 </form>;
}
