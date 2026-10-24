import type {Ref} from 'react';
import Link from 'next/link';
import {canConfirm,fieldLabel,formatImportDate,importStatus,statusLabel,type ImportJob} from './import-model';
import styles from './imports.module.css';

export function ImportBadge({status}:{status:string}){
 return <span className={styles.badge} data-state={status}>{statusLabel(status)}</span>;
}

type ReviewProps={job:ImportJob;canWrite:boolean;disabled:boolean;busy:boolean;headingRef:Ref<HTMLHeadingElement>;
 onValidate:()=>void;onConfirm:()=>void;onPage:(offset:number)=>void;strategyLabel:string};

export function ImportReview({job,canWrite,disabled,busy,headingRef,onValidate,onConfirm,onPage,strategyLabel}:ReviewProps){
 const download=`/api/trade-imports/${job.jobId}`;
 // Errors first *within this server-supplied page*, never imply a whole-history client filter.
 const rows=[...job.rows].sort((a,b)=>Number(b.errors.length>0)-Number(a.errors.length>0)||a.row-b.row);
 const complete=job.status==='APPLIED';
 const cards=complete?[['File rows',job.total],['New trades booked',job.applied],['Already booked',job.replayed],['Rows to fix',job.invalid]]:
  [['File rows',job.total],['Valid rows',job.valid],['Rows to fix',job.invalid],['Already booked',job.replayed]];
 return <section className={styles.card} aria-label="Import review">
  <header className={styles.header}><div><span className={styles.kicker}>Step 3 · Review & book</span>
   <h2 ref={headingRef} tabIndex={-1} className={styles.reviewTitle}>Review {job.filename}</h2>
   <p>{strategyLabel} <span aria-hidden="true">·</span> File source: {job.source}</p></div><ImportBadge status={job.status}/></header>
  <div className={styles.stats}>{cards.map(([label,value])=><div className={styles.stat} key={label} data-attention={label==='Rows to fix'&&Number(value)>0}><span>{label}</span><strong>{job.status==='RECEIVED'?'—':value}</strong></div>)}</div>
  <p className={styles.live} role="status">{importStatus(job)}</p>
  {job.status==='NEEDS_CORRECTION'?<div className={`${styles.note} ${styles.error}`}><strong>Nothing booked.</strong> Correct the listed errors in your file and submit a revised upload. Valid rows remain available in this review.</div>:null}
  {complete?<div className={`${styles.note} ${styles.success}`}><strong>Booking completed.</strong> Use the trade links below to inspect retained records. Already-booked source IDs were not booked again.</div>:null}
  {canWrite&&!complete?<div className={styles.actionBar}>
   <p>{job.status==='READY'?'All rows passed. Check the proposed trades and properties before confirming. Booking rechecks current permissions and data.':'Validation checks the entire file. Every row must pass before this batch can be booked.'}</p>
   <div className={styles.actions}><button className={canConfirm(job)?styles.secondary:styles.primary} disabled={disabled} onClick={onValidate}>Validate all rows</button>
    {job.total>0?<button className={styles.primary} disabled={disabled||!canConfirm(job)} onClick={onConfirm}>{job.total===job.replayed&&job.total>0?'Confirm existing trades':`Book ${job.total-job.replayed} trades`}{job.replayed&&job.total!==job.replayed?` · retain ${job.replayed} existing`:''}</button>:null}</div>
  </div>:null}
  <div className={styles.header}><div><h3>Trade rows</h3><p className={styles.hint}>{job.status==='RECEIVED'?'Validate your file to inspect its rows. Nothing has been booked.':`Errors appear first on this page. Validation covered the full file, not just the ${job.rows.length} records shown.`}</p></div>
   <div className={styles.actions}><a href={`${download}/artifact`}>Original file</a><a href={`${download}/errors`}>Download error report</a></div></div>
  {rows.length?<div className={styles.table}><table><thead><tr><th>Row / source trade</th><th>Instrument</th><th className={styles.numeric}>Quantity</th><th className={styles.numeric}>Price</th><th>Execution / settlement</th><th>Status & action</th><th>Details</th></tr></thead>
   <tbody>{rows.map(row=>{
    const receipt=job.receipt.find(item=>item.row===row.row);
    const type=row.evidence?.instrumentType;
    return <tr key={row.row} data-error={row.errors.length>0}>
     <td><strong>{row.row===0?'File':`Row ${row.row}`}</strong><small>{row.sourceTradeId||'File-level issue'}</small></td>
     <td>{row.evidence?.instrumentId?<Link href={`/instruments/${row.evidence.instrumentId}`}>{type==='EQUITY'?'Equity':type==='ETF'?'ETF':type?'Fund':'Instrument'}</Link>:type??'See submitted listing'}<small>Listing details in row fields</small></td>
     <td className={styles.numeric}>{row.values?.quantity??'—'}<small>{row.values?.side??''}</small></td>
     <td className={styles.numeric}>{row.values?.executionPrice??'—'}<small>{row.evidence?.currency??row.values?.tradeCurrency??''}</small></td>
     <td>{row.values?.tradeDatetime?<time title={row.values.tradeDatetime}>{formatImportDate(row.values.tradeDatetime)}</time>:'—'}<small>Settlement: {row.values?.settlementDate||'—'}</small></td>
     <td><ImportBadge status={receipt?(receipt.outcome==='BOOKED'?'APPLIED':'REPLAY'):row.status}/>{row.errors.map((error,i)=><p key={i}><strong>{fieldLabel(error.field)}: </strong>{error.message}</p>)}
      {receipt?<p><Link href={`/trades/${receipt.tradeId}`}>{receipt.outcome==='BOOKED'?'Open booked trade':'Open existing trade'}</Link></p>:null}</td>
     <td><details><summary>Inspect row fields</summary><dl>{Object.entries(row.values??{}).filter(([,value])=>value).map(([key,value])=><div key={key}><dt>{fieldLabel(key)}<code className={styles.machineKey}>{key}</code></dt><dd>{value}</dd></div>)}</dl></details></td>
    </tr>;
   })}</tbody></table></div>:<div className={styles.empty}><h3>Ready for validation</h3><p>Your original file is retained. Validate it to see the proposed trades and any errors. No trades have been booked.</p></div>}
  {job.total>0?<div className={styles.pagination}><span>Showing {job.offset+1}–{Math.min(job.offset+job.limit,job.total)} of {job.total} records</span><div className={styles.actions}>
   <button className={styles.secondary} disabled={disabled||job.offset===0} onClick={()=>onPage(Math.max(0,job.offset-job.limit))}>Previous rows</button>
   <button className={styles.secondary} disabled={disabled||job.offset+job.limit>=job.total} onClick={()=>onPage(job.offset+job.limit)}>Next rows</button></div></div>:null}
  <details className={styles.technical}><summary>Import identifiers & audit details</summary><dl><dt>Job ID</dt><dd>{job.jobId}</dd><dt>Strategy ID</dt><dd>{job.strategyId}</dd><dt>Received</dt><dd>{job.createdAt}</dd><dt>Review hash</dt><dd>{job.reviewHash??'Not validated yet'}</dd></dl></details>
  {busy?<p className={styles.live}>Processing your request. A timeout does not imply that a booking failed.</p>:null}
 </section>;
}
