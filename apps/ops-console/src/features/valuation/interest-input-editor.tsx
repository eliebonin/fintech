'use client';
import {useEffect,useId,useRef,useState,type FormEvent,type ReactNode} from 'react';
import {BffApiError} from '@/lib/api-errors';
import {closingBalanceBody,dailyInterestBody,InterestFieldError,interestToday,type InterestFields} from './interest-model';
import type {InterestContext,InterestEditor,InterestIntent,InterestOptions} from './interest-types';
import styles from './interest-workspace.module.css';

export function InterestDialog({title,description,locked=false,dirty=false,onClose,children}:{title:string;description:string;locked?:boolean;dirty?:boolean;onClose:()=>void;children:ReactNode}){
 const dialog=useRef<HTMLDialogElement>(null),id=useId(),[discard,setDiscard]=useState(false);
 useEffect(()=>{const node=dialog.current;node?.showModal();return()=>{if(node?.open)node.close();};},[]);
 useEffect(()=>{if(!dirty)return;const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',guard);return()=>window.removeEventListener('beforeunload',guard);},[dirty]);
 function close(){if(locked)return;if(dirty)setDiscard(true);else onClose();}
 return <dialog ref={dialog} className={`pnl-workspace ${styles.dialog}`} aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`} onCancel={event=>{event.preventDefault();close();}}>
  <header className={styles.dialogHeading}><div><h2 id={`${id}-title`}>{title}</h2><p id={`${id}-description`}>{description}</p></div><button type="button" className={styles.close} aria-label="Close editor" disabled={locked} onClick={close}>×</button></header>
  {discard&&<div className={styles.discard} role="alert"><strong>Discard your unsaved changes?</strong><p>The input has not been saved.</p><div className={styles.actions}><button type="button" onClick={()=>setDiscard(false)} autoFocus>Keep editing</button><button type="button" className={styles.danger} onClick={onClose}>Discard changes</button></div></div>}<div hidden={discard}>{children}</div>
 </dialog>;
}

export function InterestInputEditor({editor,context,options,locked,error,retry,onSave,onClose}:{editor:InterestEditor;context:InterestContext;options:InterestOptions;locked:boolean;error:Error|null;retry?:ReactNode;onSave:(intent:InterestIntent)=>void;onClose:()=>void}){
 const {row}=editor,isDaily=editor.kind==='daily',withdraw=editor.kind==='withdraw';
 const id=useId(),summary=useRef<HTMLDivElement>(null),[dirty,setDirty]=useState(false),[errors,setErrors]=useState<Record<string,string>>({});
 const [bond,setBond]=useState(row?.instrument_id??editor.prefill?.instrumentId??''),[currency,setCurrency]=useState(row?.currency_id??editor.prefill?.currencyId??'');
 const detailed=editor.kind==='daily'?editor.row?.payload.inputs:undefined;
 const title=withdraw?'Withdraw closing-balance input':`${row?'Correct':'Add'} ${isDaily?'daily interest':'closing-balance input'}`;
 useEffect(()=>{if(error||Object.keys(errors).length)summary.current?.focus();},[error,errors]);
 const fields=error instanceof BffApiError?error.fieldErrors:undefined;
 const serverErrors=Object.fromEntries(Object.entries(fields??{}).map(([key,value])=>{const field=key.split('.').at(-1)!;return [field==='dailyEarned'||field==='closingBalance'&&!detailed?'amount':field,value.join(' ')];}));
 const fieldErrors={...serverErrors,...errors};
 const message=(field:string)=>fieldErrors[field]?<small className={styles.fieldError} id={`${id}-${field}-error`}>{fieldErrors[field]}</small>:null;
 function invalid(field:string){return {'aria-invalid':!!fieldErrors[field],'aria-describedby':fieldErrors[field]?`${id}-${field}-error`:undefined};}
 function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(locked)return;setErrors({});
  const form=event.currentTarget,data=new FormData(form),values:InterestFields={instrumentId:bond,currencyId:currency,valueDate:String(data.get('valueDate')??''),amount:String(data.get('amount')??''),source:String(data.get('source')??''),reason:String(data.get('reason')??'')};
  if(detailed)for(const key of ['openingBalance','closingBalance','balanceMovements'] as const)values[key]=String(data.get(key)??'');
  try{
   const body=editor.kind==='daily'?dailyInterestBody(context.strategyId,values,editor.row):closingBalanceBody(context.strategyId,values,editor.row,withdraw);
   onSave({path:isDaily?'accrual-inputs':'balance-inputs',body});
  }catch(cause){setErrors({[cause instanceof InterestFieldError?cause.field:'general']:cause instanceof Error?cause.message:'Check the input values.'});}
 }
 const selected=options.bonds.find(item=>item.id===bond);
 const bondChoices=selected||!row?options.bonds:[{id:row.instrument_id,label:row.instrument_name??'Retained bond',currencyId:row.currency_id,currency:row.currency_code??'Retained currency'},...options.bonds];
 const currencies=options.currencies.some(item=>item.id===currency)||!row?options.currencies:[{id:row.currency_id,label:row.currency_code??'Retained currency'},...options.currencies];
 return <InterestDialog title={title} description={row?`A new revision will retain the original input and its source evidence.`:'Amounts are stored exactly in the selected local currency.'} locked={locked} dirty={dirty} onClose={onClose}>
  <p className={styles.context}><strong>{context.strategyLabel||'Selected strategy'}</strong>{row&&<> · {row.value_date} · revision {row.revision}</>}</p>
  {(error||Object.keys(errors).length>0)&&<div ref={summary} tabIndex={-1} role="alert" className={styles.error}><strong>The input has not been confirmed.</strong><p>{error?.message??'Check the highlighted fields.'}</p>{Object.entries(fieldErrors).map(([field,text])=><p key={field}>{['instrumentId','currencyId','valueDate','amount','sourceReference','reason','openingBalance','closingBalance','balanceMovements'].includes(field)?<a href={`#${id}-${field}`}>{text}</a>:text}</p>)}</div>}
  {retry}
  <form onSubmit={submit} onChange={()=>{setDirty(true);setErrors({});}}>
   <fieldset disabled={locked} className={styles.fields}>
    <label>Bond<select id={`${id}-instrumentId`} required value={bond} disabled={!!row} {...invalid('instrumentId')} onChange={event=>{setBond(event.target.value);setCurrency(options.bonds.find(item=>item.id===event.target.value)?.currencyId??'');}} autoFocus={!row}><option value="">Choose a bond</option>{bondChoices.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select>{message('instrumentId')}</label>
    <label>Currency<select id={`${id}-currencyId`} required value={currency} disabled={!!row||!isDaily} {...invalid('currencyId')} onChange={event=>setCurrency(event.target.value)}><option value="">Choose currency</option>{currencies.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select>{!isDaily&&<small>Uses the bond’s local currency.</small>}{message('currencyId')}</label>
    <label>Value date<input id={`${id}-valueDate`} type="date" name="valueDate" required max={interestToday()} defaultValue={row?.value_date??editor.prefill?.valueDate??context.to} readOnly={!!row} {...invalid('valueDate')}/>{message('valueDate')}</label>
    {!withdraw&&<label>{isDaily?'Daily earned amount':'Closing accrued balance'}<input id={`${id}-amount`} aria-label={isDaily?'Daily earned amount':'Closing accrued balance'} name="amount" required inputMode="decimal" defaultValue={editor.kind==='daily'?editor.row?.daily_earned_interest:editor.row?.closing_balance??''} {...invalid('amount')}/><small>{isDaily?'Interest earned on this date; not the accumulated balance.':'Total accrued interest at the end of this date; not daily income.'} Negative and zero amounts are allowed.</small>{message('amount')}{message(isDaily?'dailyEarned':'closingBalance')}</label>}
    <label className={styles.full}>Source reference<input id={`${id}-sourceReference`} name="source" required maxLength={isDaily?500:2000} defaultValue={editor.kind==='daily'?editor.row?.payload.sourceReference:editor.row?.source_reference} placeholder="Statement, file or source record reference" {...invalid('sourceReference')}/>{message('sourceReference')}</label>
    {!isDaily&&<label className={styles.full}>{withdraw?'Withdrawal reason':'Assessment / correction reason'}<textarea id={`${id}-reason`} name="reason" required maxLength={2000} rows={3} {...invalid('reason')} placeholder={withdraw?'Explain why this input must no longer be used.':'Explain how the closing balance was established or why it changed.'}/>{message('reason')}</label>}
    {detailed&&<fieldset className={styles.reconciliation}><legend>Retained reconciliation</legend><p>This input also reconciles balances. Keep the bridge consistent with the corrected daily amount; the service validates it using its retained pricing context.</p>{(['openingBalance','closingBalance','balanceMovements'] as const).map(key=><label key={key}>{key==='openingBalance'?'Opening accrued balance':key==='closingBalance'?'Closing accrued balance':'Balance movements'}<input id={`${id}-${key}`} name={key} required inputMode="decimal" defaultValue={detailed[key]} {...invalid(key)}/>{message(key)}</label>)}</fieldset>}
   </fieldset>
   <p className={styles.effect}>{withdraw?'Withdraws this source revision. It does not replace the amount with zero. Rebuild accrued balances afterwards.':isDaily?'Saving validates a daily source. Rebuild accrued balances to incorporate the revision.':'Saving records a sourced closing stock. Rebuild accrued balances to apply it to history.'}</p>
   <footer className={styles.actions}><button type="submit" disabled={locked||!bond||!currency} className={withdraw?styles.danger:styles.primary}>{locked?'Awaiting confirmation…':withdraw?'Withdraw input':row?'Save new revision':'Save input'}</button></footer>
  </form>
 </InterestDialog>;
}
