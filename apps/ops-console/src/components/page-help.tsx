import {getPageGuide} from '@/lib/page-guides';

/** Optional native disclosure: no portal, fetch, form action or draft state ownership. */
export function PageHelp({pathname,embedded=false}:{pathname:string;embedded?:boolean}){
 const guide=getPageGuide(pathname);
 if(!guide)return null;
 return <details className={`page-help${embedded?' page-help-embedded':''}`} key={pathname}>
  <summary><span>How to use this page</span>{' '}<span className="page-help-topic">{guide.title}</span></summary>
  <div className="page-help-content">
   <section><h2>Purpose</h2><p>{guide.purpose}</p><h2>How to use it</h2><ol>{guide.steps.map(step=><li key={step}>{step}</li>)}</ol></section>
   <section><h2>Key terms</h2><dl>{guide.terms.map(item=><div key={item.term}><dt>{item.term}</dt><dd>{item.meaning}</dd></div>)}</dl></section>
   <section className="page-help-impact"><h2>Workflow impact</h2><ul>{guide.impact.map(item=><li key={item}>{item}</li>)}</ul><p className="page-help-note">This guide is explanatory. Permissions, form validation and retained evidence determine what can actually be done. Opening help does not save or submit anything.</p></section>
  </div>
 </details>;
}
