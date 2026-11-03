import type {KeyboardEvent,ReactNode} from 'react';
import {reportViews,type ReportView} from './report-navigation';

const labels:Record<ReportView,string>={breakdown:'Breakdown',positions:'Positions & cash',review:'Review',logs:'Logs'};
export function ReportTabs({active,onNavigate,pendingAmendments=0}:{active:ReportView;onNavigate:(view:ReportView)=>void;pendingAmendments?:number}){
 function key(event:KeyboardEvent<HTMLButtonElement>,view:ReportView){
  const index=reportViews.indexOf(view);
  const next=event.key==='ArrowRight'?(index+1)%4:event.key==='ArrowLeft'?(index+3)%4:event.key==='Home'?0:event.key==='End'?3:null;
  if(next===null)return;
  event.preventDefault();onNavigate(reportViews[next]);
  document.getElementById(`pnl-report-${reportViews[next]}-tab`)?.focus();
 }
 return <div role="tablist" aria-label="Selected valuation report" className="pnl-tabs pnl-report-tabs">{reportViews.map(view=><button key={view} type="button" role="tab" id={`pnl-report-${view}-tab`} aria-controls={`pnl-report-${view}-panel`} aria-selected={active===view} tabIndex={active===view?0:-1} onClick={()=>onNavigate(view)} onKeyDown={event=>key(event,view)}>{labels[view]}{view==='review'&&pendingAmendments>0?<span className="pnl-tab-count" aria-hidden="true" title={`${pendingAmendments} pending amendments`}>{pendingAmendments}</span>:null}</button>)}</div>;
}
/** Mounted panels retain filters, evidence disclosures and reviewed drafts. */
export function ReportPanel({view,active,children}:{view:ReportView;active:ReportView;children:ReactNode}){
 return <section id={`pnl-report-${view}-panel`} role="tabpanel" aria-labelledby={`pnl-report-${view}-tab`} tabIndex={0} hidden={view!==active} className="pnl-tab-panel pnl-report-panel">{children}</section>;
}
