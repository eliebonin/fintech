/** UI location only; the server still authorizes every selected attempt. */
export const reportViews=['breakdown','positions','review','logs'] as const;
export type ReportView=typeof reportViews[number];
export type ReportLocation={attemptId:string;view:ReportView};

export function readReportLocation(hash:string):ReportLocation|null{
 const query=new URLSearchParams(hash.replace(/^#/,''));
 const attemptId=query.get('valuationRun'),view=query.get('report')??'breakdown';
 if(!attemptId||!/^[a-zA-Z0-9-]{1,100}$/.test(attemptId)||!reportViews.includes(view as ReportView))return null;
 return {attemptId,view:view as ReportView};
}
export function reportHash(location:ReportLocation):string{
 return '#'+new URLSearchParams({valuationRun:location.attemptId,report:location.view}).toString();
}
export function writeReportLocation(location:ReportLocation|null,mode:'push'|'replace'='push'){
 if(typeof window==='undefined')return;
 if(!location&&!readReportLocation(window.location.hash))return;
 const hash=location?reportHash(location):'';
 if(hash===window.location.hash)return;
 window.history[mode==='replace'?'replaceState':'pushState'](null,'',window.location.pathname+window.location.search+hash);
}
