import {formatImportDate,importStatus,type ImportJob} from './import-model';
import {ImportBadge} from './import-review';
import styles from './imports.module.css';

type Props={jobs:ImportJob[];total:number;offset:number;busy:boolean;disabled:boolean;loaded:boolean;
 onOpen:(id:string)=>void;onRefresh:()=>void;onPage:(offset:number)=>void};
export function ImportHistory({jobs,total,offset,busy,disabled,loaded,onOpen,onRefresh,onPage}:Props){
 return <section className={styles.card}>
  <header className={styles.header}><div><h2>Import history</h2><p>Retained files, validation outcomes and booking receipts in your current access scope.</p></div><button className={styles.secondary} disabled={busy} onClick={onRefresh}>Refresh history</button></header>
  {!loaded?<p className={styles.note}>Import history has not loaded yet. Refresh to load the current state.</p>:
   !jobs.length?<div className={styles.empty}><h3>No imports yet</h3><p>Files you can access will appear here after upload. Nothing is booked simply by uploading a file.</p></div>:
   <div className={styles.table}><table><thead><tr><th>Received</th><th>File / source</th><th>Status</th><th>Outcome</th><th>Review</th></tr></thead><tbody>{jobs.map(job=><tr key={job.jobId}>
    <td><time title={job.createdAt}>{formatImportDate(job.createdAt)}</time></td><td><strong>{job.filename}</strong><small>{job.source}</small></td>
    <td><ImportBadge status={job.status}/></td><td>{importStatus(job)}</td><td><button className={styles.secondary} disabled={disabled} aria-label={`Open import ${job.filename}`} onClick={()=>onOpen(job.jobId)}>Open import</button></td>
   </tr>)}</tbody></table></div>}
  {loaded?<div className={styles.pagination}><span>{total} imports{total?` · showing ${offset+1}–${Math.min(offset+25,total)}`:''}</span><div className={styles.actions}><button className={styles.secondary} disabled={offset===0||busy} onClick={()=>onPage(Math.max(0,offset-25))}>Previous</button><button className={styles.secondary} disabled={offset+25>=total||busy} onClick={()=>onPage(offset+25)}>Next</button></div></div>:null}
 </section>;
}
